"""Free programs, discounts and grants a resident should check before the Bridgeline grant pays.

Source: "Grants, Funding and Free Programs for San Francisco Affordable Housing Residents",
status as of 2026-11-03 (app/data/resources.json, 32 rows, each with its public source link).
Indexed in Elasticsearch as `homebase-resources` with a semantic_text field embedded by Mistral.
"""
from __future__ import annotations

import json
import time
from typing import Any

from app import config

INDEX_RESOURCES = "homebase-resources"
SNAPSHOT = config.DATA_DIR / "resources.json"
SOURCE_LABEL = "Bridgeline research · SF grants, funding and free programs (status as of 2026-11-03)"
CLOSED = "Closed for 2026"

TAG_LABELS = {
    "childcare": "child care",
    "transit": "transit",
    "internet": "home internet",
    "device": "a computer",
    "tuition": "tuition",
    "savings": "savings",
    "scholarship": "scholarships",
    "training": "training",
    "digital-basics": "digital basics",
    "older-adults": "older adults",
    "disability": "disability support",
    "youth": "young adults",
    "career-coaching": "career coaching",
    "mentorship": "mentors",
    "job-readiness": "job search help",
}

# Child care is the barrier that most often ends training, so it outranks everything else.
# Audience programs (older adults, youth) are boosted only when the resident volunteered their age.
TAG_WEIGHTS = {"childcare": 1.2, "older-adults": 1.0, "youth": 0.8, "device": 0.5, "transit": 0.5,
               "savings": 0.4, "internet": 0.3, "career-coaching": 0.3, "digital-basics": 0.25, "training": 0.1}

# Out-of-scope goals (healthcare, trades...): free City training that is not tech-only.
GENERAL_TRAINING_IDS = ["other-city-job-training", "city-college-noncredit-classes", "five-keys-schools-and-programs",
                        "goodwill-training-and-career-services", "federal-voucher-through-the-city", "free-city-college"]
TECH_ONLY_IDS = ["techsf", "per-scholas", "stanford-code-in-place", "dev-mission-tech-support-and-programs",
                 "dev-mission-pre-apprenticeship"]
SUPPORT_TAGS = ("childcare", "transit")

# Coaching and mentor resources: a resident whose goal is a job always sees exactly one of these.
COACHING_TAGS = ("career-coaching", "mentorship")
JOB_WORDS = ("job", "career", "work", "employ", "hire", "position", "trabajo", "empleo", "carrera",
             "工作", "職", "就業", "trabaho", "hanapbuhay", "việc làm", "công việc", "nghề")
AUDIENCE_TAGS = ("older-adults", "disability", "youth")

# Housing programs whose residents can use the SF Housing Authority FSS account.
FSS_HOUSING_TYPES = {"public_housing", "voucher"}


def mapping(inference_id: str) -> dict:
    return {
        "properties": {
            "id": {"type": "keyword"},
            "category": {"type": "keyword"},
            "program": {"type": "text", "fields": {"kw": {"type": "keyword"}}},
            "provides": {"type": "text"},
            "who": {"type": "text"},
            "status": {"type": "keyword"},
            "status_note": {"type": "text"},
            "source_url": {"type": "keyword", "index": False},
            "tags": {"type": "keyword"},
            "housing_only": {"type": "boolean"},
            "as_of": {"type": "date"},
            "text": {"type": "semantic_text", "inference_id": inference_id},
        }
    }


def load_resources() -> list[dict]:
    return json.loads(SNAPSHOT.read_text())


def search_text(r: dict) -> str:
    return f"{r['program']}. {r['provides']}. Who qualifies: {r['who']}. Category: {r['category']}."


def wanted_tags(profile: dict, housing_type: str | None = None) -> list[str]:
    """Which needs this resident has, inferred only from what they told us."""
    tags: list[str] = []
    if profile.get("needs_childcare"):
        tags.append("childcare")
    commute = str(profile.get("commute") or "").lower()
    if commute in ("muni", "bus", "transit", "bart", "clipper") or not commute:
        tags.append("transit")
    if profile.get("has_computer") is False:
        tags += ["device", "internet"]
    experience = str(profile.get("experience") or "").lower()
    if any(w in experience for w in ("little", "no computer", "basic", "beginner", "none", "smartphone")):
        tags.append("digital-basics")
    tags.append("training")
    if housing_type in FSS_HOUSING_TYPES:
        tags.append("savings")
    # Only when the resident volunteered their age; we never ask for it.
    age = profile.get("age_group")
    if age == "55_plus":
        tags.append("older-adults")
    elif age == "under_25":
        tags.append("youth")
    if seeks_job(profile):
        tags.append("career-coaching")
    return list(dict.fromkeys(tags))


def seeks_job(profile: dict) -> bool:
    """True when the resident's goal is employment (any pilot language).

    Learning digital basics alone (e.g. email and video calls) is not a job search."""
    if [t for t in profile.get("career_tracks") or [] if str(t).lower() != "digital basics"]:
        return True
    text = " ".join(str(profile.get(k) or "") for k in ("goal", "search_query")).lower()
    return any(w in text for w in JOB_WORDS)


def is_coaching(doc: dict) -> bool:
    return bool(set(doc.get("tags") or []) & set(COACHING_TAGS))


def coaching_query(profile: dict) -> dict:
    """Best single coaching/mentor resource for this resident's goal (open ones only)."""
    goal = profile.get("search_query") or profile.get("goal") or "job search"
    return {
        "size": 1,
        "_source": {"excludes": ["text"]},
        "query": {"bool": {
            "must": [{"semantic": {"field": "text", "query": f"career coaching and mentors for: {goal}"}}],
            "filter": [{"terms": {"tags": list(COACHING_TAGS)}}],
            "must_not": [{"term": {"status": CLOSED}}],
        }},
    }


def build_query(profile: dict, housing_type: str | None = None, k: int = 6,
                include_closed: bool = False) -> dict:
    tags = wanted_tags(profile, housing_type)
    need_words = {
        "childcare": "free child care for my kids while I study",
        "transit": "discounted Muni bus fare",
        "device": "free or refurbished computer",
        "internet": "free home internet",
        "digital-basics": "beginner computer classes",
        "savings": "savings account for education",
        "older-adults": "free computer classes and tech help for older adults and seniors",
        "youth": "tech programs for young adults",
    }
    goal = profile.get("search_query") or profile.get("goal") or "tech job training"
    text = "; ".join([str(goal)] + [need_words[t] for t in tags if t in need_words])
    should: list[dict] = [{"term": {"tags": {"value": t, "boost": TAG_WEIGHTS.get(t, 0.2)}}} for t in tags]
    should.append({"term": {"status": {"value": "Available", "boost": 0.2}}})
    must_not: list[dict] = []
    if not include_closed:
        must_not.append({"term": {"status": CLOSED}})
    if housing_type not in FSS_HOUSING_TYPES:
        must_not.append({"term": {"id": "sf-housing-authority-family-self-sufficiency"}})
    positive = {
        "bool": {
            "must": [{"semantic": {"field": "text", "query": text}}],
            "should": should,
            "must_not": must_not,
        }
    }
    # Programs built for a specific audience (older adults, disability, youth) are demoted, not hidden,
    # because we never ask age or disability status.
    audience = [t for t in AUDIENCE_TAGS if t not in tags]
    own = [t for t in AUDIENCE_TAGS if t in tags]  # audiences the resident told us they belong to
    negative: dict = {"terms": {"tags": audience}}
    if own:  # a resource that also serves the resident's own audience is never demoted
        negative = {"bool": {"must": [negative], "must_not": [{"terms": {"tags": own}}]}}
    query = (
        {"boosting": {"positive": positive, "negative": negative, "negative_boost": 0.4}}
        if audience else positive
    )
    return {"size": k, "_source": {"excludes": ["text"]}, "query": query}


def alternatives_query(profile: dict, housing_type: str | None = None, k: int = 4) -> dict:
    """Free City training for a goal Bridgeline does not fund (healthcare, trades...)."""
    goal = profile.get("search_query") or profile.get("goal") or "job training"
    must_not: list[dict] = [{"term": {"status": CLOSED}}, {"terms": {"id": TECH_ONLY_IDS}}]
    if housing_type not in FSS_HOUSING_TYPES:
        must_not.append({"term": {"id": "sf-housing-authority-family-self-sufficiency"}})
    return {
        "size": k,
        "_source": {"excludes": ["text"]},
        "query": {"bool": {
            "must": [{"semantic": {"field": "text", "query": f"free job training and classes for: {goal}"}}],
            "filter": [{"terms": {"tags": ["training", "tuition", "career-coaching"]}}],
            "should": [{"terms": {"id": GENERAL_TRAINING_IDS, "boost": 0.3}},
                       {"term": {"status": {"value": "Available", "boost": 0.1}}}],
            "must_not": must_not,
        }},
    }


def supports_query(profile: dict, k: int = 2) -> dict | None:
    """Child care and transit help, whatever the training goal. None when the resident needs neither."""
    tags = [t for t in wanted_tags(profile) if t in SUPPORT_TAGS]
    if not tags:
        return None
    return {
        "size": k,
        "_source": {"excludes": ["text"]},
        "query": {"bool": {
            "filter": [{"terms": {"tags": tags}}],
            "should": [{"term": {"tags": {"value": "childcare", "boost": 2.0}}},
                       {"term": {"status": {"value": "Available", "boost": 1.0}}}],
            "must_not": [{"term": {"status": CLOSED}}],
        }},
    }


def alternative_training(profile: dict, housing_type: str | None = None, k: int = 4) -> dict[str, Any]:
    """Out-of-scope goals: free City training for the resident's own goal, plus child care / transit help.

    Raises on Elastic failure."""
    es = _es()
    t0 = time.perf_counter()
    body = alternatives_query(profile, housing_type, k)
    alts = []
    for h in es.search(index=INDEX_RESOURCES, **body)["hits"]["hits"]:
        d = dict(h["_source"])
        d["_score"] = h.get("_score")
        status = {"Available": "open now", "Confirm": "confirm current openings"}.get(d.get("status"), "")
        d["_why"] = " · ".join(p for p in ("Free training for your goal", status) if p)
        alts.append(d)
    supports = []
    sq = supports_query(profile)
    if sq:
        tags = wanted_tags(profile, housing_type)
        for h in es.search(index=INDEX_RESOURCES, **sq)["hits"]["hits"]:
            d = dict(h["_source"])
            d["_score"] = h.get("_score")
            d["_why"] = _why(d, tags)
            supports.append(d)
    return {"alternatives": alts, "supports": supports, "query": body, "supports_query": sq,
            "took_ms": int((time.perf_counter() - t0) * 1000), "source": SOURCE_LABEL}


def _es():
    from app.search import es_client

    es = es_client()
    if es is None:
        raise RuntimeError("Elasticsearch is not configured (ES_URL / ES_API_KEY)")
    return es


def _why(doc: dict, tags: list[str]) -> str:
    hit = [TAG_LABELS[t] for t in doc.get("tags", []) if t in tags and t != "training" and t in TAG_LABELS]
    parts = []
    if hit:
        parts.append("Helps with " + ", ".join(hit[:3]))
    if doc.get("status") == "Available":
        parts.append("open now")
    elif doc.get("status") == "Confirm":
        parts.append("confirm current openings")
    elif doc.get("status") == "Not yet available":
        parts.append("not open yet")
    return " · ".join(parts) or "Related to your goal"


def relevant_resources(profile: dict, housing_type: str | None = None, k: int = 6,
                       include_closed: bool = False) -> dict[str, Any]:
    """Semantic + tag-boosted search over the resources index. Raises on Elastic failure."""
    body = build_query(profile, housing_type, k, include_closed)
    tags = wanted_tags(profile, housing_type)
    es = _es()
    t0 = time.perf_counter()
    res = es.search(index=INDEX_RESOURCES, **body)

    def as_doc(h: dict) -> dict:
        d = dict(h["_source"])
        d["_score"] = h.get("_score")
        d["_why"] = _why(d, tags)
        return d

    docs: list[dict] = []
    coaching_seen = False
    for h in res["hits"]["hits"]:
        d = as_doc(h)
        if is_coaching(d):
            if coaching_seen:  # at most one coaching/mentor item
                continue
            coaching_seen = True
        docs.append(d)
    out: dict[str, Any] = {"query": body}
    if seeks_job(profile) and not coaching_seen and k > 0:
        cq = coaching_query(profile)
        extra = [as_doc(h) for h in es.search(index=INDEX_RESOURCES, **cq)["hits"]["hits"]]
        extra = [d for d in extra if is_coaching(d)]
        if extra:
            if len(docs) >= k:
                docs = docs[: k - 1]
            docs.append(extra[0])
            out["coaching_query"] = cq
    took = int((time.perf_counter() - t0) * 1000)
    return {"resources": docs, **out, "took_ms": took, "source": SOURCE_LABEL}
