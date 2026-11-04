import copy
import types

import pytest
from fastapi.testclient import TestClient

from app import ai, main

PROGRAMS = {
    "ccsf-evening-it": {
        "id": "ccsf-evening-it", "name": "Evening IT Support", "provider": "City College of San Francisco",
        "tuition_usd": 0, "materials_usd": 0, "exam_fees_usd": 0, "schedule": "part-time-evening",
        "hours_per_week": 6, "weeks": 8, "format": "in-person", "free_to_resident": True, "wioa_etpl": False,
    },
    "per-scholas-it-support": {
        "id": "per-scholas-it-support", "name": "IT Support", "provider": "Per Scholas",
        "tuition_usd": 0, "schedule": "full-time-day", "hours_per_week": 40, "weeks": 15,
        "format": "in-person", "free_to_resident": True, "wioa_etpl": False,
    },
}
PROPS = [{"code": "MISSION-24", "name": "24th & Mission Commons (demo)", "neighborhood": "Mission",
          "housing_type": "LIHTC", "units": 180}]

PROGRAMS["ccsf-evening-it"]["location"] = {"lat": 37.73, "lon": -122.45}

PROFILE = {
    "language": "es", "goal": "IT support job", "availability": "evenings", "hours_per_week_available": 8,
    "needs_childcare": True, "children": 2, "has_computer": False, "commute": "muni",
    "search_query": "part-time evening IT support training for beginners",
}


@pytest.fixture
def client(monkeypatch):
    store: dict[str, dict] = {}
    catalog = types.SimpleNamespace(
        load_properties=lambda: PROPS,
        get_property=lambda code: next((p for p in PROPS if p["code"] == code), None),
        get_program=lambda pid: copy.deepcopy(PROGRAMS.get(pid)),
        load_programs=lambda: list(PROGRAMS.values()),
    )

    def update(app_id, patch):
        store[app_id] = {**store[app_id], **patch}
        return store[app_id]

    search = types.SimpleNamespace(
        es_status=lambda: {"connected": True, "cluster": "test", "inference_id": "x", "programs": 2, "applications": len(store), "error": None},
        search_programs=lambda q, profile, k=6: [
            {**PROGRAMS["per-scholas-it-support"], "_score": 9.0, "_why": "IT support"},
            {**PROGRAMS["ccsf-evening-it"], "_score": 5.0, "_why": "evening"},
        ],
        save_application=lambda doc: store.setdefault(doc["id"], doc),
        get_application=lambda app_id: store.get(app_id),
        list_applications=lambda: list(store.values()),
        update_application=update,
        impact_stats=lambda: {"total": len(store), "by_status": {}, "query": {}},
    )
    building = {"id": "b-1", "name": "Real Building", "housing_type": "inclusionary",
                "location": {"lat": 37.75, "lon": -122.42}}
    opendata = types.SimpleNamespace(
        housing_stats=lambda: {"buildings": 570, "units": 31981, "query": {}},
        search_buildings=lambda q, size=6: [building] if q else [],
        get_building=lambda bid: building if bid == "b-1" else None,
        distance_km=lambda a, b: 1.5 if a and b else None,
    )
    monkeypatch.setattr(main, "_opendata", lambda: opendata)
    monkeypatch.setattr(main, "_cat", lambda: catalog)
    monkeypatch.setattr(main, "_search", lambda: search)
    monkeypatch.setattr(ai, "parse_intake", lambda text, lang=None: dict(PROFILE))
    monkeypatch.setattr(ai, "draft_plan", lambda *a: {"headline": "Plan", "steps": ["a"], "message": "Hola", "navigator_note": "n", "risks": []})
    return TestClient(main.app), store


def test_health(client):
    c, _ = client
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json()["elastic"]["connected"] is True


def test_join_known_and_unknown(client):
    c, _ = client
    assert c.post("/api/join", json={"property_code": "mission-24"}).json()["property"]["code"] == "MISSION-24"
    assert c.post("/api/join", json={"property_code": "NOPE"}).status_code == 404


def test_intake_returns_profile_and_ms(client):
    c, _ = client
    r = c.post("/api/intake", json={"text": "Trabajo de día, tengo dos hijos"})
    body = r.json()
    assert body["profile"]["language"] == "es"
    assert "ms" in body


def test_intake_mistral_failure_is_502(client, monkeypatch):
    c, _ = client

    def boom(*a, **k):
        raise ai.AIError("Mistral call failed: timeout")

    monkeypatch.setattr(ai, "parse_intake", boom)
    r = c.post("/api/intake", json={"text": "hola"})
    assert r.status_code == 502
    assert r.json()["stage"] == "mistral"


def test_match_puts_schedule_fit_free_program_first(client):
    c, _ = client
    r = c.post("/api/match", json={"profile": PROFILE})
    progs = r.json()["programs"]
    assert progs[0]["id"] == "ccsf-evening-it"
    assert progs[0]["schedule_fit"] is True
    assert progs[0]["waterfall"]["totals"]["resident"] == 0
    assert progs[1]["schedule_fit"] is False


def test_match_elastic_failure_is_502(client, monkeypatch):
    c, _ = client
    search = main._search()

    def boom(*a, **k):
        raise ConnectionError("cluster unreachable")

    monkeypatch.setattr(search, "search_programs", boom)
    r = c.post("/api/match", json={"profile": PROFILE})
    assert r.status_code == 502
    assert r.json()["stage"] == "elastic"


def test_full_flow_plan_apply_approve_milestones(client):
    c, store = client
    plan = c.post("/api/plan", json={"profile": PROFILE, "program_id": "ccsf-evening-it", "property_code": "MISSION-24"}).json()
    assert plan["benefits"]["status"] == "protected"
    assert plan["waterfall"]["tier"] == "stay_in_training"

    created = c.post("/api/applications", json={
        "profile": {**PROFILE, "immigration_status": "x"}, "program_id": "ccsf-evening-it",
        "property_code": "MISSION-24", "plan": plan["plan"],
        "waterfall": {"totals": {"grant": 999999}},  # client amounts are ignored
    }).json()["application"]
    assert created["id"].startswith("HB-2026-")
    assert created["grant_amount"] <= 2500
    assert "immigration_status" not in created["profile"]
    assert created["risk"] in ("low", "medium")
    app_id = created["id"]

    assert c.post(f"/api/applications/{app_id}/milestone", json={"milestone": "enrolled"}).status_code == 409

    approved = c.post(f"/api/applications/{app_id}/decision", json={"action": "approve", "reviewer": "Dana"}).json()["application"]
    assert approved["status"] == "approved"
    assert approved["decision_days"] is not None

    enrolled = c.post(f"/api/applications/{app_id}/milestone", json={"milestone": "enrolled"}).json()["application"]
    assert enrolled["status"] == "enrolled"
    assert enrolled["payments"] and all(p["paid_to"] for p in enrolled["payments"])

    placed = c.post(f"/api/applications/{app_id}/milestone", json={"milestone": "placed"}).json()["application"]
    assert placed["outcome"] == {"completed": True, "placed_or_raise": True}

    apps = c.get("/api/applications").json()["applications"]
    assert apps[0]["id"] == app_id


def test_risk_high_for_daytime_full_time_program(client):
    c, _ = client
    created = c.post("/api/applications", json={
        "profile": PROFILE, "program_id": "per-scholas-it-support", "property_code": "MISSION-24",
    }).json()["application"]
    assert created["risk"] == "high"
    assert any("h/week" in r for r in created["risk_reasons"])


def test_impact_includes_budget(client):
    c, _ = client
    body = c.get("/api/impact").json()
    assert body["budget"]["total"] == 368500
    assert sum(i["amount"] for i in body["budget"]["items"]) == 368500


def test_opendata_endpoints(client):
    c, _ = client
    assert c.get("/api/opendata/housing").json()["units"] == 31981
    assert c.get("/api/buildings", params={"q": "mission"}).json()["buildings"][0]["id"] == "b-1"


def test_opendata_failure_is_502(client, monkeypatch):
    c, _ = client
    od = main._opendata()

    def boom():
        raise ConnectionError("down")

    monkeypatch.setattr(od, "housing_stats", boom)
    r = c.get("/api/opendata/housing")
    assert r.status_code == 502 and r.json()["stage"] == "elastic"


def test_match_with_building_adds_distance(client):
    c, _ = client
    progs = c.post("/api/match", json={"profile": PROFILE, "building_id": "b-1"}).json()["programs"]
    ccsf = next(p for p in progs if p["id"] == "ccsf-evening-it")
    assert ccsf["distance_km"] == 1.5
    ps = next(p for p in progs if p["id"] == "per-scholas-it-support")
    assert ps["distance_km"] is None  # no location: None-safe


def test_plan_uses_building_housing_type_when_no_property(client):
    c, _ = client
    body = c.post("/api/plan", json={"profile": PROFILE, "program_id": "ccsf-evening-it", "building_id": "b-1"}).json()
    assert body["program"]["distance_km"] == 1.5
    assert body["benefits"]["status"] == "review"
    assert any("Operator confirms program type" in i["treatment"] for i in body["benefits"]["items"])


def test_intake_display_fallback_is_english_when_model_omits_it():
    profile = ai._normalize_profile({"language": "es", "goal": "IT job", "availability": "evenings"}, "hola", None)
    assert profile["display"]["goal"] == "IT job"
    translated = ai._normalize_profile({"language": "es", "goal": "IT job", "display": {"goal": "Trabajo en TI"}}, "hola", None)
    assert translated["display"]["goal"] == "Trabajo en TI"


def test_application_stores_free_program_value(client):
    c, _ = client
    created = c.post("/api/applications", json={"profile": PROFILE, "program_id": "ccsf-evening-it", "property_code": "MISSION-24"}).json()["application"]
    assert created["free_program_value"] == 1200


def test_draft_plan_asks_for_resident_language_headline_and_steps(monkeypatch):
    seen = {}

    def fake_chat(system, user, **kw):
        seen["system"] = system
        return {"headline": "Empieza", "steps": ["Paso 1"], "steps_en": ["Step 1"], "message": "Hola",
                "navigator_note": "n", "risks": ["r"]}

    monkeypatch.setattr(ai, "_chat_json", fake_chat)
    out = ai.draft_plan({"language": "es"}, {"name": "x"}, {"lines": []}, {"status": "protected"})
    assert "headline in Spanish" in seen["system"] and "steps in Spanish" in seen["system"]
    assert out["steps"] == ["Paso 1"] and out["steps_en"] == ["Step 1"]


# ---------- Mistral rate-limit resilience ----------

def test_complete_retries_rate_limit_then_succeeds(monkeypatch):
    from app import ai

    calls = {"n": 0}

    class Chat:
        def complete(self, **kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError('API error occurred: Status 429. Body: {"message":"Rate limit exceeded"}')
            return "ok"

    class Client:
        chat = Chat()

    monkeypatch.setattr(ai, "_mistral", lambda: Client())
    monkeypatch.setattr(ai, "RATE_LIMIT_BACKOFF_S", (0.0, 0.0, 0.0))
    assert ai._complete(model="m", messages=[]) == "ok"
    assert calls["n"] == 3


def test_complete_gives_up_after_backoff_and_does_not_retry_other_errors(monkeypatch):
    import pytest
    from app import ai

    calls = {"n": 0}

    class Chat:
        def complete(self, **kw):
            calls["n"] += 1
            raise RuntimeError("Status 429 rate_limited")

    class Client:
        chat = Chat()

    monkeypatch.setattr(ai, "_mistral", lambda: Client())
    monkeypatch.setattr(ai, "RATE_LIMIT_BACKOFF_S", (0.0, 0.0))
    with pytest.raises(RuntimeError):
        ai._complete(model="m", messages=[])
    assert calls["n"] == 3  # first try + two backoff retries

    calls["n"] = 0

    class BadChat:
        def complete(self, **kw):
            calls["n"] += 1
            raise ValueError("invalid request")

    class BadClient:
        chat = BadChat()

    monkeypatch.setattr(ai, "_mistral", lambda: BadClient())
    with pytest.raises(ValueError):
        ai._complete(model="m", messages=[])
    assert calls["n"] == 1
