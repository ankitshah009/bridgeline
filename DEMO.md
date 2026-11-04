# Bridgeline: 90-second demo

**Live site:** https://bridgeline-sf.vercel.app (same Mistral + Elastic Cloud backend as local; applications made on either show up on both).

**One line:** A text-message link that takes a resident of San Francisco affordable housing from "I want a better job" to a funded seat in tech training, with $0 out of pocket and no risk to their rent.

## Setup (before going on stage)

```bash
# one-time: seed Elastic Cloud (already done on 2026-11-03)
uv run python scripts/setup_elastic.py --reset   # Mistral inference endpoint + programs + simulated cohort
uv run python scripts/load_opendata.py --reset   # DataSF MOHCD portfolio -> Elastic

# run (two terminals)
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010     # API (Mistral Large + Elastic Cloud)
cd frontend && npx next dev -p 3000                          # Next.js UI, proxies /api -> :8010 (frontend/.env.local)
```
**Right before going on stage:** `uv run python scripts/reset_demo.py --yes` (deletes live test applications, keeps the
simulated cohort), then open `http://localhost:3000/?new=1` (clears the resident's saved state).

Open four tabs on http://localhost:3000: `/?new=1` in a phone-width window, `/navigator`, `/impact`, `/directory`.
Check http://localhost:3000/api/health shows `mistral: true`, `mistral_model: mistral-large-latest`, `elastic.connected: true`.
Backup Elastic: `set -a; . ./.env.local-es; set +a` before starting uvicorn switches to the fully seeded local container `homebase-es`.

**Measured live on 2026-11-03 (Elastic Cloud serverless 9.7 + Mistral Large):** intake 4.1 s, match 0.5 s, plan 5.0 s,
apply 0.4 s, approve 0.7 s, impact 0.2 s. Spanish 2-kids evening profile → CCSF evening IT certificate, Stay-in-Training,
grant $2,442 paid to child care / SFMTA Lifeline / device vendor, resident $0, benefits shield "protected" (LIHTC).
On Match, tap **Computer Technician / IT Support Certificate** (second card) for the career story; the first card is the
digital-basics on-ramp.

## Script (about 90 s)

**0:00 The problem (impact tab, DataSF panel on screen)**
"San Francisco has [buildings on screen] affordable rental buildings and [units on screen] income-restricted homes. That's live city open data, aggregated in Elasticsearch. The best tech training here is already free: Per Scholas, TechSF. But Per Scholas runs 12 to 16 weeks at 40 hours a week with no stipend. For a parent working days, tuition isn't the barrier. Child care, the bus and a laptop are."

**0:15 The resident (phone)**
Join with the demo property code. On the Plan step, tap the Spanish chip:
*"Trabajo de día cuidando ancianos, tengo dos hijos y quiero trabajar en computadoras. Solo puedo estudiar en la noche."*
"She types in her own language. Mistral turns it into a plan profile: IT, evenings only, two kids, no laptop. The app switches to Spanish."

**0:30 The match**
"Elasticsearch runs semantic search over the SF training catalog with Mistral embeddings. The query was Spanish and the catalog is English. Free options come first, ranked by whether they fit her evenings."
Open the top match.

**0:40 Who pays**
"Tuition is covered by the free program. Our grant covers the rest: child care, a Muni pass, a laptop. It pays the providers directly, so her cost is **$0**."
Point to the yellow **Check first** notes: "Last dollar means last. Before our grant pays for child care, she's routed to San Francisco's free child care support, and to Clipper START for half-price transit. Those come from 34 local programs we researched, indexed in Elastic."
Point to the **Benefits Shield**: "No cash ever reaches her, so the grant is designed not to raise her rent under HUD's income rule. Before every award, a navigator confirms that with the operator."

**0:55 The navigator (navigator tab)**
Her application is at the top with risk flags. "Mistral drafted this plan, and it's labelled as a draft. AI never decides eligibility or awards; a person does." Click **Approve**.
Phone: the status flips to **Approved** live.
Click **Enrolled**: "The first payment goes to the provider, not to her."

**1:10 The proof (impact tab, opens on Live)**
"This page counts only real applications, live from Elasticsearch. A minute ago it said no live applications. Now it shows her approved grant." Then flip the toggle to **Pilot model**: "Here is the pilot we are modelling, with the simulated cohort clearly labelled: the funnel, free and public dollars leveraged against grant dollars, and the 10-day decision time."
"The pilot covers 1,000 units at about $18,000 per resident who finishes and gets hired or raises their pay. Randomized studies of sector-focused training found 11 to 40% higher earnings. That's the model we're funding: training plus support plus a navigator."

**(If time) Directory tab**
"Everything free in SF in one place: programs, free help and our three grant templates, browsable as carousels. Search works in any language." Type *cuidado de niños gratis* to show semantic search returning SF child care support.

**1:25 Close**
"Bridgeline. Free training first, our grant for the rest, and $0 for the resident. Built tonight on Mistral and Elastic."

## If something breaks
- Do **not** click "Re-check sources" on stage. It calls Mistral for every source and can hit the rate limit while you demo intake.
- Mistral 429 (rate limit): the app retries for up to 7 s, then shows a red card. Wait a few seconds and tap again.
- If Mistral or Elastic fails, the UI shows a red card naming the stage. Say so and retry; never fake a result.
- If the network is slow, `load_opendata.py --snapshot` loads the committed DataSF snapshot.

## Honest caveats (say them if asked)
- Program facts come from public listings. Each card says to confirm cohort dates and eligibility with the provider.
- The pilot cohort on the impact page is **simulated** and labelled that way. Live demo applications are real records in Elastic.
- Demo properties are fictional. The DataSF buildings are real. Housing-type mapping from MOHCD program is an inference for routing, and the operator confirms it.
- Benefits treatment is planning guidance, not legal advice. Counsel and each operator's compliance team sign off before launch.

## Sponsor fit
- **Mistral:** multilingual intake (EN/ES/繁中/Filipino/Tiếng Việt), `mistral-embed` for semantic search inside Elastic (inference endpoint), drafted plans in the resident's language.
- **Elastic:** `semantic_text` + Mistral inference endpoint, hybrid ranking with filters, geo distance from home to training, aggregations for the impact page, plus SF open data (DataSF MOHCD portfolio, 850 buildings) and a 34-program free-help directory indexed alongside (4 indices: programs, applications, sf-housing, resources).
