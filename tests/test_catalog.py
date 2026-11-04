from collections import Counter

from app import catalog

REQUIRED_PROGRAM_KEYS = {
    "id", "name", "provider", "level", "career_tracks", "description", "tuition_usd", "materials_usd",
    "exam_fees_usd", "schedule", "hours_per_week", "weeks", "format", "neighborhood", "location", "languages",
    "requirements", "stipend", "free_to_resident", "wioa_etpl", "workforce_pell_candidate",
    "isa_or_required_loan", "published_outcomes", "refund_policy", "url", "illustrative", "verify_note",
}
SCHEDULES = {"full-time-day", "part-time-day", "part-time-evening", "self-paced"}
FORBIDDEN = {"race", "ethnicity", "immigration_status", "citizenship", "name", "first_name", "last_name", "ssn"}


def test_programs_complete_and_honest():
    programs = catalog.load_programs()
    assert 14 <= len(programs) <= 18
    ids = [p["id"] for p in programs]
    assert len(ids) == len(set(ids))
    for p in programs:
        assert REQUIRED_PROGRAM_KEYS <= p.keys(), p["id"]
        assert p["schedule"] in SCHEDULES, p["id"]
        assert p["level"] in {"basics", "entry", "career"}
        assert p["published_outcomes"] is None, "never invent outcome rates"
        assert p["verify_note"].strip()
        assert len(p["description"]) > 80
        assert -123 < p["location"]["lon"] < -122 and 37.6 < p["location"]["lat"] < 37.9
    levels = Counter(p["level"] for p in programs)
    assert all(levels[l] >= 3 for l in ("basics", "entry", "career"))
    assert any(p["illustrative"] for p in programs)
    assert any(p["free_to_resident"] and p["schedule"] == "part-time-evening" and p["level"] == "career" for p in programs)


def test_per_scholas_matches_design_doc():
    p = catalog.get_program("per-scholas-it-support")
    assert p["tuition_usd"] == 0 and p["free_to_resident"] and not p["stipend"]
    assert p["schedule"] == "full-time-day" and p["hours_per_week"] == 40


def test_properties():
    props = catalog.load_properties()
    assert len(props) == 6
    assert len({p["code"] for p in props}) == 6
    assert all("(demo)" in p["name"] for p in props)
    assert {p["housing_type"] for p in props} == {"LIHTC", "public_housing", "project_based", "voucher"}
    assert 950 <= sum(p["units"] for p in props) <= 1100
    assert catalog.get_property(" mission-24 ")["name"] == "Mission Commons (demo)"
    assert catalog.get_property("NOPE") is None


def test_funding_sources_in_order():
    sources = catalog.load_funding_sources()
    assert [s["order"] for s in sources] == sorted(s["order"] for s in sources)
    assert sources[0]["id"] == "free_program" and sources[-1]["id"] == "homebase_grant"
    assert next(s for s in sources if s["id"] == "wioa_ita")["cap_usd"] == 6000


def test_pilot_cohort_is_labelled_and_safe():
    cohort = catalog.load_pilot_cohort()
    assert 40 <= len(cohort) <= 60
    program_ids = {p["id"] for p in catalog.load_programs()}
    codes = {p["code"] for p in catalog.load_properties()}
    caps = {"starter": 500, "stay_in_training": 2500, "career": 6000}
    for d in cohort:
        assert d["simulated"] is True and d["id"].startswith("SIM-")
        assert d["program_id"] in program_ids and d["property_code"] in codes
        assert d["grant_amount"] <= caps[d["tier"]]
        assert not (FORBIDDEN & d.keys()) and not (FORBIDDEN & d["profile"].keys())
        if d["decision_days"] is not None:
            assert 0 < d["decision_days"] <= 14
        for pay in d["payments"]:
            assert "resident" not in pay["paid_to"].lower(), "grants are never paid to residents"
    statuses = Counter(d["status"] for d in cohort)
    assert statuses["placed"] and statuses["completed"] and statuses["enrolled"] and statuses["declined"]


def test_resident_cost_and_search_text():
    p = catalog.get_program("illustrative-etpl-network-technician")
    assert catalog.resident_cost(p) == 5200 + 300 + 370
    assert "network" in catalog.search_text(p).lower()
