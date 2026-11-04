import pytest
from fastapi.testclient import TestClient

from app import directory, main


@pytest.fixture
def client():
    return TestClient(main.app)


def test_directory_sections_cover_everything():
    d = directory.directory()
    ids = [s["id"] for s in d["sections"]]
    assert ids[0] == "tiers"
    assert ids[1:4] == ["career", "entry", "basics"]
    tiers = d["sections"][0]["items"]
    assert [t["id"] for t in tiers] == ["starter", "stay_in_training", "career"]
    assert [t["cap"] for t in tiers] == [500, 2500, 6000]
    assert all(t["example_lines"] for t in tiers)

    programs = [i for s in d["sections"] if s["kind"] == "program" for i in s["items"]]
    resources = [i for s in d["sections"] if s["kind"] == "resource" for i in s["items"]]
    assert len(programs) == d["counts"]["programs"]
    assert len(resources) == d["counts"]["resources"]  # every research row appears exactly once
    assert len({r["id"] for r in resources}) == len(resources)


def test_program_items_have_cost_hint_and_schedule_label():
    item = directory.program_item({"id": "x", "name": "X", "level": "entry", "tuition_usd": 100,
                                   "materials_usd": 20, "exam_fees_usd": 30, "schedule": "part-time-evening",
                                   "free_to_resident": False})
    assert item["resident_cost_hint"] == 150
    assert item["free"] is False
    assert item["schedule_label"] == "Evenings"


def test_resource_sections_sorted_available_first_closed_last():
    d = directory.directory()
    order = directory.STATUS_ORDER
    for s in d["sections"]:
        if s["kind"] != "resource":
            continue
        ranks = [order.get(i["status"], 9) for i in s["items"]]
        assert ranks == sorted(ranks)


def test_resource_grouping_rules():
    sec = directory._resource_section
    assert sec({"category": "Only for affordable or assisted housing", "tags": ["transit"]}) == "housing"
    assert sec({"category": "Costs that make training harder", "tags": ["childcare"]}) == "childcare"
    assert sec({"category": "Costs that make training harder", "tags": ["transit"]}) == "transit"
    assert sec({"category": "Costs that make training harder", "tags": ["internet"]}) == "devices"
    assert sec({"category": "Colleges and universities", "tags": ["tuition"]}) == "colleges"
    assert sec({"category": "Training and education", "tags": ["training"]}) == "aid"
    assert sec({"category": "Free local programs", "tags": ["training", "digital-basics"]}) == "local"
    assert sec({"category": "Career coaching and mentors", "tags": ["career-coaching"]}) == "coaching"
    assert sec({"category": "Free local programs", "tags": ["mentorship"]}) == "coaching"


def test_coaching_section_after_aid_with_both_items():
    d = directory.directory()
    ids = [s["id"] for s in d["sections"]]
    assert ids.index("coaching") == ids.index("aid") + 1
    coaching = next(s for s in d["sections"] if s["id"] == "coaching")
    assert coaching["title"] == "Career coaching & mentors"
    assert [i["id"] for i in coaching["items"]] == ["adplist-mentors", "sfpl-career-coaching"]  # Available first
    assert d["counts"]["resources"] == 34


def test_coaching_intents():
    assert directory.intents("free resume help")[0] == ["career-coaching"]
    assert directory.intents("busco un mentor")[0] == ["mentorship"]
    assert directory.intents("ayuda con mi currículum y entrevista")[0] == ["career-coaching"]


def test_intents_use_word_boundaries():
    assert directory.intents("busco trabajo")[0] == []  # "bus" must not fire inside "busco"
    assert directory.intents("free buses and kids care")[0] == ["childcare", "transit"]
    assert directory.intents("我需要托兒")[0] == ["childcare"]  # CJK still substring-matched
    assert directory.intents("cuidado de niños gratis")[0] == ["childcare"]


def test_directory_endpoint(client):
    r = client.get("/api/directory")
    assert r.status_code == 200
    body = r.json()
    assert body["counts"]["tiers"] == 3 and body["sections"]


class FakeES:
    def __init__(self, responses=None, raise_exc=None):
        self.responses, self.raise_exc, self.calls = responses, raise_exc, []

    def msearch(self, **kw):
        self.calls.append(kw)
        if self.raise_exc:
            raise self.raise_exc
        return {"responses": self.responses}


def _hit(src, score):
    return {"_source": src, "_score": score}


def test_search_merges_programs_and_resources_by_score(monkeypatch):
    fake = FakeES([
        {"hits": {"hits": [_hit({"id": "p1", "name": "Evening IT", "tuition_usd": 0, "schedule": "part-time-evening",
                                 "free_to_resident": True}, 0.80)]}},
        {"hits": {"hits": [_hit({"id": "r1", "program": "SF child care support", "category": "Costs",
                                 "status": "Available"}, 0.90)]}},
    ])
    monkeypatch.setattr("app.search._require", lambda: fake)
    out = directory.search("cuidado de niños gratis", k=12)
    assert [r["id"] for r in out["results"]] == ["r1", "p1"]  # rank 1 in each list; raw score breaks the tie
    assert out["intents"] == {"tags": ["childcare"], "evening": False}
    rb = fake.calls[0]["searches"][3]
    assert {"terms": {"tags": ["childcare"], "boost": 1.0}} in rb["query"]["bool"]["should"]
    assert out["results"][0]["kind"] == "resource" and out["results"][1]["kind"] == "program"
    assert out["results"][1]["_why"].startswith("Evenings")
    searches = fake.calls[0]["searches"]
    assert searches[1]["query"]["bool"]["must"][0]["semantic"]["field"] == "description"
    assert searches[3]["query"]["bool"]["must"][0]["semantic"]["field"] == "text"
    assert set(out["query"]) == {"programs", "resources", "fusion"}


def test_intents_multilingual():
    assert directory.intents("necesito una computadora para estudiar en la noche") == (["device"], True)
    assert directory.intents("free Muni pass and child care")[0] == ["childcare", "transit"]
    assert directory.intents("IT support") == ([], False)


def test_evening_intent_boosts_program_schedule():
    pb, _ = directory.search_bodies("evening IT classes")
    assert pb["query"]["bool"]["should"] == [
        {"terms": {"schedule": ["part-time-evening", "self-paced"], "boost": 0.5}}]


def test_search_endpoint_reports_elastic_stage(client, monkeypatch):
    monkeypatch.setattr("app.search._require", lambda: FakeES(raise_exc=ConnectionError("down")))
    r = client.get("/api/directory/search", params={"q": "IT"})
    assert r.status_code == 502
    assert r.json()["stage"] == "elastic"


def test_search_endpoint_requires_q(client):
    assert client.get("/api/directory/search", params={"q": " "}).status_code == 400


def test_search_raises_on_per_index_error(monkeypatch):
    fake = FakeES([{"error": {"type": "index_not_found_exception"}}, {"hits": {"hits": []}}])
    monkeypatch.setattr("app.search._require", lambda: fake)
    with pytest.raises(RuntimeError):
        directory.search("x")
