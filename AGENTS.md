# Bridgeline: agent instructions

Hack-night project for Make SF Better (Mistral AI x Elastic), 2026-11-03. Read `CONTRACT.md` first; it fixes file ownership, data shapes and the HTTP API.

- Stack: Python 3.14 via `uv`, FastAPI, `elasticsearch` 9.x, `mistralai` 3.x, vanilla HTML/CSS/JS served by FastAPI. No node.
- Run API: `uv run uvicorn app.main:app --reload --port 8010`. UI: `cd frontend && npx next dev -p 3000` (Next.js 16, proxies `/api` to `HOMEBASE_API_URL` from `frontend/.env.local`). Node via nvm (`~/.nvm/versions/node/v26.13.0/bin`).
- Seed Elastic: `uv run python scripts/setup_elastic.py --reset` and `uv run python scripts/load_opendata.py --reset` (DataSF MOHCD portfolio).
- `web/` is the original vanilla reference UI; the shipped UI is `frontend/`.
- Secrets live in `.env` (`MISTRAL_API_KEY`, `ES_URL`, `ES_API_KEY`), never committed; `.env.example` has no values.
- Tests: `uv run pytest -n auto` (never serial). Tests must not need network; mock Mistral and Elastic.
- Real calls only in the demo. If a stage fails, show the failure; never fake a match.
- Grants are paid to providers and vendors, never as cash to residents. Race and immigration status are never collected.
- AI drafts plans and translates; it never decides eligibility or awards.
- Commits: no AI or agent attribution of any kind.
