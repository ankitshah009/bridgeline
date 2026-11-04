"""Bridgeline directory: browse every grant template, training program and free resource.

`directory()` is served from the local JSON catalog so the marketplace view never depends on
Elasticsearch being up. `search()` runs Elastic semantic search over programs and resources
together and merges the hits.
"""
from __future__ import annotations

import re
import time
from typing import Any

from app import config, rules

SCHEDULE_LABELS = {
    "full-time-day": "Full-time, daytime",
    "part-time-day": "Part-time, daytime",
    "part-time-evening": "Evenings",
    "self-paced": "Self-paced, online",
}

LEVEL_SECTIONS = [
    ("career", "Career programs", "Job-ready training for IT support, networking, data and more."),
    ("entry", "Entry programs", "First certificates and short courses that open the door."),
    ("basics", "Digital basics", "Start here: computer, email and online skills, free."),
]

# Example grant budgets that show what each tier can pay for. These are illustrations of the
# template, not awards; real amounts come from the funding waterfall for a specific plan.
TIER_EXAMPLES = {
    "starter": {
        "example": "Refurbished laptop and a certification exam voucher for someone studying on their own.",
        "example_lines": [{"item": "Refurbished laptop", "amount": 350, "paid_to": "Approved device vendor"},
                          {"item": "Exam voucher", "amount": 150, "paid_to": "Testing provider"}],
        "accent": "yellow",
    },
    "stay_in_training": {
        "example": "Evening child care, a Clipper START pass and a laptop while attending a free program.",
        "example_lines": [{"item": "Child care, one term", "amount": 1920, "paid_to": "Licensed child care provider"},
                          {"item": "Transit", "amount": 172, "paid_to": "SFMTA · Clipper START"},
                          {"item": "Refurbished laptop", "amount": 350, "paid_to": "Approved device vendor"}],
        "accent": "purple",
    },
    "career": {
        "example": "Tuition for a paid program when no free or public option fits, paid 50/30/20 at milestones.",
        "example_lines": [{"item": "Tuition (50% at enrollment)", "amount": 2250, "paid_to": "Training provider"},
                          {"item": "Tuition (30% at completion)", "amount": 1350, "paid_to": "Training provider"},
                          {"item": "Tuition (20% at placement)", "amount": 900, "paid_to": "Training provider"}],
        "accent": "green",
    },
}

# Resource sections in display order. Each resource lands in the first section whose rule matches,
# so every row of the research appears exactly once.
RESOURCE_SECTIONS: list[tuple[str, str, str]] = [
    ("childcare", "Child care & family", "Care for your kids while you train."),
    ("transit", "Transit", "Cheaper or free rides to class."),
    ("devices", "Devices & internet", "Computers, home internet and tech help."),
    ("housing", "Scholarships & savings (housing residents)", "Only for residents of affordable or assisted housing."),
    ("colleges", "Colleges & universities", "Free and discounted college classes."),
    ("aid", "Training & public aid", "No-cost training programs and public funding for tuition."),
    ("coaching", "Career coaching & mentors", "Free coaching, resume help and volunteer mentors for your job search."),
    ("local", "Free local programs", "Neighborhood classes, labs and one-on-one help."),
]

STATUS_ORDER = {"Available": 0, "Confirm": 1, "Not yet available": 2, "Closed for 2026": 3}
RRF_K = 10


def _resource_section(r: dict) -> str:
    tags = set(r.get("tags") or [])
    category = r.get("category") or ""
    if category == "Only for affordable or assisted housing":
        return "housing"
    if category == "Career coaching and mentors" or tags & {"career-coaching", "mentorship"}:
        return "coaching"
    if "childcare" in tags:
        return "childcare"
    if "transit" in tags:
        return "transit"
    if category == "Costs that make training harder" or (
            tags & {"device", "internet"} and category == "Free local programs" and "training" not in tags):
        return "devices"
    if category == "Colleges and universities":
        return "colleges"
    if category == "Training and education":
        return "aid"
    return "local"


def _load_programs() -> list[dict]:
    from app import catalog

    return catalog.load_programs()


def _load_resources() -> list[dict]:
    from app import resources

    return resources.load_resources()


def program_item(p: dict) -> dict:
    cost = float((p.get("tuition_usd") or 0) + (p.get("materials_usd") or 0) + (p.get("exam_fees_usd") or 0))
    item = {k: v for k, v in p.items() if k not in ("search_text",)}
    item.update({
        "kind": "program",
        "resident_cost_hint": cost,
        "free": bool(p.get("free_to_resident")) or cost == 0,
        "schedule_label": SCHEDULE_LABELS.get(p.get("schedule", ""), p.get("schedule", "")),
    })
    return item


def tier_items() -> list[dict]:
    out = []
    for tid, t in rules.GRANT_TIERS.items():
        out.append({"kind": "tier", "id": tid, "label": t["label"], "cap": t["cap"], "covers": t["covers"],
                    "requires": t["requires"], **TIER_EXAMPLES.get(tid, {})})
    return out


def directory() -> dict[str, Any]:
    t0 = time.perf_counter()
    programs = [program_item(p) for p in _load_programs()]
    resources = _load_resources()

    sections: list[dict] = [{
        "id": "tiers", "kind": "tier", "title": "Bridgeline grant templates",
        "subtitle": "What the grant can pay for. Always paid to providers and vendors, never cash.",
        "items": tier_items(),
    }]
    for level, title, subtitle in LEVEL_SECTIONS:
        items = [p for p in programs if p.get("level") == level]
        # Free first, then lowest cost, then evenings/self-paced ahead of full-time day.
        items.sort(key=lambda p: (not p["free"], p["resident_cost_hint"], p.get("illustrative", False), p["name"]))
        if items:
            sections.append({"id": level, "kind": "program", "title": title, "subtitle": subtitle, "items": items})

    grouped: dict[str, list[dict]] = {sid: [] for sid, _, _ in RESOURCE_SECTIONS}
    for r in resources:
        grouped[_resource_section(r)].append({**r, "kind": "resource"})
    for sid, title, subtitle in RESOURCE_SECTIONS:
        items = sorted(grouped[sid], key=lambda r: (STATUS_ORDER.get(r.get("status"), 9), r.get("program", "")))
        if items:
            sections.append({"id": sid, "kind": "resource", "title": title, "subtitle": subtitle, "items": items})

    return {
        "sections": sections,
        "counts": {"programs": len(programs), "resources": len(resources), "tiers": len(rules.GRANT_TIERS)},
        "ms": int((time.perf_counter() - t0) * 1000),
    }


# Need words in the five pilot languages -> resource tags. Semantic scores from one embedding model sit
# in a narrow band, so an explicit need in the query ("child care", "Muni", "laptop") gets a boost.
INTENT_WORDS: dict[str, tuple[str, ...]] = {
    "childcare": ("child", "kid", "daycare", "babysit", "niño", "nino", "hijo", "cuidado", "guarder",
                  "托兒", "托儿", "孩子", "小孩", "bata", "anak", "trẻ", "con nhỏ", "giữ trẻ"),
    "transit": ("muni", "bus", "transit", "clipper", "fare", "transporte", "pasaje", "autobús", "autobus",
                "公車", "交通", "pamasahe", "xe buýt", "đi lại"),
    "device": ("laptop", "computer", "device", "computadora", "laptop", "電腦", "kompyuter", "máy tính"),
    "internet": ("internet", "wifi", "wi-fi", "網路", "mạng"),
    "scholarship": ("scholarship", "beca", "獎學金", "iskolar", "học bổng"),
    "career-coaching": ("resume", "résumé", "coach", "career advice", "job search", "interview",
                        "currículum", "curriculum", "entrevista", "履歷", "簡歷", "面試", "panayam",
                        "sơ yếu", "phỏng vấn"),
    "mentorship": ("mentor", "mentoría", "mentoria", "導師", "người hướng dẫn"),
}
EVENING_WORDS = ("evening", "night", "noche", "nocturn", "晚上", "夜", "gabi", "buổi tối", "tối")


_CJK = re.compile(r"[　-鿿]")


def _hit(word: str, low: str) -> bool:
    """CJK words match as substrings (no spaces between words). Other words need a word boundary,
    so "bus" doesn't fire on Spanish "busco"; short words also allow a plural ("kids", "buses")."""
    if _CJK.search(word):
        return word in low
    if len(word) <= 3:
        return re.search(rf"\b{re.escape(word)}(?:s|es)?\b", low) is not None
    return re.search(rf"\b{re.escape(word)}", low) is not None


def intents(q: str) -> tuple[list[str], bool]:
    low = (q or "").lower()
    tags = [tag for tag, words in INTENT_WORDS.items() if any(_hit(w, low) for w in words)]
    return tags, any(_hit(w, low) for w in EVENING_WORDS)


def search_bodies(q: str, size: int = 12) -> tuple[dict, dict]:
    tags, evening = intents(q)
    program_should: list[dict] = []
    if evening:
        program_should.append({"terms": {"schedule": ["part-time-evening", "self-paced"], "boost": 0.5}})
    programs_body = {
        "size": size,
        "_source": {"excludes": ["search_text"]},
        "query": {"bool": {"must": [{"semantic": {"field": "description", "query": q}}],
                           "should": program_should,
                           "must_not": [{"term": {"isa_or_required_loan": True}}]}},
    }
    resource_should: list[dict] = [{"term": {"status": {"value": "Available", "boost": 0.05}}}]
    if tags:
        resource_should.append({"terms": {"tags": tags, "boost": 1.0}})
    resources_body = {
        "size": size,
        "_source": {"excludes": ["text"]},
        "query": {"bool": {"must": [{"semantic": {"field": "text", "query": q}}],
                           "should": resource_should}},
    }
    return programs_body, resources_body


def search(q: str, k: int = 12) -> dict[str, Any]:
    """Semantic search across programs and resources. Raises on Elasticsearch failure."""
    from app.resources import INDEX_RESOURCES
    from app.search import _require

    es = _require()
    q = (q or "").strip()
    pb, rb = search_bodies(q, size=k)
    t0 = time.perf_counter()
    resp = es.msearch(searches=[{"index": config.INDEX_PROGRAMS}, pb, {"index": INDEX_RESOURCES}, rb])
    took = int((time.perf_counter() - t0) * 1000)
    responses = resp["responses"]
    for r in responses:
        if "error" in r:
            raise RuntimeError(str(r["error"])[:300])

    results: list[dict] = []
    for h in responses[0]["hits"]["hits"]:
        item = program_item(h["_source"])
        item["_score"] = h.get("_score") or 0.0
        item["_why"] = f"{item['schedule_label']} · " + ("Free tuition" if item["free"] else
                                                         f"${item['resident_cost_hint']:,.0f} before aid")
        results.append(item)
    resource_results: list[dict] = []
    for h in responses[1]["hits"]["hits"]:
        d = {**h["_source"], "kind": "resource", "_score": h.get("_score") or 0.0}
        d["_why"] = f"{d.get('category', '')} · {d.get('status', '')}"
        resource_results.append(d)

    # Reciprocal rank fusion across the two indices: each list keeps its own ranking (scores from
    # different indices aren't comparable once boosts apply), and the marketplace shows both kinds.
    fused: list[tuple[float, float, dict]] = []
    for ranked in (results, resource_results):
        ranked.sort(key=lambda d: d["_score"], reverse=True)
        for rank, d in enumerate(ranked):
            d["_rank"] = rank + 1
            fused.append((1.0 / (RRF_K + rank + 1), d["_score"], d))
    fused.sort(key=lambda t: (t[0], t[1]), reverse=True)
    tags, evening = intents(q)
    return {"results": [d for _, _, d in fused[:k]], "intents": {"tags": tags, "evening": evening},
            "query": {"programs": pb, "resources": rb, "fusion": f"rrf(k={RRF_K})"}, "took_ms": took}
