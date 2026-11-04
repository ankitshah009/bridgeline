"""Honest availability: programs known not to be running this term are never recommended first."""
import types
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import catalog, directory, main, search

NOT_RUNNING = "ccsf-noncredit-computer-basics"


def _stale(pid: str, score: float) -> dict:
    """A program document as an older Elasticsearch copy would return it: no availability fields."""
    doc = catalog.get_program(pid)
    doc.pop("offered_now", None)
    doc.pop("availability_note", None)
    return {**doc, "_score": score}


def test_catalog_marks_every_program_and_flags_ccsf_basics():
    programs = catalog.load_programs()
    assert all("offered_now" in p for p in programs)
    off = [p for p in programs if p["offered_now"] is False]
    assert [p["id"] for p in off] == [NOT_RUNNING]
    note = off[0]["availability_note"]
    assert "Currently unavailable" in note and "2026-11-03" in note and "ccsf.edu" in note


@pytest.fixture
def api(monkeypatch):
    def search_programs(q, profile, k=6):
        # Computer Basics has the best semantic score and the stale doc lacks offered_now.
        return [_stale(NOT_RUNNING, 0.99), _stale("sfpl-tech-help", 0.7),
                _stale("ccsf-it-support-certificate", 0.8), _stale("google-it-support-coursera", 0.6)]

    monkeypatch.setattr(main, "_search", lambda: types.SimpleNamespace(search_programs=search_programs))
    monkeypatch.setattr(main, "_attach_live_checks", lambda items: None)
    return TestClient(main.app)


def _profile(**kw):
    base = {"language": "es", "goal": "Trabajar en computadoras", "in_scope": True, "needs_clarification": False,
            "availability": "evenings", "hours_per_week_available": 8, "career_tracks": ["digital basics", "IT support"],
            "children": 2, "needs_childcare": True, "has_computer": False, "search_query": "evening IT training"}
    return {**base, **kw}


def test_match_never_recommends_a_program_that_is_not_running(api):
    progs = api.post("/api/match", json={"profile": _profile()}).json()["programs"]
    ids = [p["id"] for p in progs]
    assert ids[0] == "ccsf-it-support-certificate"
    assert ids[-1] == NOT_RUNNING  # after every running program, despite the top semantic score
    basics = progs[-1]
    assert basics["offered_now"] is False and basics["availability_note"]  # overlaid from the catalog
    assert basics["match_role"] == "other" and basics["goal_match"] is False
    assert basics["fit"].startswith("Not running this term")


def test_on_ramp_or_goal_goes_to_an_offered_basics_class(api):
    p = _profile(availability="flexible", hours_per_week_available=20, career_tracks=["digital basics"],
                 goal="Learn computer basics")
    progs = api.post("/api/match", json={"profile": p}).json()["programs"]
    roles = {x["id"]: x["match_role"] for x in progs}
    assert roles["sfpl-tech-help"] in ("goal", "on_ramp")
    assert roles[NOT_RUNNING] == "other"
    assert [x["id"] for x in progs][-1] == NOT_RUNNING


def test_fit_label_and_role_helpers():
    prog = catalog.get_program(NOT_RUNNING)
    assert main.offered_now(prog) is False and main.offered_now({"offered_now": "unknown"}) is True
    assert main.match_role(prog, {"career_tracks": ["digital basics"]}) == "other"


def test_directory_shows_not_running_last_with_note():
    secs = {s["id"]: s for s in directory.directory()["sections"]}
    basics = secs["basics"]["items"]
    assert basics[-1]["id"] == NOT_RUNNING and basics[-1]["availability_note"]
    assert all(i.get("offered_now") is not False for i in basics[:-1])


class _FakeMsearch:
    def __init__(self, responses):
        self.responses = responses

    def msearch(self, **kw):
        return {"responses": self.responses}


def test_directory_search_puts_not_running_after_running(monkeypatch):
    src = lambda pid: {k: v for k, v in catalog.get_program(pid).items() if k not in ("offered_now", "availability_note")}
    fake = _FakeMsearch([
        {"hits": {"hits": [{"_source": src(NOT_RUNNING), "_score": 0.95},
                           {"_source": src("sfpl-tech-help"), "_score": 0.80}]}},
        {"hits": {"hits": []}},
    ])
    monkeypatch.setattr("app.search._require", lambda: fake)
    out = directory.search("computer basics", k=12)
    progs = [r for r in out["results"] if r["kind"] == "program"]
    assert [p["id"] for p in progs] == ["sfpl-tech-help", NOT_RUNNING]
    assert progs[1]["_why"].startswith("Not running this term") and progs[1]["offered_now"] is False


def test_search_programs_sorts_not_running_last(monkeypatch):
    client = MagicMock()
    hits = []
    for pid, score in ((NOT_RUNNING, 9.0), ("sfpl-tech-help", 5.0)):
        doc = catalog.get_program(pid)
        doc["search_text"] = "x"
        hits.append({"_id": pid, "_score": score, "_source": doc})
    client.search.return_value = {"hits": {"hits": hits}}
    monkeypatch.setattr(search, "es_client", lambda: client)
    ranked = search.search_programs("computer basics", {"availability": "evenings"}, k=6)
    assert [p["id"] for p in ranked] == ["sfpl-tech-help", NOT_RUNNING]
    assert ranked[1]["_why"].startswith("Not running this term")
