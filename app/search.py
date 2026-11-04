"""Elasticsearch access: program matching (semantic_text + Mistral embeddings), applications store, impact aggregations."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from elasticsearch import BadRequestError, Elasticsearch, NotFoundError

from app import config
from app.catalog import resident_cost

AWARDED_STATUSES = ["approved", "enrolled", "completed", "placed"]
DECIDED_STATUSES = AWARDED_STATUSES + ["declined", "needs_info"]

# How well a program's schedule fits what the resident said they can do (0..1).
SCHEDULE_FIT = {
    "evenings": {"part-time-evening": 1.0, "self-paced": 0.9, "part-time-day": 0.15, "full-time-day": 0.0},
    "weekends": {"self-paced": 1.0, "part-time-evening": 0.5, "part-time-day": 0.2, "full-time-day": 0.0},
    "daytime": {"part-time-day": 1.0, "self-paced": 0.8, "full-time-day": 0.75, "part-time-evening": 0.5},
    "full-time": {"full-time-day": 1.0, "part-time-day": 0.8, "self-paced": 0.7, "part-time-evening": 0.6},
    "flexible": {"full-time-day": 0.85, "part-time-day": 0.85, "self-paced": 0.85, "part-time-evening": 0.85},
}
SCHEDULE_LABEL = {
    "part-time-evening": "Evening classes",
    "part-time-day": "Part-time daytime",
    "full-time-day": "Full-time daytime",
    "self-paced": "Self-paced",
}
WEIGHTS = {"semantic": 0.35, "schedule": 0.25, "cost": 0.20, "hours": 0.10, "track": 0.07, "language": 0.03}

_client: Elasticsearch | None = None


def es_client() -> Elasticsearch | None:
    """Shared client, or None when ES_URL / ES_API_KEY are not set."""
    global _client
    if not (config.ES_URL and config.ES_API_KEY):
        return None
    if _client is None:
        _client = Elasticsearch(config.ES_URL, api_key=config.ES_API_KEY, request_timeout=30,
                                retry_on_timeout=True, max_retries=2)
    return _client


def _require() -> Elasticsearch:
    es = es_client()
    if es is None:
        raise RuntimeError("Elasticsearch is not configured: set ES_URL and ES_API_KEY in .env")
    return es


def _body(resp) -> dict:
    return resp.body if hasattr(resp, "body") else resp


# ---------------------------------------------------------------- mappings (shared with scripts/setup_elastic.py)

def programs_mapping(inference_id: str) -> dict:
    kw = {"type": "keyword"}
    flt = {"type": "float"}
    boolean = {"type": "boolean"}
    return {
        "dynamic": False,
        "properties": {
            "id": kw,
            "name": {"type": "text", "fields": {"keyword": kw}},
            "provider": {"type": "text", "fields": {"keyword": kw}},
            "level": kw,
            "career_tracks": kw,
            "description": {"type": "semantic_text", "inference_id": inference_id},
            "search_text": {"type": "text"},
            "tuition_usd": flt, "materials_usd": flt, "exam_fees_usd": flt, "resident_cost_usd": flt,
            "schedule": kw, "hours_per_week": flt, "weeks": flt, "format": kw, "neighborhood": kw,
            "location": {"type": "geo_point"},
            "languages": kw,
            "stipend": boolean, "free_to_resident": boolean, "wioa_etpl": boolean,
            "workforce_pell_candidate": boolean, "isa_or_required_loan": boolean,
            "refund_policy": boolean, "illustrative": boolean,
        },
    }


def applications_mapping() -> dict:
    kw = {"type": "keyword"}
    flt = {"type": "float"}
    return {
        "dynamic": False,  # profile, waterfall, benefits, plan, decision, payments stay in _source only
        "properties": {
            "id": kw, "created_at": {"type": "date"}, "updated_at": {"type": "date"}, "status": kw,
            "property_code": kw, "property_name": kw, "housing_type": kw, "language": kw,
            "program_id": kw, "program_name": kw, "provider": kw, "tier": kw,
            "grant_amount": flt, "free_program_value": flt, "public_aid": flt,
            "risk": kw, "risk_reasons": kw, "decision_days": flt, "simulated": {"type": "boolean"},
            "outcome": {"properties": {"completed": {"type": "boolean"}, "placed_or_raise": {"type": "boolean"}}},
        },
    }


# ---------------------------------------------------------------- status

def current_inference_id(es: Elasticsearch | None = None) -> str | None:
    es = es or es_client()
    if es is None:
        return None
    try:
        mapping = _body(es.indices.get_mapping(index=config.INDEX_PROGRAMS))
    except NotFoundError:
        return None
    for idx in mapping.values():
        desc = idx.get("mappings", {}).get("properties", {}).get("description", {})
        if desc.get("type") == "semantic_text":
            return desc.get("inference_id", "default")
    return None


def _count(es: Elasticsearch, index: str) -> int:
    try:
        return int(_body(es.count(index=index))["count"])
    except NotFoundError:
        return 0


def es_status() -> dict:
    status = {"connected": False, "cluster": None, "inference_id": None, "programs": 0, "applications": 0, "error": None}
    es = es_client()
    if es is None:
        status["error"] = "ES_URL / ES_API_KEY not set"
        return status
    try:
        info = _body(es.info())
        status["connected"] = True
        status["cluster"] = info.get("cluster_name") or info.get("name")
        status["inference_id"] = current_inference_id(es)
        status["programs"] = _count(es, config.INDEX_PROGRAMS)
        status["applications"] = _count(es, config.INDEX_APPLICATIONS)
    except Exception as exc:  # surface any failure to the health panel
        status["error"] = f"{type(exc).__name__}: {exc}"[:300]
    return status


# ---------------------------------------------------------------- program matching

def _track_match(profile_tracks: list[str], program_tracks: list[str]) -> str | None:
    for want in profile_tracks or []:
        w = want.lower().strip()
        if not w:
            continue
        for have in program_tracks or []:
            h = have.lower()
            if w in h or h in w:
                return have
    return None


def _fit(program: dict, profile: dict) -> tuple[dict, list[str]]:
    availability = (profile.get("availability") or "flexible").lower()
    schedule = program.get("schedule", "")
    sched_fit = SCHEDULE_FIT.get(availability, SCHEDULE_FIT["flexible"]).get(schedule, 0.5)

    cost = resident_cost(program)
    free = bool(program.get("free_to_resident"))
    cost_fit = 1.0 if free else max(0.0, 1.0 - cost / 6000.0)

    hours_fit = 1.0
    available = profile.get("hours_per_week_available")
    ph = float(program.get("hours_per_week") or 0)
    if isinstance(available, (int, float)) and available > 0 and ph > available * 1.25 + 1:
        hours_fit = max(0.0, 1.0 - (ph - available) / ph)

    track = _track_match(profile.get("career_tracks") or [], program.get("career_tracks") or [])
    lang = (profile.get("language") or "en").lower()
    lang_fit = 1.0 if lang in [l.lower() for l in program.get("languages", [])] else 0.0

    reasons: list[str] = []
    label = SCHEDULE_LABEL.get(schedule, schedule)
    if sched_fit >= 0.8:
        reasons.append(f"{label}: fits your schedule")
    elif sched_fit <= 0.2:
        reasons.append(f"{label}: hard to fit with your current hours")
    else:
        reasons.append(label)
    if free:
        reasons.append("Free tuition" if cost == 0 else f"Free tuition (about ${cost:,.0f} for books/fees)")
    else:
        reasons.append(f"${cost:,.0f} before aid")
    if track:
        reasons.append(f"Leads to {track}")
    if lang != "en" and lang_fit:
        reasons.append("Offered in your language")
    if program.get("stipend"):
        reasons.append("Pays a stipend: needs a benefits check")
    if program.get("illustrative"):
        reasons.append("Illustrative example")
    comps = {"schedule": sched_fit, "cost": cost_fit, "hours": hours_fit,
             "track": 1.0 if track else 0.0, "language": lang_fit}
    return comps, reasons


def _program_query(query: str, with_highlight: bool) -> dict:
    body = {
        "size": 25,
        "query": {
            "bool": {
                "should": [{"semantic": {"field": "description", "query": query}}],
                "must_not": [{"term": {"isa_or_required_loan": True}}],
                "minimum_should_match": 1,
            }
        },
    }
    if with_highlight:
        body["highlight"] = {"fields": {"description": {"type": "semantic", "number_of_fragments": 1, "order": "score"}}}
    return body


def search_programs(query: str, profile: dict, k: int = 6, include_unapproved: bool = False) -> list[dict]:
    """Semantic search over the catalog, re-ranked by fit (schedule, resident cost, hours, track, language).

    Raises on Elasticsearch failure; never returns made-up results.
    """
    es = _require()
    query = (query or profile.get("search_query") or profile.get("goal") or "tech training for beginners").strip()
    body = _program_query(query, with_highlight=True)
    if include_unapproved:
        body["query"]["bool"].pop("must_not")
    started = time.perf_counter()
    try:
        resp = _body(es.search(index=config.INDEX_PROGRAMS, body=body))
    except BadRequestError:
        body.pop("highlight", None)  # older clusters without the semantic highlighter
        resp = _body(es.search(index=config.INDEX_PROGRAMS, body=body))
    took_ms = int((time.perf_counter() - started) * 1000)

    hits = resp.get("hits", {}).get("hits", [])
    if not hits:
        return []
    max_score = max((h.get("_score") or 0.0) for h in hits) or 1.0
    ranked = []
    for h in hits:
        program = dict(h["_source"])
        program.pop("search_text", None)
        sem = (h.get("_score") or 0.0) / max_score
        comps, reasons = _fit(program, profile)
        comps["semantic"] = sem
        score = sum(WEIGHTS[name] * value for name, value in comps.items())
        frags = (h.get("highlight") or {}).get("description") or []
        program.update({
            "_score": round(score, 4),
            "_es_score": h.get("_score"),
            "_why": " · ".join(reasons),
            "_highlight": frags[0] if frags else None,
            "_fit": {name: round(value, 3) for name, value in comps.items()},
            "_took_ms": took_ms,
        })
        ranked.append(program)
    ranked.sort(key=lambda p: p["_score"], reverse=True)
    return ranked[:k]


# ---------------------------------------------------------------- applications

def save_application(doc: dict) -> dict:
    es = _require()
    doc = dict(doc)
    doc.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    es.index(index=config.INDEX_APPLICATIONS, id=doc["id"], document=doc, refresh=True)
    return doc


def get_application(app_id: str) -> dict | None:
    es = _require()
    try:
        return _body(es.get(index=config.INDEX_APPLICATIONS, id=app_id))["_source"]
    except NotFoundError:
        return None


def list_applications(include_simulated: bool = True, size: int = 200) -> list[dict]:
    es = _require()
    query = {"match_all": {}} if include_simulated else {"bool": {"must_not": [{"term": {"simulated": True}}]}}
    resp = _body(es.search(index=config.INDEX_APPLICATIONS,
                           body={"size": size, "query": query, "sort": [{"created_at": {"order": "desc"}}]}))
    return [h["_source"] for h in resp.get("hits", {}).get("hits", [])]


def update_application(app_id: str, patch: dict) -> dict:
    es = _require()
    patch = dict(patch)
    patch["updated_at"] = datetime.now(timezone.utc).isoformat()
    es.update(index=config.INDEX_APPLICATIONS, id=app_id, doc=patch, refresh=True)
    doc = get_application(app_id)
    if doc is None:
        raise KeyError(app_id)
    return doc


# ---------------------------------------------------------------- impact

IMPACT_SCOPES = ("all", "live")


def impact_query(scope: str = "all") -> dict:
    """Aggregation body for the impact page. scope="live" drops the simulated pilot cohort."""
    awarded = {"terms": {"status": AWARDED_STATUSES}}
    body: dict = {
        "size": 0,
        "track_total_hits": True,
    }
    if scope == "live":
        body["query"] = {"bool": {"must_not": [{"term": {"simulated": True}}]}}
    return body | {
        "aggs": {
            "by_status": {"terms": {"field": "status", "size": 20}},
            "by_tier": {"terms": {"field": "tier", "size": 10}},
            "by_language": {"terms": {"field": "language", "size": 10}},
            "by_property": {
                "terms": {"field": "property_name", "size": 50},
                "aggs": {"approved": {"filter": awarded}},
            },
            "awarded": {
                "filter": awarded,
                "aggs": {
                    "free_program_value": {"sum": {"field": "free_program_value"}},
                    "public_aid": {"sum": {"field": "public_aid"}},
                    "grant": {"sum": {"field": "grant_amount"}},
                },
            },
            "completed": {"filter": {"term": {"outcome.completed": True}}},
            "placed_or_raise": {"filter": {"term": {"outcome.placed_or_raise": True}}},
            "decision_days": {"percentiles": {"field": "decision_days", "percents": [50]}},
            "simulated": {"filter": {"term": {"simulated": True}}},
        },
    }


def _buckets(aggs: dict, name: str) -> dict:
    return {b["key"]: b["doc_count"] for b in aggs.get(name, {}).get("buckets", [])}


def impact_stats(scope: str = "all") -> dict:
    if scope not in IMPACT_SCOPES:
        raise ValueError(f"scope must be one of {IMPACT_SCOPES}")
    es = _require()
    body = impact_query(scope)
    started = time.perf_counter()
    resp = _body(es.search(index=config.INDEX_APPLICATIONS, body=body))
    took_ms = int((time.perf_counter() - started) * 1000)
    aggs = resp.get("aggregations", {})
    total_raw = resp.get("hits", {}).get("total", 0)
    total = total_raw.get("value", 0) if isinstance(total_raw, dict) else int(total_raw)
    by_status = _buckets(aggs, "by_status")
    awarded = aggs.get("awarded", {})
    median_raw = (aggs.get("decision_days", {}).get("values") or {}).get("50.0")
    simulated = aggs.get("simulated", {}).get("doc_count", 0)

    def n(*statuses: str) -> int:
        return sum(by_status.get(s, 0) for s in statuses)

    return {
        "total": total,
        "by_status": by_status,
        "by_tier": _buckets(aggs, "by_tier"),
        "by_language": _buckets(aggs, "by_language"),
        "by_property": [
            {"property": b["key"], "residents": b["doc_count"], "approved": b.get("approved", {}).get("doc_count", 0)}
            for b in aggs.get("by_property", {}).get("buckets", [])
        ],
        "dollars": {
            "free_program_value": round(awarded.get("free_program_value", {}).get("value", 0.0) or 0.0, 2),
            "public_aid": round(awarded.get("public_aid", {}).get("value", 0.0) or 0.0, 2),
            "grant": round(awarded.get("grant", {}).get("value", 0.0) or 0.0, 2),
        },
        "outcomes": {
            "completed": aggs.get("completed", {}).get("doc_count", 0),
            "placed_or_raise": aggs.get("placed_or_raise", {}).get("doc_count", 0),
        },
        "funnel": [
            {"stage": "Applied", "count": total},
            {"stage": "Decided", "count": n(*DECIDED_STATUSES)},
            {"stage": "Grant approved", "count": n(*AWARDED_STATUSES)},
            {"stage": "Enrolled", "count": n("enrolled", "completed", "placed")},
            {"stage": "Completed", "count": n("completed", "placed")},
            {"stage": "Job or raise", "count": n("placed")},
        ],
        "median_decision_days": round(median_raw, 1) if isinstance(median_raw, (int, float)) else None,
        "simulated_count": simulated,
        "live_count": total - simulated,
        "took_ms": resp.get("took", took_ms),
        "scope": scope,
        "query": body,
    }
