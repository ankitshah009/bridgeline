from fastapi.testclient import TestClient

from app import resources, rules

SPANISH = {
    "language": "es", "goal": "Get an entry-level IT job", "career_tracks": ["IT support"],
    "experience": "Little computer experience", "availability": "evenings",
    "hours_per_week_available": 8, "needs_childcare": True, "children": 2,
    "has_computer": False, "commute": "muni",
    "search_query": "part-time evening IT support training for beginners",
}


def test_snapshot_rows_are_complete():
    rows = resources.load_resources()
    assert len(rows) == 34  # 32 researched rows + SFPL career coaching + ADPList mentors
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    allowed = {"Available", "Confirm", "Closed for 2026", "Not yet available"}
    for r in rows:
        assert r["status"] in allowed
        assert r["tags"] and set(r["tags"]) <= set(resources.TAG_LABELS)
        assert r["as_of"] == "2026-11-03"
        assert r["source_url"] and r["source_url"].startswith("http")
    # ids referenced by the rules engine exist
    for check in rules.CHECKS_FIRST.values():
        assert check["resource_id"] in ids


def test_wanted_tags_follow_the_profile():
    tags = resources.wanted_tags(SPANISH, "LIHTC")
    assert {"childcare", "transit", "device", "internet", "digital-basics", "training"} <= set(tags)
    assert "savings" not in tags
    assert "savings" in resources.wanted_tags(SPANISH, "public_housing")
    assert "childcare" not in resources.wanted_tags({"needs_childcare": False, "has_computer": True})


def test_query_excludes_closed_and_fss_for_non_assisted():
    body = resources.build_query(SPANISH, "LIHTC")
    positive = body["query"]["boosting"]["positive"]
    assert body["query"]["boosting"]["negative"] == {"terms": {"tags": ["older-adults", "disability", "youth"]}}
    must_not = positive["bool"]["must_not"]
    assert {"term": {"status": "Closed for 2026"}} in must_not
    assert {"term": {"id": "sf-housing-authority-family-self-sufficiency"}} in must_not
    assert positive["bool"]["must"][0]["semantic"]["field"] == "text"
    open_body = resources.build_query(SPANISH, "voucher", include_closed=True)
    assert open_body["query"]["boosting"]["positive"]["bool"]["must_not"] == []


class FakeES:
    def __init__(self, hits):
        self.hits, self.calls = hits, []

    def search(self, **kw):
        self.calls.append(kw)
        return {"hits": {"hits": self.hits}}


def test_relevant_resources_adds_why(monkeypatch):
    hits = [
        {"_score": 1.4, "_source": {"id": "san-francisco-child-care-support", "program": "San Francisco child care support",
                                     "tags": ["childcare"], "status": "Available"}},
        {"_score": 1.1, "_source": {"id": "tech-exchange-classes", "program": "Tech Exchange classes",
                                     "tags": ["digital-basics", "device"], "status": "Confirm"}},
    ]
    fake = FakeES(hits)
    monkeypatch.setattr(resources, "_es", lambda: fake)
    out = resources.relevant_resources(SPANISH, "LIHTC", k=2)
    assert fake.calls[0]["index"] == resources.INDEX_RESOURCES
    assert out["resources"][0]["_why"].startswith("Helps with child care")
    assert "confirm" in out["resources"][1]["_why"]
    assert out["query"]["size"] == 2


def test_coaching_rows_present():
    rows = {r["id"]: r for r in resources.load_resources()}
    sfpl, adp = rows["sfpl-career-coaching"], rows["adplist-mentors"]
    assert sfpl["status"] == "Confirm" and "May 6, 2026" in sfpl["status_note"]
    assert sfpl["source_url"] == "https://sfpl.org/events/2026/05/06/workshop-career-coaching"
    assert adp["status"] == "Available" and adp["source_url"] == "https://adplist.org/explore"
    assert resources.is_coaching(sfpl) and resources.is_coaching(adp)
    assert not sfpl["housing_only"] and not adp["housing_only"]


def test_seeks_job_multilingual():
    assert resources.seeks_job(SPANISH)
    assert resources.seeks_job({"goal": "Quiero un trabajo en computadoras"})
    assert resources.seeks_job({"goal": "找一份電腦工作"})
    assert not resources.seeks_job({"goal": "Learn to video call my grandkids"})
    assert "career-coaching" in resources.wanted_tags(SPANISH, "LIHTC")


class SeqES:
    """Returns a different response per search call."""

    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def search(self, **kw):
        self.calls.append(kw)
        return {"hits": {"hits": self.responses.pop(0)}}


def _h(id_, tags, score=1.0, status="Available"):
    return {"_score": score, "_source": {"id": id_, "program": id_, "tags": tags, "status": status}}


def test_job_seeker_gets_exactly_one_coaching_item_via_fallback(monkeypatch):
    main = [_h("childcare", ["childcare"], 1.4), _h("clipper", ["transit"], 1.2), _h("tx", ["device"], 1.1)]
    fake = SeqES(main, [_h("adplist-mentors", ["mentorship", "career-coaching"], 0.9)])
    monkeypatch.setattr(resources, "_es", lambda: fake)
    out = resources.relevant_resources(SPANISH, "LIHTC", k=3)
    ids = [d["id"] for d in out["resources"]]
    assert ids == ["childcare", "clipper", "adplist-mentors"]  # replaces the last slot, keeps k
    assert len(fake.calls) == 2
    assert fake.calls[1]["query"]["bool"]["filter"] == [{"terms": {"tags": ["career-coaching", "mentorship"]}}]
    assert out["resources"][-1]["_why"].startswith("Helps with career coaching")
    assert "coaching_query" in out


def test_job_seeker_coaching_deduped_and_no_extra_call(monkeypatch):
    main = [_h("sfpl-career-coaching", ["career-coaching"], 1.3), _h("childcare", ["childcare"], 1.2),
            _h("adplist-mentors", ["mentorship", "career-coaching"], 1.1)]
    fake = SeqES(main)
    monkeypatch.setattr(resources, "_es", lambda: fake)
    out = resources.relevant_resources(SPANISH, "LIHTC", k=3)
    assert [d["id"] for d in out["resources"]] == ["sfpl-career-coaching", "childcare"]
    assert len(fake.calls) == 1


def test_non_job_goal_gets_no_forced_coaching(monkeypatch):
    fake = SeqES([_h("childcare", ["childcare"])])
    monkeypatch.setattr(resources, "_es", lambda: fake)
    out = resources.relevant_resources({"goal": "Learn to video call family", "needs_childcare": True}, k=3)
    assert [d["id"] for d in out["resources"]] == ["childcare"]
    assert len(fake.calls) == 1


def test_waterfall_checks_first_keeps_amounts():
    program = {"id": "p", "name": "Evening IT", "provider": "CCSF", "tuition_usd": 0, "materials_usd": 0,
               "exam_fees_usd": 0, "schedule": "part-time-evening", "hours_per_week": 8, "weeks": 16,
               "format": "in-person", "free_to_resident": True, "level": "entry"}
    wf = rules.funding_waterfall(program, SPANISH)
    ids = [c["resource_id"] for c in wf["checks_first"]]
    assert ids == ["san-francisco-child-care-support", "clipper-start", "tech-exchange-classes"]
    transit = next(l for l in wf["lines"] if l["item"] == "Transit")
    assert "Clipper START" in transit["paid_to"]
    assert wf["totals"]["resident"] == 0
    assert wf["cash_to_resident"] == 0


def test_api_resources_endpoint(monkeypatch):
    from app import main

    monkeypatch.setattr(resources, "relevant_resources",
                        lambda profile, housing_type=None, k=6, include_closed=False: {
                            "resources": [{"id": "clipper-start", "_why": "Helps with transit"}],
                            "query": {"size": k}, "took_ms": 3, "source": "test"})
    client = TestClient(main.app)
    r = client.post("/api/resources", json={"profile": SPANISH, "housing_type": "LIHTC", "k": 3})
    assert r.status_code == 200
    data = r.json()
    assert data["resources"][0]["id"] == "clipper-start"
    assert data["query"] == {"size": 3}
    assert data["housing_type"] == "LIHTC"


def test_api_resources_reports_elastic_failure(monkeypatch):
    from app import main

    def boom(*a, **k):
        raise ConnectionError("down")

    monkeypatch.setattr(resources, "relevant_resources", boom)
    r = TestClient(main.app).post("/api/resources", json={"profile": SPANISH})
    assert r.status_code == 502
    assert r.json()["stage"] == "elastic"
