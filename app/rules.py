"""Deterministic funding and benefits rules. No AI here.

Order of funding: free program, then public aid, then the Bridgeline grant for what is left.
The grant is always paid to providers and vendors, never to the resident as cash.
"""
from __future__ import annotations

import math

GRANT_TIERS: dict[str, dict] = {
    "starter": {
        "label": "Starter",
        "cap": 500,
        "covers": "Device, exam fee or short course.",
        "requires": "A goal and a navigator check-in.",
    },
    "stay_in_training": {
        "label": "Stay-in-Training",
        "cap": 2500,
        "covers": "Child care, transit, equipment and certification fees during a free program.",
        "requires": "Admission to an approved program.",
    },
    "career": {
        "label": "Career",
        "cap": 6000,
        "covers": "Tuition where no free or public option fits, plus eligible support costs.",
        "requires": "Admission, a completed funding check and a career plan.",
    },
}

# Planning assumptions for cost of attendance, not quotes. Shown on screen as assumptions.
COST_ASSUMPTIONS: dict[str, dict] = {
    "childcare_household_hour": {
        "value": 15.0,
        "note": ("Child care priced per household: one evening family child care provider for all siblings, "
                 "training hours only, $15/hour (planning assumption; confirm against SF market rates)."),
    },
    "award_term_weeks": {
        "value": 16.0,
        "note": "Support costs are awarded one term (up to 16 weeks) at a time and renew at a navigator check-in.",
    },
    "transit_month": {
        "value": 43.0,
        "note": "Muni Lifeline monthly pass, about half the adult fare (planning assumption; confirm current fare).",
    },
    "device": {
        "value": 350.0,
        "note": "Refurbished laptop from an approved vendor (planning assumption).",
    },
    "free_seat_career": {
        "value": 4500.0,
        "note": "Estimated value of a free career-level seat, $4,500 (planning assumption, used only to report leverage).",
    },
    "free_seat_entry": {
        "value": 1200.0,
        "note": "Estimated value of a free entry-level seat, $1,200 (planning assumption).",
    },
    "free_seat_basics": {
        "value": 300.0,
        "note": "Estimated value of a free digital-basics seat, $300 (planning assumption).",
    },
    "wioa_ita_cap": {
        "value": 6000.0,
        "note": "SF WIOA Individual Training Account cap: tuition and materials only, state-listed (ETPL) providers.",
    },
}

PAYER_LABELS = {
    "free_program": "Free program",
    "public_aid": "Public aid (WIOA ITA)",
    "grant": "Bridgeline grant",
    "resident": "You",
}

TUITION_SPLIT = [("enrollment", 50), ("completion", 30), ("placement", 20)]


def _num(value, default=0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _int(value, default=0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _a(key: str) -> float:
    return COST_ASSUMPTIONS[key]["value"]


def program_weeks(program: dict) -> int:
    return max(_int(program.get("weeks"), 12), 1)


def term_weeks(program: dict) -> int:
    return min(program_weeks(program), int(_a("award_term_weeks")))


def terms(program: dict) -> int:
    return math.ceil(program_weeks(program) / _a("award_term_weeks"))


def support_costs(program: dict, profile: dict) -> list[dict]:
    """Cost-of-attendance lines the grant may pay, each to a vendor."""
    weeks = term_weeks(program)
    hours = max(_num(program.get("hours_per_week"), 0), 0)
    fmt = (program.get("format") or "in-person").lower()
    lines: list[dict] = []

    children = _int(profile.get("children"), 0)
    if profile.get("needs_childcare") and children <= 0:
        children = 1
    scheduled = program.get("schedule") != "self-paced"
    if profile.get("needs_childcare") and hours > 0 and scheduled:
        amount = round(_a("childcare_household_hour") * hours * weeks, 2)
        lines.append({
            "item": "Child care",
            "kind": "support",
            "amount": amount,
            "paid_to": "Licensed child care provider",
            "note": f"{children} child{'ren' if children != 1 else ''}, one provider, {hours:g} h/week x {weeks} weeks, invoiced monthly",
        })

    if fmt != "online":
        months = math.ceil(weeks / 4.33)
        lines.append({
            "item": "Transit",
            "kind": "support",
            "amount": round(_a("transit_month") * months, 2),
            "paid_to": "SFMTA · Clipper START (50% off; Muni Lifeline moves here Jan 1, 2027)",
            "note": f"{months} month{'s' if months != 1 else ''} of Muni Lifeline passes loaded to Clipper",
        })

    if profile.get("has_computer") is False:
        lines.append({
            "item": "Laptop",
            "kind": "equipment",
            "amount": _a("device"),
            "paid_to": "Approved refurbished-device vendor",
            "note": "Delivered before day one; resident keeps it",
        })

    exam = _num(program.get("exam_fees_usd"))
    if exam > 0:
        lines.append({
            "item": "Certification exam fees",
            "kind": "education",
            "amount": round(exam, 2),
            "paid_to": "Exam vendor (voucher)",
            "note": "Voucher issued when the resident is ready to test",
        })
    return lines


# Free or discounted resources a navigator checks before the grant pays (last-dollar rule).
# Ids match app/data/resources.json. Amounts stay budgeted: the grant covers whatever these don't.
CHECKS_FIRST = {
    "Child care": {
        "resource_id": "san-francisco-child-care-support",
        "program": "San Francisco child care support",
        "note": "Check SF child care support first (free up to 110% AMI for eligible young children); grant covers what it doesn't",
    },
    "Transit": {
        "resource_id": "clipper-start",
        "program": "Clipper START",
        "note": "Enroll in Clipper START first (50% off for adults 19-64 at or below 200% FPL; Muni Lifeline moves here Jan 1, 2027; apply by Dec 1)",
    },
    "Laptop": {
        "resource_id": "tech-exchange-classes",
        "program": "Tech Exchange classes",
        "note": "Tech Exchange: finishers may receive a device \u2014 check first",
    },
}


def checks_first(lines: list[dict]) -> list[dict]:
    items = {l.get("item") for l in lines if (l.get("amount") or 0) > 0}
    return [dict(v) for k, v in CHECKS_FIRST.items() if k in items]


def free_seat_value(program: dict) -> float:
    explicit = _num(program.get("value_usd") or program.get("market_value_usd"))
    if explicit > 0:
        return explicit
    level = (program.get("level") or "entry").lower()
    key = f"free_seat_{level}" if f"free_seat_{level}" in COST_ASSUMPTIONS else "free_seat_entry"
    return _a(key)


def funding_waterfall(program: dict, profile: dict) -> dict:
    provider = program.get("provider") or program.get("name") or "Training provider"
    tuition = _num(program.get("tuition_usd")) + _num(program.get("materials_usd"))
    free = bool(program.get("free_to_resident")) or tuition <= 0
    lines: list[dict] = []
    assumptions = [v["note"] for v in COST_ASSUMPTIONS.values()]
    notes: list[str] = []

    # 1. Free program covers tuition.
    tuition_left = 0.0
    if free:
        value = free_seat_value(program)
        lines.append({
            "item": f"Tuition — covered free by {provider} (est. value ${value:,.0f})",
            "kind": "education",
            "amount": round(value, 2),
            "payer": "free_program",
            "payer_label": f"Free program ({provider})",
            "paid_to": provider,
            "note": "No tuition charged to the resident. Seat value is a planning estimate, used only to report leverage.",
        })
    else:
        # 2. Public aid: WIOA ITA for state-listed providers, tuition and materials only.
        tuition_left = tuition
        if program.get("wioa_etpl"):
            aid = min(tuition, _a("wioa_ita_cap"))
            tuition_left = round(tuition - aid, 2)
            lines.append({
                "item": "Tuition and materials",
                "kind": "education",
                "amount": round(aid, 2),
                "payer": "public_aid",
                "payer_label": "Public aid (WIOA ITA), route to job center first",
                "paid_to": provider,
                "note": "Eligibility and current funding confirmed by the SF job center. Grant pays only the remainder.",
            })
            notes.append("Navigator: refer to an SF job center for a WIOA ITA before any grant tuition is approved.")
        if program.get("workforce_pell_candidate"):
            notes.append("Workforce Pell may apply once California approves programs; re-check before award.")

    # 3. Bridgeline grant for the remainder, paid to vendors.
    grant_lines: list[dict] = []
    if tuition_left > 0:
        grant_lines.append({
            "item": "Tuition remainder" if program.get("wioa_etpl") else "Tuition and materials",
            "kind": "education",
            "amount": round(tuition_left, 2),
            "paid_to": provider,
            "note": "No free or public option fits; paid 50/30/20 at enrollment, completion and job placement.",
        })
    grant_lines.extend(support_costs(program, profile))
    need = round(sum(l["amount"] for l in grant_lines), 2)

    has_childcare = any(l["item"] == "Child care" for l in grant_lines)
    if need <= GRANT_TIERS["starter"]["cap"] and not has_childcare:
        tier = "starter"  # device, exam fee or short course
    elif tuition_left > 0:
        tier = "career"
    else:
        tier = "stay_in_training"
    n_terms = terms(program)
    if n_terms > 1:
        notes.append(f"Covers term 1 of {n_terms} ({term_weeks(program)} of {program_weeks(program)} weeks); "
                     "renews at navigator check-in.")
    if profile.get("needs_childcare") and program.get("schedule") == "self-paced":
        notes.append("Self-paced program: no scheduled class time, so no child care is budgeted. "
                     "Navigator can add care for fixed study blocks.")
    cap = GRANT_TIERS[tier]["cap"]

    # Approved providers only: no income-share agreements or required loans.
    approved = not program.get("isa_or_required_loan")
    if not approved:
        notes.append("Not grant-eligible: this provider uses an income-share agreement or a required loan. "
                     "Navigator: offer a free or approved alternative.")

    # Allocate within the cap. Child care first: it is the barrier that most often ends training.
    priority = {"Child care": 0, "Tuition and materials": 1, "Tuition remainder": 1, "Transit": 2, "Laptop": 3, "Certification exam fees": 4}
    remaining = float(cap) if approved else 0.0
    for line in sorted(grant_lines, key=lambda l: priority.get(l["item"], 9)):
        funded = round(min(line["amount"], remaining), 2)
        remaining = round(remaining - funded, 2)
        gap = round(line["amount"] - funded, 2)
        if funded > 0:
            lines.append({**line, "amount": funded, "payer": "grant", "payer_label": "Bridgeline grant"})
        if gap > 0:
            lines.append({
                **line,
                "amount": gap,
                "payer": "resident",
                "payer_label": "Unfunded gap" if approved else "Not grant-eligible",
                "paid_to": "Not yet funded",
                "note": ("Over the tier cap. Navigator: look for a free alternative or a public subsidy before award."
                         if approved else "Provider not approved (income-share agreement or required loan)."),
            })

    totals = {k: 0.0 for k in ("free_program", "public_aid", "grant", "resident")}
    for line in lines:
        totals[line["payer"]] = round(totals[line["payer"]] + line["amount"], 2)
    totals["free_program_value"] = totals["free_program"]
    within_cap = totals["resident"] == 0
    if not within_cap and approved:
        notes.append(f"Grant need ${need:,.0f} is over the {GRANT_TIERS[tier]['label']} cap of ${cap:,}. "
                     "Navigator: look for a free alternative or a public subsidy.")

    schedule: list[dict] = []
    for line in lines:
        if line["payer"] != "grant":
            continue
        if line["item"].startswith("Tuition"):
            for milestone, pct in TUITION_SPLIT:
                schedule.append({
                    "milestone": milestone, "pct": pct, "item": line["item"],
                    "amount": round(line["amount"] * pct / 100, 2), "paid_to": line["paid_to"],
                })
        else:
            milestone = "completion" if line["item"] == "Certification exam fees" else "enrollment"
            cadence = "monthly, as invoiced" if line["item"] in ("Child care", "Transit") else "once"
            schedule.append({
                "milestone": milestone, "pct": 100, "item": line["item"],
                "amount": line["amount"], "paid_to": line["paid_to"], "cadence": cadence,
            })

    return {
        "lines": lines,
        "checks_first": checks_first(lines),
        "totals": totals,
        "grant_need": need,
        "tier": tier,
        "tier_label": GRANT_TIERS[tier]["label"],
        "tier_cap": cap,
        "tier_requires": GRANT_TIERS[tier]["requires"],
        "within_cap": within_cap,
        "payment_schedule": schedule,
        "term_weeks": term_weeks(program),
        "terms": terms(program),
        "cash_to_resident": 0.0,
        "approved_provider": approved,
        "program_stipend": bool(program.get("stipend")),
        "notes": notes,
        "assumptions": assumptions,
    }


HOUSING_LABELS = {
    "LIHTC": "Low-Income Housing Tax Credit",
    "public_housing": "Public housing",
    "project_based": "Project-based Section 8",
    "voucher": "Housing Choice Voucher (Section 8)",
}

OTHER_HOUSING_LABELS = {
    "inclusionary": "Inclusionary (below-market-rate) unit",
    "small_sites": "Small Sites Program",
    "supportive": "Supportive or transitional housing",
    "other": "Other affordable housing",
}

DISCLAIMER ="Planning guidance, not legal advice. Housing counsel and the operator's compliance team sign off before launch."


def benefits_check(waterfall: dict, housing_type: str) -> dict:
    items: list[dict] = []
    section8 = housing_type in ("voucher", "project_based")
    paid_lines = [l for l in waterfall.get("lines", []) if l.get("payer") in ("grant", "public_aid") and l.get("amount", 0) > 0]

    items.append({
        "line": "Cash to resident",
        "treatment": "None. Every dollar goes to a provider or vendor, and the pilot pays no stipends, which may count as income.",
        "cite": "24 CFR 5.609",
        "ok": _num(waterfall.get("cash_to_resident")) == 0,
    })

    for line in paid_lines:
        kind = line.get("kind")
        if kind in ("education", "equipment"):
            items.append({
                "line": line["item"],
                "treatment": "Student financial assistance used for tuition, books, supplies and required fees is excluded from income, up to actual cost.",
                "cite": "24 CFR 5.609 (student financial assistance)",
                "ok": True,
            })
        else:
            direct = line.get("paid_to") and line.get("paid_to") != "Not yet funded"
            items.append({
                "line": line["item"],
                "treatment": ("Paid directly to the vendor, never to the household. Reimbursed support costs are excluded "
                              "for publicly assisted programs; for privately funded grants, counsel confirms before launch."),
                "cite": "24 CFR 5.609 (reimbursement of out-of-pocket costs)",
                "ok": bool(direct),
            })

    if waterfall.get("program_stipend"):
        items.append({
            "line": "Program stipend",
            "treatment": "The training provider pays its own stipend. Stipends are not excluded student aid and may count as income; compliance reviews before enrollment.",
            "cite": "24 CFR 5.609",
            "ok": False,
        })

    if section8 and any(l.get("kind") in ("education", "equipment") for l in paid_lines):
        items.append({
            "line": "Section 8 student rule",
            "treatment": "Section 8 households can be treated differently for student aid. Navigator confirms with the PHA or operator compliance before award.",
            "cite": "24 CFR 5.609; 24 CFR 5.612",
            "ok": False,
        })

    known = housing_type in HOUSING_LABELS
    items.append({
        "line": f"Housing program: {HOUSING_LABELS.get(housing_type) or OTHER_HOUSING_LABELS.get(housing_type) or (housing_type or 'unknown')}",
        "treatment": ("Written guidance from housing counsel and the operator's compliance team is on file for this program type."
                      if known else
                      "Operator confirms program type and income rules before award; guidance for this program type is not on file yet."),
        "cite": "Operator compliance sign-off",
        "ok": known,
    })

    status = "protected" if all(i["ok"] for i in items) else "review"
    if status == "protected":
        summary = "Paid straight to providers. No cash to you, so this grant is designed not to change your rent."
    else:
        summary = ("Paid straight to providers, with no cash to you. One item needs a compliance check for your housing "
                   "program before the award, and your navigator handles it.")
    return {"status": status, "items": items, "summary": summary, "disclaimer": DISCLAIMER}
