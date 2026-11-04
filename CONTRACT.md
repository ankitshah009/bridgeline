# Bridgeline: build contract (shared by all agents)

Hack night: Mistral AI x Elastic "Make SF Better", 2026-11-03. Demo at 7:30 PM PT. **Hard stop for agent work: 6:50 PM PT.**
Stack: Python 3.14 + uv, FastAPI, `elasticsearch` 9.x client, `mistralai` 3.x SDK, vanilla HTML/CSS/JS (no node on this machine).
Settings: `app/config.py` (already written; import from it, do not redefine env handling).

## File ownership (edit only your files)

| Owner | Files |
|---|---|
| A: data + Elastic | `app/data/programs.json`, `app/data/properties.json`, `app/data/funding_sources.json`, `app/data/pilot_cohort.json`, `app/catalog.py`, `app/search.py`, `scripts/setup_elastic.py`, `tests/test_catalog.py`, `tests/test_search.py` |
| B: API + Mistral + rules | `app/main.py`, `app/ai.py`, `app/rules.py`, `tests/test_rules.py`, `tests/test_api.py` |
| C: web UI | `web/**` (index.html, navigator.html, impact.html, css, js, svg) |

## Program document (`app/data/programs.json`: list of these)

```json
{
  "id": "per-scholas-it-support",
  "name": "IT Support (CompTIA A+ prep)",
  "provider": "Per Scholas San Francisco Bay",
  "level": "basics | entry | career",
  "career_tracks": ["IT support", "help desk"],
  "description": "Plain-language description used for semantic search.",
  "tuition_usd": 0,
  "materials_usd": 0,
  "exam_fees_usd": 0,
  "schedule": "full-time-day | part-time-day | part-time-evening | self-paced",
  "hours_per_week": 40,
  "weeks": 15,
  "format": "in-person | hybrid | online",
  "neighborhood": "SoMa",
  "location": {"lat": 37.78, "lon": -122.40},
  "languages": ["en"],
  "requirements": ["..."],
  "stipend": false,
  "free_to_resident": true,
  "wioa_etpl": false,
  "workforce_pell_candidate": false,
  "isa_or_required_loan": false,
  "published_outcomes": null,
  "refund_policy": true,
  "url": "https://...",
  "illustrative": false,
  "verify_note": "Confirm current cohort dates and eligibility with provider."
}
```
`published_outcomes` is `null` unless a number is publicly published; never invent rates. Entries that are not a specific real program get `"illustrative": true`.

## Profile (output of Mistral intake, input to matching and rules)

```json
{
  "language": "es",
  "goal": "Get an entry-level IT support job",
  "career_tracks": ["IT support"],
  "experience": "Uses smartphone daily, little computer experience",
  "current_work": "Home health aide, daytime, ~35 h/week",
  "availability": "evenings | daytime | weekends | full-time | flexible",
  "hours_per_week_available": 10,
  "needs_childcare": true,
  "children": 2,
  "has_computer": false,
  "commute": "muni",
  "summary": "One-sentence English summary for the navigator",
  "search_query": "English query for semantic search, e.g. 'part-time evening IT support training for beginners'"
}
```

## Python interfaces

`app/search.py` (A):
- `es_client() -> Elasticsearch | None` (None if ES_URL/ES_API_KEY missing)
- `es_status() -> dict` with `{"connected": bool, "cluster": str|None, "inference_id": str|None, "programs": int, "applications": int, "error": str|None}`
- `search_programs(query: str, profile: dict, k: int = 6) -> list[dict]` returns program dicts plus `"_score": float` and `"_why": str` (highlight or matched track). Uses semantic search on `description` (semantic_text) combined with filters/boosts from profile (schedule fit, free first). Raises on ES failure (no fake results).
- `save_application(doc: dict) -> dict`, `get_application(app_id: str) -> dict | None`, `list_applications() -> list[dict]`, `update_application(app_id: str, patch: dict) -> dict`
- `impact_stats() -> dict`: aggregations over `homebase-applications` (includes the labelled simulated pilot cohort + live demo applications):
  `{"total": int, "by_status": {...}, "by_tier": {...}, "by_property": [{"property": str, "residents": int, "approved": int}], "dollars": {"free_program_value": float, "public_aid": float, "grant": float}, "outcomes": {"completed": int, "placed_or_raise": int}, "median_decision_days": float|None, "query": dict}` (`query` = the ES request body, shown on screen).

`app/catalog.py` (A): `load_programs()`, `load_properties()`, `load_funding_sources()`, `get_program(pid)`, `get_property(code)`.
`scripts/setup_elastic.py` (A): creates Mistral inference endpoint (`PUT _inference/text_embedding/homebase-mistral-embed`, service `mistral`, model `mistral-embed`) falling back to `.multilingual-e5-small-elasticsearch`, creates both indices, indexes programs and `pilot_cohort.json`. Idempotent; `--reset` flag.

`app/rules.py` (B), deterministic, no AI:
- `funding_waterfall(program: dict, profile: dict) -> dict`
  `{"lines": [{"item": "Tuition", "amount": 0.0, "payer": "free_program|public_aid|grant|resident", "payer_label": str, "paid_to": str, "note": str}], "totals": {"free_program": x, "public_aid": x, "grant": x, "resident": 0.0}, "tier": "starter|stay_in_training|career", "tier_cap": 2500, "within_cap": bool, "payment_schedule": [{"milestone": "enrollment|completion|placement", "pct": 50, "amount": x, "paid_to": str}], "assumptions": [str]}`
- `benefits_check(waterfall: dict, housing_type: str) -> {"status": "protected|review", "items": [{"line": str, "treatment": str, "cite": str, "ok": bool}], "summary": str}`
- `GRANT_TIERS`, `COST_ASSUMPTIONS` (labelled planning assumptions).

`app/ai.py` (B), Mistral:
- `parse_intake(text: str, language_hint: str | None) -> dict` (Profile, JSON mode)
- `draft_plan(profile, program, waterfall, benefits) -> {"headline": str, "steps": [str], "message": str (in resident's language), "navigator_note": str (English), "risks": [str]}`
AI drafts; it never decides eligibility or awards.

## HTTP API (`app/main.py`, B). All JSON. Errors: HTTP 502 `{"error": str, "stage": "mistral|elastic"}`.

| Method + path | Body | Response |
|---|---|---|
| GET `/api/health` | | `{"mistral": bool, "elastic": es_status()}` |
| GET `/api/properties` | | `[{"code","name","neighborhood","housing_type","units"}]` |
| POST `/api/join` | `{"property_code"}` | `{"property": {...}}` or 404 |
| POST `/api/intake` | `{"text", "language"?}` | `{"profile": Profile, "ms": int}` |
| POST `/api/match` | `{"profile", "property_code"?}` | `{"programs": [program + {"waterfall": ..., "fit": str}], "query": str, "ms": int}` (free/lowest resident cost first) |
| POST `/api/plan` | `{"profile", "program_id", "property_code"}` | `{"program", "waterfall", "benefits", "plan"}` |
| POST `/api/applications` | `{"profile", "program_id", "property_code", "waterfall", "benefits", "plan"}` | `{"application"}` |
| GET `/api/applications` | | `{"applications": [...]}` newest first |
| GET `/api/applications/{id}` | | `{"application"}` |
| POST `/api/applications/{id}/decision` | `{"action": "approve|request_info|decline", "reviewer", "note"}` | `{"application"}` |
| POST `/api/applications/{id}/milestone` | `{"milestone": "enrolled|completed|placed"}` | `{"application"}` (appends to `payments`) |
| GET `/api/impact` | | `impact_stats()` + `{"budget": {...pilot budget...}}` |

Pages: `/` -> `web/index.html` (resident), `/navigator` -> `web/navigator.html`, `/impact` -> `web/impact.html`, `/static/*` -> `web/`.

## Application document

```json
{
  "id": "HB-2026-0042", "created_at": "ISO", "status": "submitted|in_review|approved|needs_info|declined|enrolled|completed|placed",
  "property_code": "MISSION-24", "property_name": "...", "housing_type": "LIHTC|public_housing|project_based|voucher",
  "language": "es", "profile": {...}, "program_id": "...", "program_name": "...", "provider": "...",
  "tier": "stay_in_training", "grant_amount": 2140.0, "free_program_value": 0.0, "public_aid": 0.0,
  "waterfall": {...}, "benefits": {...}, "plan": {...},
  "risk": "low|medium|high", "risk_reasons": [str],
  "decision": {"action", "reviewer", "note", "at"} | null, "decision_days": float | null,
  "payments": [{"milestone", "amount", "paid_to", "at"}],
  "outcome": {"completed": bool, "placed_or_raise": bool} ,
  "simulated": false
}
```
Pilot cohort docs have `"simulated": true` and the UI labels them "simulated pilot cohort (illustrative)".

## Rules everywhere
- No cash to residents, ever. Grants pay providers/vendors. No stipends in the pilot.
- Never collect or display race or immigration status.
- Operators/funders see only aggregates (no names, no individual rows on /impact).
- If Mistral or Elastic fails, show the failure; never fake a match.
- No AI or agent attribution in code comments, commits or UI copy.
