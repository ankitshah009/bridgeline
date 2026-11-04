"""Intake honesty: never invent or recast a goal, rank by the stated goal, use age only when volunteered."""
import types

import pytest
from fastapi.testclient import TestClient

from app import ai, main, resources

# ---------------------------------------------------------------- intake normalization


def test_non_tech_goal_is_kept_and_flagged_out_of_scope():
    raw = {"language": "es", "goal": "Become a medical assistant", "in_scope": False,
           "career_tracks": ["IT support"], "children": 3}
    p = ai._normalize_profile(raw, "Quiero ser asistente médica. Tengo tres hijos.", None)
    assert p["goal"] == "Become a medical assistant"
    assert p["in_scope"] is False
    assert p["career_tracks"] == []  # never recast as tech
    assert p["scope_note"] == ai.SCOPE_NOTE["es"]
    assert p["needs_clarification"] is False and p["follow_up"] is None


def test_non_tech_goal_with_computer_wish_keeps_only_digital_basics():
    raw = {"language": "en", "goal": "Become a nurse", "in_scope": False, "wants_digital_skills": True,
           "career_tracks": ["IT support"], "scope_note": "We focus on tech; here is City training."}
    p = ai._normalize_profile(raw, "I want to be a nurse and also learn computers.", None)
    assert p["career_tracks"] == ["digital basics"]
    assert p["wants_digital_skills"] is True
    assert p["scope_note"] == "We focus on tech; here is City training."


def test_in_scope_profile_has_no_scope_note():
    p = ai._normalize_profile({"language": "en", "goal": "IT support job", "in_scope": True}, "I want an IT job", None)
    assert p["in_scope"] is True and p["scope_note"] is None


def test_greeting_makes_no_model_call_and_asks_follow_up(monkeypatch):
    monkeypatch.setattr(ai, "_chat_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no model call")))
    p = ai.parse_intake("hi")
    assert p["needs_clarification"] is True
    assert p["goal"] is None and p["display"]["goal"] == ""
    assert p["career_tracks"] == []
    assert p["follow_up"] == ai.FOLLOW_UP["en"]
    es = ai.parse_intake("¡Hola!")
    assert es["language"] == "es" and es["follow_up"] == ai.FOLLOW_UP["es"]
    assert ai.parse_intake("xin chào")["language"] == "vi"


def test_model_null_goal_means_clarification():
    p = ai._normalize_profile({"language": "tl", "goal": None}, "Gusto ko lang magtanong", None)
    assert p["needs_clarification"] is True and p["goal"] is None
    assert p["follow_up"] == ai.FOLLOW_UP["tl"]


def test_clarification_overrides_an_invented_goal():
    raw = {"language": "en", "goal": "Gain basic digital skills", "needs_clarification": True,
           "follow_up": "What job would you like?"}
    p = ai._normalize_profile(raw, "um not sure", None)
    assert p["goal"] is None and p["follow_up"] == "What job would you like?"
    assert p["search_query"] == "beginner digital skills"


@pytest.mark.parametrize("value,expected", [("55_plus", "55_plus"), ("under_25", "under_25"),
                                            ("old", None), (None, None), ("", None)])
def test_age_group_only_from_allowed_values(value, expected):
    p = ai._normalize_profile({"language": "en", "goal": "Learn email", "age_group": value}, "I want to learn email", None)
    assert p["age_group"] == expected


def test_intake_prompt_forbids_recasting_and_guessing():
    s = ai.INTAKE_SYSTEM
    assert "Never turn a non-tech goal" in s and "never invent a goal" in s and "Never guess age" in s


# ---------------------------------------------------------------- matching (API)

BASICS = {"id": "basics-evening", "name": "Computer Basics", "level": "basics", "schedule": "part-time-evening",
          "hours_per_week": 6, "weeks": 16, "tuition_usd": 0, "free_to_resident": True,
          "career_tracks": ["digital basics", "computer skills"]}
DATA = {"id": "data-analytics", "name": "Google Data Analytics", "level": "entry", "schedule": "self-paced",
        "hours_per_week": 8, "weeks": 24, "tuition_usd": 294, "free_to_resident": False,
        "career_tracks": ["data analytics", "spreadsheets"]}
CODING_DAY = {"id": "coding-day", "name": "Intro to Coding", "level": "entry", "schedule": "part-time-day",
              "hours_per_week": 10, "weeks": 8, "tuition_usd": 0, "free_to_resident": True,
              "career_tracks": ["software development"]}
IT_EVENING = {"id": "it-evening", "name": "Evening IT Certificate", "level": "career", "schedule": "part-time-evening",
              "hours_per_week": 8, "weeks": 34, "tuition_usd": 0, "free_to_resident": True,
              "career_tracks": ["IT support", "help desk"]}


@pytest.fixture
def api(monkeypatch):
    calls = {"search": [], "alts": []}

    def search_programs(q, profile, k=6):
        calls["search"].append(q)
        return [{**BASICS, "_score": 0.9}, {**DATA, "_score": 0.7}, {**CODING_DAY, "_score": 0.8},
                {**IT_EVENING, "_score": 0.6}]

    def alternative_training(profile, housing_type=None, k=4):
        calls["alts"].append(profile.get("goal"))
        return {"alternatives": [{"id": "other-city-job-training", "program": "Other City job training",
                                  "_why": "Free training for your goal · confirm current openings"}],
                "supports": [{"id": "sf-child-care", "program": "San Francisco child care support", "_why": "Helps with child care"}],
                "query": {"size": 4}, "supports_query": None, "took_ms": 3, "source": "test"}

    monkeypatch.setattr(main, "_search", lambda: types.SimpleNamespace(search_programs=search_programs))
    monkeypatch.setattr(main, "_resources", lambda: types.SimpleNamespace(alternative_training=alternative_training))
    monkeypatch.setattr(main, "_cat", lambda: types.SimpleNamespace(get_property=lambda c: None, load_properties=lambda: []))
    monkeypatch.setattr(main, "_attach_live_checks", lambda items: None)
    return TestClient(main.app), calls


def _profile(**kw):
    base = {"language": "vi", "goal": "Learn data analytics", "in_scope": True, "needs_clarification": False,
            "availability": "evenings", "hours_per_week_available": 8, "career_tracks": ["data analytics"],
            "children": 0, "needs_childcare": False, "has_computer": True, "search_query": "data analytics evenings"}
    return {**base, **kw}


def test_goal_program_beats_basics_when_both_fit(api):
    c, _ = api
    progs = c.post("/api/match", json={"profile": _profile()}).json()["programs"]
    assert progs[0]["id"] == "data-analytics" and progs[0]["match_role"] == "goal" and progs[0]["goal_match"]
    assert progs[1]["id"] == "basics-evening" and progs[1]["match_role"] == "on_ramp"
    assert progs[0]["fit"].startswith("Matches your goal") and progs[1]["fit"].startswith("On-ramp")


def test_goal_program_with_schedule_conflict_ranks_after_on_ramp_before_unrelated(api):
    c, _ = api
    p = _profile(goal="Learn coding", career_tracks=["software development"])
    progs = c.post("/api/match", json={"profile": p}).json()["programs"]
    ids = [x["id"] for x in progs]
    assert ids[:2] == ["basics-evening", "coding-day"]  # on-ramp, then the goal program (labelled conflict)
    assert all(ids.index("coding-day") < ids.index(x) for x in ("data-analytics", "it-evening"))
    coding = next(x for x in progs if x["id"] == "coding-day")
    assert coding["match_role"] == "goal" and coding["schedule_fit"] is False and "schedule conflict" in coding["fit"]


def test_it_goal_puts_evening_it_first(api):
    c, _ = api
    p = _profile(language="es", goal="IT support job", career_tracks=["digital basics", "IT support"])
    progs = c.post("/api/match", json={"profile": p}).json()["programs"]
    assert progs[0]["id"] == "it-evening" and progs[1]["id"] == "basics-evening"


def test_clarification_returns_follow_up_and_no_search(api):
    c, calls = api
    p = _profile(goal=None, needs_clarification=True, follow_up="What work would you like?", career_tracks=[])
    r = c.post("/api/match", json={"profile": p}).json()
    assert r["needs_clarification"] is True and r["programs"] == [] and r["follow_up"] == "What work would you like?"
    assert calls["search"] == [] and calls["alts"] == []


def test_out_of_scope_returns_alternatives_not_tech_programs(api):
    c, calls = api
    p = _profile(language="es", goal="Become a medical assistant", in_scope=False, career_tracks=[],
                 scope_note="Bridgeline se enfoca en tecnología...", children=3, needs_childcare=True)
    r = c.post("/api/match", json={"profile": p}).json()
    assert r["out_of_scope"] is True and r["programs"] == []
    assert r["alternatives"][0]["program"] == "Other City job training" and r["alternatives"][0]["_why"]
    assert r["supports"][0]["program"] == "San Francisco child care support"
    assert r["scope_note"].startswith("Bridgeline")
    assert calls["search"] == [] and calls["alts"] == ["Become a medical assistant"]


def test_out_of_scope_with_computer_wish_offers_only_basics(api):
    c, _ = api
    p = _profile(goal="Become a nurse", in_scope=False, wants_digital_skills=True, career_tracks=["digital basics"])
    r = c.post("/api/match", json={"profile": p}).json()
    assert r["out_of_scope"] is True
    assert [x["id"] for x in r["programs"]] == ["basics-evening"]
    assert r["programs"][0]["match_role"] == "on_ramp"


# ---------------------------------------------------------------- resources: age and alternatives


def test_volunteered_age_adds_audience_tag_only_then():
    assert "older-adults" in resources.wanted_tags({"age_group": "55_plus"})
    assert "youth" in resources.wanted_tags({"age_group": "under_25"})
    plain = resources.wanted_tags({})
    assert "older-adults" not in plain and "youth" not in plain


def test_senior_query_boosts_older_adults_and_never_demotes_them():
    q = resources.build_query({"age_group": "55_plus", "goal": "Learn email"})["query"]
    negative = q["boosting"]["negative"]
    assert negative["bool"]["must_not"] == [{"terms": {"tags": ["older-adults"]}}]
    should = q["boosting"]["positive"]["bool"]["should"]
    assert {"term": {"tags": {"value": "older-adults", "boost": 1.0}}} in should


def test_digital_basics_alone_is_not_a_job_search():
    assert resources.seeks_job({"career_tracks": ["digital basics"], "goal": "Learn email and video calls"}) is False
    assert resources.seeks_job({"career_tracks": ["IT support"]}) is True


def test_alternatives_query_excludes_tech_only_and_closed():
    q = resources.alternatives_query({"goal": "Become a medical assistant"})["query"]["bool"]
    must_not = q["must_not"]
    assert {"term": {"status": resources.CLOSED}} in must_not
    assert {"terms": {"id": resources.TECH_ONLY_IDS}} in must_not
    assert "medical assistant" in q["must"][0]["semantic"]["query"]


def test_supports_query_only_when_needed():
    assert resources.supports_query({"needs_childcare": False, "commute": "walk", "has_computer": True}) is None
    sq = resources.supports_query({"needs_childcare": True, "commute": "muni"})
    assert sq["query"]["bool"]["filter"] == [{"terms": {"tags": ["childcare", "transit"]}}]


def test_alternative_training_reads_both_searches(monkeypatch):
    class FakeES:
        def __init__(self):
            self.n = 0

        def search(self, index, **body):
            self.n += 1
            src = ({"id": "other-city-job-training", "program": "Other City job training", "status": "Confirm", "tags": ["training"]}
                   if self.n == 1 else
                   {"id": "sf-child-care", "program": "SF child care support", "status": "Available", "tags": ["childcare"]})
            return {"hits": {"hits": [{"_source": src, "_score": 1.0}]}}

    monkeypatch.setattr(resources, "_es", lambda: FakeES())
    out = resources.alternative_training({"goal": "Become a medical assistant", "needs_childcare": True}, k=4)
    assert out["alternatives"][0]["_why"] == "Free training for your goal · confirm current openings"
    assert out["supports"][0]["program"] == "SF child care support"
