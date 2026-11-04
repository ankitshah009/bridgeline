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
}

# Child care is the barrier that most often ends training, so it outranks everything else.
TAG_WEIGHTS = {"childcare": 1.2, "device": 0.5, "transit": 0.5, "savings": 0.4, "internet": 0.3,
               "digital-basics": 0.25, "training": 0.1}
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
    return list(dict.fromkeys(tags))


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
    query = (
        {"boosting": {"positive": positive, "negative": {"terms": {"tags": audience}}, "negative_boost": 0.4}}
        if audience else positive
    )
    return {"size": k, "_source": {"excludes": ["text"]}, "query": query}


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
    t0 = time.perf_counter()
    res = _es().search(index=INDEX_RESOURCES, **body)
    took = int((time.perf_counter() - t0) * 1000)
    docs = []
    for h in res["hits"]["hits"]:
        d = dict(h["_source"])
        d["_score"] = h.get("_score")
        d["_why"] = _why(d, tags)
        docs.append(d)
    return {"resources": docs, "query": body, "took_ms": took, "source": SOURCE_LABEL}
