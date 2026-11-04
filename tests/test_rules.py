from app import rules

SPANISH_MOM = {
    "language": "es", "availability": "evenings", "hours_per_week_available": 8,
    "needs_childcare": True, "children": 2, "has_computer": False, "commute": "muni",
}

FREE_EVENING = {
    "id": "free-evening-it", "name": "Evening IT Support", "provider": "City College of San Francisco",
    "tuition_usd": 0, "materials_usd": 0, "exam_fees_usd": 0, "schedule": "part-time-evening",
    "hours_per_week": 6, "weeks": 8, "format": "in-person", "free_to_resident": True,
    "wioa_etpl": False, "stipend": False,
}

PAID_NON_ETPL = {
    "id": "paid-bootcamp", "name": "Data Analytics Bootcamp", "provider": "Example Bootcamp",
    "tuition_usd": 3500, "materials_usd": 0, "exam_fees_usd": 0, "schedule": "part-time-evening",
    "hours_per_week": 10, "weeks": 12, "format": "online", "free_to_resident": False, "wioa_etpl": False,
}

PAID_ETPL = {**PAID_NON_ETPL, "id": "etpl", "provider": "ETPL College", "wioa_etpl": True, "tuition_usd": 7000}


def _lines(wf, payer):
    return [l for l in wf["lines"] if l["payer"] == payer]


def test_spanish_mom_free_evening_program_is_stay_in_training_with_zero_resident_cost():
    wf = rules.funding_waterfall(FREE_EVENING, SPANISH_MOM)
    assert wf["tier"] == "stay_in_training"
    assert wf["totals"]["resident"] == 0
    assert wf["within_cap"] is True
    assert wf["cash_to_resident"] == 0
    items = {l["item"] for l in _lines(wf, "grant")}
    assert {"Child care", "Transit", "Laptop"} <= items
    # Every grant dollar goes to a named vendor, never the resident.
    for line in _lines(wf, "grant"):
        assert line["paid_to"] and "resident" not in line["paid_to"].lower()
    # Child care per household: one provider for both kids, $15/h, 6 h x 8 weeks.
    cc = next(l for l in wf["lines"] if l["item"] == "Child care")
    assert cc["amount"] == 15 * 6 * 8
    assert wf["totals"]["grant"] <= wf["tier_cap"]
    assert _lines(wf, "free_program")[0]["payer_label"].startswith("Free program")


def test_paid_non_etpl_tuition_goes_to_career_tier_with_milestone_split():
    wf = rules.funding_waterfall(PAID_NON_ETPL, {"has_computer": True})
    assert wf["tier"] == "career"
    tuition = [s for s in wf["payment_schedule"] if s["item"].startswith("Tuition")]
    assert [s["pct"] for s in tuition] == [50, 30, 20]
    assert [s["milestone"] for s in tuition] == ["enrollment", "completion", "placement"]
    assert sum(s["amount"] for s in tuition) == 3500
    assert wf["totals"]["public_aid"] == 0


def test_etpl_program_uses_public_aid_first_and_grant_only_for_remainder():
    wf = rules.funding_waterfall(PAID_ETPL, {"has_computer": True})
    assert wf["totals"]["public_aid"] == 6000
    assert wf["totals"]["grant"] == 1000
    assert wf["lines"][0]["payer"] == "public_aid"
    assert any("job center" in n for n in wf["notes"])


def test_over_cap_shows_gap_honestly():
    long_program = {**FREE_EVENING, "hours_per_week": 20, "weeks": 16}
    wf = rules.funding_waterfall(long_program, {**SPANISH_MOM, "children": 3})
    assert wf["tier"] == "stay_in_training"
    assert wf["totals"]["grant"] == 2500
    assert wf["totals"]["resident"] > 0
    assert wf["within_cap"] is False
    assert any("free alternative" in n for n in wf["notes"])
    # Child care is funded first.
    assert any(l["item"] == "Child care" and l["payer"] == "grant" for l in wf["lines"])


def test_small_need_is_starter():
    wf = rules.funding_waterfall({**FREE_EVENING, "format": "online", "exam_fees_usd": 120}, {"has_computer": False})
    assert wf["tier"] == "starter"
    assert wf["totals"]["grant"] == 470


def test_benefits_protected_for_lihtc():
    wf = rules.funding_waterfall(FREE_EVENING, SPANISH_MOM)
    check = rules.benefits_check(wf, "LIHTC")
    assert check["status"] == "protected"
    assert "No cash" in check["summary"]
    assert "not legal advice" in check["disclaimer"]


def test_benefits_review_for_voucher_household_with_education_lines():
    wf = rules.funding_waterfall(FREE_EVENING, SPANISH_MOM)  # laptop counts as education equipment
    check = rules.benefits_check(wf, "voucher")
    assert check["status"] == "review"
    assert any(i["line"] == "Section 8 student rule" and not i["ok"] for i in check["items"])


def test_benefits_review_when_gap_line_exists_is_not_flagged_as_cash():
    wf = rules.funding_waterfall({**FREE_EVENING, "hours_per_week": 20, "weeks": 16}, SPANISH_MOM)
    check = rules.benefits_check(wf, "public_housing")
    cash = next(i for i in check["items"] if i["line"] == "Cash to resident")
    assert cash["ok"] is True


def test_benefits_other_housing_types_need_operator_review():
    wf = rules.funding_waterfall(FREE_EVENING, {**SPANISH_MOM, "has_computer": True})
    for ht in ("inclusionary", "small_sites", "supportive", "other", "", None):
        check = rules.benefits_check(wf, ht)
        assert check["status"] == "review"
        assert any("Operator confirms program type" in i["treatment"] for i in check["items"])


def test_isa_provider_gets_no_grant():
    isa = {**PAID_NON_ETPL, "isa_or_required_loan": True}
    wf = rules.funding_waterfall(isa, {"has_computer": True})
    assert wf["approved_provider"] is False
    assert wf["totals"]["grant"] == 0
    assert any("income-share" in n for n in wf["notes"])


def test_program_stipend_triggers_benefits_review():
    wf = rules.funding_waterfall({**FREE_EVENING, "stipend": True}, {**SPANISH_MOM, "has_computer": True})
    check = rules.benefits_check(wf, "LIHTC")
    assert check["status"] == "review"
    assert any(i["line"] == "Program stipend" for i in check["items"])


def test_self_paced_program_budgets_no_childcare():
    wf = rules.funding_waterfall({**PAID_NON_ETPL, "schedule": "self-paced", "tuition_usd": 294}, SPANISH_MOM)
    assert not any(l["item"] == "Child care" for l in wf["lines"])
    assert any("Self-paced" in n for n in wf["notes"])


def test_long_evening_certificate_fits_stay_in_training_one_term_at_a_time():
    ccsf_cert = {**FREE_EVENING, "id": "ccsf-it-support-certificate", "hours_per_week": 8, "weeks": 34, "materials_usd": 150}
    wf = rules.funding_waterfall(ccsf_cert, SPANISH_MOM)
    assert wf["tier"] == "stay_in_training"
    assert wf["totals"]["resident"] == 0
    assert wf["totals"]["grant"] <= 2500
    assert wf["term_weeks"] == 16 and wf["terms"] == 3
    assert any("Covers term 1 of 3" in n and "renews at navigator check-in" in n for n in wf["notes"])
    cc = next(l for l in wf["lines"] if l["item"] == "Child care")
    assert cc["amount"] == 15 * 8 * 16


def test_short_program_has_single_term_and_no_renewal_note():
    wf = rules.funding_waterfall(FREE_EVENING, SPANISH_MOM)
    assert wf["terms"] == 1
    assert not any("renews" in n for n in wf["notes"])


def test_free_seat_value_reported_as_leverage_not_cost():
    career = {**FREE_EVENING, "level": "career"}
    wf = rules.funding_waterfall(career, SPANISH_MOM)
    assert wf["totals"]["free_program_value"] == 4500
    assert wf["totals"]["resident"] == 0
    free_line = next(l for l in wf["lines"] if l["payer"] == "free_program")
    assert "covered free by City College of San Francisco (est. value $4,500)" in free_line["item"]
    assert rules.funding_waterfall({**FREE_EVENING, "level": "basics"}, SPANISH_MOM)["totals"]["free_program_value"] == 300
    assert rules.funding_waterfall({**FREE_EVENING, "level": None}, SPANISH_MOM)["totals"]["free_program_value"] == 1200
    assert rules.funding_waterfall(PAID_NON_ETPL, SPANISH_MOM)["totals"]["free_program_value"] == 0
