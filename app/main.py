"""Bridgeline HTTP API and page server."""
from __future__ import annotations

import contextlib
import os
import secrets
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import ai, config, rules

app = FastAPI(title="Bridgeline")
app.mount("/static", StaticFiles(directory=config.WEB_DIR, check_dir=False), name="static")


# Data modules are owned elsewhere; import lazily so tests can swap them.
def _cat():
    from app import catalog

    return catalog


def _search():
    from app import search

    return search


def _opendata():
    from app import opendata

    return opendata


def _opendata_auto_refresh() -> None:
    """Keep DataSF data fresh: check once at startup in a daemon thread (never blocks or raises).

    Skipped under pytest and when BRIDGELINE_AUTOREFRESH=0.
    """
    if os.getenv("BRIDGELINE_AUTOREFRESH", "1") == "0" or "PYTEST_CURRENT_TEST" in os.environ:
        return
    try:
        _opendata().start_auto_refresh()
    except Exception:  # freshness is best-effort; the API must still start
        pass


# Run the refresh at startup by wrapping the default lifespan (on_event is deprecated).
_default_lifespan = app.router.lifespan_context


@contextlib.asynccontextmanager
async def _lifespan(application):
    _opendata_auto_refresh()
    async with _default_lifespan(application) as state:
        yield state


app.router.lifespan_context = _lifespan


def _resources():
    from app import resources

    return resources


def _directory():
    from app import directory

    return directory


class StageError(Exception):
    def __init__(self, stage: str, error: str, status: int = 502):
        self.stage, self.error, self.status = stage, error, status


@app.exception_handler(StageError)
async def _stage_error(_: Request, exc: StageError):
    return JSONResponse({"error": exc.error, "stage": exc.stage}, status_code=exc.status)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _elastic(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except StageError:
        raise
    except Exception as exc:
        raise StageError("elastic", f"Elasticsearch failed: {type(exc).__name__}: {exc}") from exc


def _mistral(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        raise StageError("mistral", str(exc)) from exc


def _bad(msg: str, status: int = 400):
    return JSONResponse({"error": msg}, status_code=status)


# ---------- pages ----------

# The UI is the Next.js app in frontend/. This port only serves /api, so page URLs opened
# here redirect to the UI instead of returning a bare 404.
UI_URL = os.getenv("BRIDGELINE_UI_URL", "http://localhost:3000").rstrip("/")


@app.get("/", include_in_schema=False)
@app.get("/directory", include_in_schema=False)
@app.get("/navigator", include_in_schema=False)
@app.get("/impact", include_in_schema=False)
def ui_redirect(request: Request):
    return RedirectResponse(f"{UI_URL}{request.url.path}", status_code=307)


# ---------- API ----------

@app.get("/api/health")
def health():
    try:
        elastic = _search().es_status()
    except Exception as exc:
        elastic = {"connected": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"mistral": bool(ai.api_key()), "mistral_model": config.MISTRAL_CHAT_MODEL, "elastic": elastic}


def _property_public(p: dict) -> dict:
    return {k: p.get(k) for k in ("code", "name", "neighborhood", "housing_type", "units")}


@app.get("/api/properties")
def properties():
    return [_property_public(p) for p in _cat().load_properties()]


def _find_property(code: str | None) -> dict | None:
    if not code:
        return None
    cat = _cat()
    prop = cat.get_property(code) or cat.get_property(code.strip().upper())
    if prop:
        return prop
    code_l = code.strip().lower()
    return next((p for p in cat.load_properties() if str(p.get("code", "")).lower() == code_l), None)


@app.post("/api/join")
async def join(request: Request):
    body = await request.json()
    prop = _find_property(body.get("property_code"))
    if not prop:
        return _bad("We couldn't find that property code. Check the text from your building, or ask your service coordinator.", 404)
    return {"property": _property_public(prop)}


@app.get("/api/opendata/housing")
def opendata_housing():
    t0 = time.perf_counter()
    stats = _elastic(_opendata().housing_stats)
    return {**stats, "ms": _ms(t0)}


@app.get("/api/buildings")
def buildings(q: str = ""):
    t0 = time.perf_counter()
    found = _elastic(_opendata().search_buildings, q)
    return {"buildings": found, "ms": _ms(t0)}


def _building(building_id: str | None) -> dict | None:
    if not building_id:
        return None
    return _elastic(_opendata().get_building, building_id)


def _distance(building: dict | None, program: dict) -> float | None:
    if not building:
        return None
    try:
        return _opendata().distance_km(building.get("location"), program.get("location"))
    except Exception:
        return None


@app.post("/api/intake")
async def intake(request: Request):
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        return _bad("Tell us a little about your goals first.")
    t0 = time.perf_counter()
    profile = _mistral(ai.parse_intake, text, body.get("language"))
    return {"profile": profile, "ms": _ms(t0)}


SCHEDULE_FITS = {
    "evenings": {"part-time-evening", "self-paced"},
    "weekends": {"self-paced"},
    "daytime": {"part-time-day", "full-time-day", "self-paced"},
    "full-time": {"full-time-day", "part-time-day", "part-time-evening", "self-paced"},
    "flexible": {"full-time-day", "part-time-day", "part-time-evening", "self-paced"},
}

SCHEDULE_LABELS = {
    "full-time-day": "Full-time days",
    "part-time-day": "Part-time days",
    "part-time-evening": "Evenings",
    "self-paced": "Self-paced",
}


def schedule_fit(program: dict, profile: dict) -> bool:
    fits = SCHEDULE_FITS.get(profile.get("availability") or "flexible", SCHEDULE_FITS["flexible"])
    if program.get("schedule") not in fits:
        return False
    avail = profile.get("hours_per_week_available") or 0
    need = program.get("hours_per_week") or 0
    return not avail or need <= avail + 2


def _fit_label(program: dict, wf: dict, fits: bool) -> str:
    parts = [SCHEDULE_LABELS.get(program.get("schedule"), program.get("schedule") or "")]
    if program.get("hours_per_week"):
        parts.append(f"{program['hours_per_week']:g} h/week")
    if program.get("weeks"):
        parts.append(f"{program['weeks']} weeks")
    parts.append("Free" if wf["totals"]["free_program"] or program.get("free_to_resident") else "Funded")
    if wf["totals"]["resident"] == 0:
        parts.append("$0 to you")
    if not fits:
        parts.append("schedule conflict")
    if not wf.get("approved_provider", True):
        parts.append("not grant-eligible")
    return " · ".join(p for p in parts if p)


@app.post("/api/match")
async def match(request: Request):
    body = await request.json()
    profile = body.get("profile") or {}
    query = profile.get("search_query") or profile.get("goal") or "beginner tech training"
    t0 = time.perf_counter()
    hits = _elastic(_search().search_programs, query, profile, 6)
    building = _building(body.get("building_id"))
    ms = _ms(t0)
    out = []
    for p in hits:
        wf = rules.funding_waterfall(p, profile)
        fits = schedule_fit(p, profile)
        out.append({**p, "waterfall": wf, "schedule_fit": fits, "fit": _fit_label(p, wf, fits),
                    "distance_km": _distance(building, p)})
    out.sort(key=lambda p: (not p["waterfall"]["approved_provider"], not p["schedule_fit"],
                            p["waterfall"]["totals"]["resident"] > 0,
                            not p.get("free_to_resident"), -(p.get("_score") or 0)))
    return {"programs": out, "query": query, "ms": ms}


def _housing_type(property_code: str | None, building: dict | None = None) -> str:
    prop = _find_property(property_code)
    return (prop or {}).get("housing_type") or (building or {}).get("housing_type") or "other"


@app.post("/api/plan")
async def plan(request: Request):
    body = await request.json()
    profile = body.get("profile") or {}
    program = _cat().get_program(body.get("program_id") or "")
    if not program:
        return _bad("Unknown program", 404)
    building = _building(body.get("building_id"))
    program = {**program, "distance_km": _distance(building, program)}
    wf = rules.funding_waterfall(program, profile)
    benefits = rules.benefits_check(wf, _housing_type(body.get("property_code"), building))
    t0 = time.perf_counter()
    drafted = _mistral(ai.draft_plan, profile, program, wf, benefits)
    out = {"program": program, "waterfall": wf, "benefits": benefits, "plan": drafted, "ms": _ms(t0)}
    try:
        found = _resources().relevant_resources(
            profile, _housing_type(body.get("property_code"), building), k=4)
        out["resources"] = found["resources"]
        _attach_live_checks(out["resources"])
    except Exception as exc:  # resources are additive; the plan stands without them
        out["resources"] = []
        out["resources_error"] = f"Elasticsearch failed: {type(exc).__name__}: {exc}"
    return out


@app.post("/api/resources")
async def resources_search(request: Request):
    body = await request.json()
    profile = body.get("profile") or {}
    housing_type = body.get("housing_type") or _housing_type(body.get("property_code"))
    t0 = time.perf_counter()
    found = _elastic(_resources().relevant_resources, profile, housing_type,
                     k=int(body.get("k") or 6), include_closed=bool(body.get("include_closed")))
    _attach_live_checks(found["resources"])
    return {"resources": found["resources"], "query": found["query"], "source": found["source"],
            "housing_type": housing_type, "ms": _ms(t0)}


@app.get("/api/directory")
def directory_browse():
    """Marketplace view: grant templates, programs by level, and free resources by need."""
    out = _directory().directory()
    _attach_live_checks([it for s in out["sections"] if s.get("kind") != "tier" for it in s["items"]])
    return out


@app.get("/api/directory/search")
def directory_search(q: str = "", k: int = 12):
    if not q.strip():
        return _bad("q is required")
    t0 = time.perf_counter()
    found = _elastic(_directory().search, q, k=max(1, min(k, 30)))
    _attach_live_checks(found["results"])
    return {"results": found["results"], "intents": found.get("intents"), "query": found["query"],
            "took_ms": found["took_ms"], "ms": _ms(t0)}


# ---------- live source checks ----------

def _attach_live_checks(items: list[dict]) -> None:
    """Additive: add `live_check` from the latest source-check run; silently skip on any failure."""
    try:
        from app import freshness

        freshness.attach(items)
    except Exception:
        pass


@app.get("/api/sources/status")
def sources_status():
    from app import freshness

    t0 = time.perf_counter()
    out = _elastic(freshness.status)
    return out | {"ms": _ms(t0)}


@app.post("/api/sources/verify")
def sources_verify():
    from app import freshness

    # On the public deployment, re-checks would let anyone spend Mistral quota; run them from the CLI.
    if os.getenv("VERCEL") or os.getenv("BRIDGELINE_DISABLE_SOURCE_VERIFY") == "1":
        return JSONResponse({"error": "Source re-checks run from the CLI on this deployment (scripts/verify_sources.py)",
                             "stage": "policy"}, status_code=403)
    if not freshness.start_background():
        return JSONResponse({"error": "A source check is already running", "running": True}, status_code=409)
    return {"started": True, "running": True}


def assess_risk(profile: dict, program: dict, wf: dict, benefits: dict) -> tuple[str, list[str]]:
    high, medium = [], []
    need = program.get("hours_per_week") or 0
    avail = profile.get("hours_per_week_available") or 0
    if need and avail and need > avail:
        (high if need - avail > 5 else medium).append(f"Program needs {need:g} h/week; resident has about {avail} h/week.")
    if profile.get("availability") == "evenings" and program.get("schedule") in ("full-time-day", "part-time-day"):
        high.append("Daytime program conflicts with the resident's current work hours.")
    childcare_funded = sum(l["amount"] for l in wf["lines"] if l["item"] == "Child care" and l["payer"] == "grant")
    if profile.get("needs_childcare") and childcare_funded <= 0:
        high.append("Needs child care, and none is funded yet.")
    if profile.get("has_computer") is False and program.get("format") in ("online", "hybrid") and \
            not any(l["item"] == "Laptop" and l["payer"] == "grant" for l in wf["lines"]):
        medium.append("No computer for an online or hybrid program.")
    if wf["totals"]["resident"] > 0:
        medium.append(f"Unfunded gap of ${wf['totals']['resident']:,.0f}.")
    if program.get("stipend"):
        medium.append("Program pays a stipend, which may count as household income. Benefits review needed.")
    if benefits.get("status") != "protected":
        medium.append("Benefits check needs compliance review before award.")
    if high:
        return "high", high + medium
    if medium:
        return "medium", medium
    return "low", []


@app.post("/api/applications")
async def create_application(request: Request):
    body = await request.json()
    profile = body.get("profile") or {}
    program = _cat().get_program(body.get("program_id") or "")
    if not program:
        return _bad("Unknown program", 404)
    prop = _find_property(body.get("property_code")) or {}
    building = _building(body.get("building_id"))
    housing_type = _housing_type(body.get("property_code"), building)
    # Recompute money server-side; the client copy is never trusted for amounts.
    wf = rules.funding_waterfall(program, profile)
    benefits = rules.benefits_check(wf, housing_type)
    risk, reasons = assess_risk(profile, program, wf, benefits)
    profile_clean = {k: v for k, v in profile.items() if k not in ("race", "ethnicity", "immigration_status")}
    doc = {
        "id": f"HB-2026-{secrets.randbelow(9000) + 1000}",
        "created_at": _now().isoformat(),
        "status": "submitted",
        "property_code": prop.get("code") or body.get("property_code"),
        "property_name": prop.get("name") or (building or {}).get("name"),
        "building_id": (building or {}).get("id"),
        "distance_km": _distance(building, program),
        "housing_type": housing_type,
        "language": profile.get("language") or "en",
        "profile": profile_clean,
        "program_id": program.get("id"),
        "program_name": program.get("name"),
        "provider": program.get("provider"),
        "tier": wf["tier"],
        "grant_amount": wf["totals"]["grant"],
        "free_program_value": wf["totals"]["free_program_value"],
        "public_aid": wf["totals"]["public_aid"],
        "waterfall": wf,
        "benefits": benefits,
        "plan": body.get("plan") or {},
        "risk": risk,
        "risk_reasons": reasons,
        "decision": None,
        "decision_days": None,
        "payments": [],
        "outcome": {"completed": False, "placed_or_raise": False},
        "simulated": False,
    }
    t0 = time.perf_counter()
    saved = _elastic(_search().save_application, doc)
    return {"application": saved or doc, "ms": _ms(t0)}


def _sort_key(a: dict) -> str:
    return a.get("created_at") or ""


@app.get("/api/applications")
def list_applications():
    t0 = time.perf_counter()
    apps = _elastic(_search().list_applications)
    apps = sorted(apps, key=_sort_key, reverse=True)
    return {"applications": apps, "ms": _ms(t0)}


def _get_app(app_id: str) -> dict | None:
    return _elastic(_search().get_application, app_id)


@app.get("/api/applications/{app_id}")
def get_application(app_id: str):
    doc = _get_app(app_id)
    if not doc:
        return _bad("Application not found", 404)
    return {"application": doc}


DECISIONS = {"approve": "approved", "request_info": "needs_info", "decline": "declined"}


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


@app.post("/api/applications/{app_id}/decision")
async def decide(app_id: str, request: Request):
    body = await request.json()
    action = body.get("action")
    if action not in DECISIONS:
        return _bad("action must be approve, request_info or decline")
    doc = _get_app(app_id)
    if not doc:
        return _bad("Application not found", 404)
    now = _now()
    created = _parse_ts(doc.get("created_at"))
    days = round((now - created).total_seconds() / 86400, 2) if created else None
    patch = {
        "status": DECISIONS[action],
        "decision": {"action": action, "reviewer": body.get("reviewer") or "Navigator",
                     "note": body.get("note") or "", "at": now.isoformat()},
        "decision_days": days,
    }
    t0 = time.perf_counter()
    updated = _elastic(_search().update_application, app_id, patch)
    return {"application": updated or {**doc, **patch}, "ms": _ms(t0)}


MILESTONES = {"enrolled": "enrollment", "completed": "completion", "placed": "placement"}
ALLOWED_BEFORE = {
    "enrolled": {"approved"},
    "completed": {"approved", "enrolled"},
    "placed": {"approved", "enrolled", "completed"},
}


@app.post("/api/applications/{app_id}/milestone")
async def milestone(app_id: str, request: Request):
    body = await request.json()
    m = body.get("milestone")
    if m not in MILESTONES:
        return _bad("milestone must be enrolled, completed or placed")
    doc = _get_app(app_id)
    if not doc:
        return _bad("Application not found", 404)
    if doc.get("status") not in ALLOWED_BEFORE[m]:
        return _bad(f"Can't record '{m}' while the application is '{doc.get('status')}'. Approve it first.", 409)
    now = _now().isoformat()
    schedule = (doc.get("waterfall") or {}).get("payment_schedule") or []
    new_payments = [
        {"milestone": s["milestone"], "item": s.get("item"), "amount": s["amount"], "paid_to": s["paid_to"],
         "cadence": s.get("cadence", "once"), "at": now}
        for s in schedule if s.get("milestone") == MILESTONES[m]
    ]
    outcome = dict(doc.get("outcome") or {"completed": False, "placed_or_raise": False})
    if m in ("completed", "placed"):
        outcome["completed"] = True
    if m == "placed":
        outcome["placed_or_raise"] = True
    patch = {"status": m, "payments": (doc.get("payments") or []) + new_payments, "outcome": outcome}
    t0 = time.perf_counter()
    updated = _elastic(_search().update_application, app_id, patch)
    return {"application": updated or {**doc, **patch}, "ms": _ms(t0)}


PILOT_BUDGET = {
    "items": [
        {"item": "Training grant pool: 40 residents at an average of $3,000", "amount": 120000},
        {"item": "Career navigator, 1.0 FTE, loaded", "amount": 95000},
        {"item": "App design and development, contracted", "amount": 60000},
        {"item": "Program lead, partial time", "amount": 35000},
        {"item": "Hosting, text messaging and translation", "amount": 15000},
        {"item": "Independent evaluation", "amount": 10000},
        {"item": "Administration at 10%", "amount": 33500},
    ],
    "total": 368500,
    "recipients": 40,
    "per_recipient": 9212.5,
    "grant_share": 0.33,
    "expected_completers": 28,
    "expected_successes": 20,
    "per_successful_outcome": 18425,
    "note": "Planning assumptions, not quotes.",
}

TARGETS = {
    "activated": 200, "goal_check_rate": 0.5, "decision_days": 10,
    "completion_rate": 0.7, "placement_rate": 0.7, "housing_stability": 1.0,
}


@app.get("/api/impact")
def impact(scope: str = "all"):
    """scope=all (default): pilot model incl. the labelled simulated cohort. scope=live: live applications only."""
    if scope not in ("all", "live"):
        return _bad("scope must be 'all' or 'live'")
    t0 = time.perf_counter()
    if scope == "live":
        stats = _elastic(_search().impact_stats, scope="live")
    else:
        stats = _elastic(_search().impact_stats)
    return {**stats, "scope": scope, "budget": PILOT_BUDGET, "targets": TARGETS, "ms": _ms(t0)}
