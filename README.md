# Bridgeline

**Free tech training for San Francisco affordable-housing residents, with $0 out of pocket and no risk to their rent.**

Built at the Mistral AI x Elastic "Make SF Better" hack night, November 3, 2026.

## The problem

San Francisco's best tech training is already free: Per Scholas, TechSF and Free City College. A parent working days still can't attend, because 12 to 16 weeks of classes means paying for child care, transit and a laptop. Cash help can raise the household's rent, since assisted rents are set by income (HUD, 24 CFR 5.609). DataSF lists **570 affordable rental buildings with 31,981 income-restricted homes**, all aggregated live in Elasticsearch.

## What Bridgeline does

1. **Join:** the resident opens a text-message link and enters their building code, or finds their real building in the DataSF portfolio.
2. **Plan:** they describe their situation in their own words, in English, Spanish, Traditional Chinese, Filipino or Vietnamese. **Mistral Large** turns that into a structured profile.
3. **Match:** **Elasticsearch** runs semantic search over the SF training catalog, using `semantic_text` with **Mistral embeddings** through an inference endpoint. Results are ranked free-first and by schedule fit.
4. **Who pays:** a deterministic waterfall decides who pays for what, in order: the free program, then public aid (WIOA ITA), then the Bridgeline grant. The grant pays child care, transit and device vendors directly. Free city help is checked first: SF child care support, Clipper START and Tech Exchange.
5. **Benefits shield:** every line is checked against HUD income rules. There are no cash stipends, every payment goes to a vendor, and anything the rules don't settle is flagged for counsel and operator review.
6. **Navigator:** a human reviews the plan Mistral drafted. AI never decides eligibility or awards. Approval releases milestone payments: 50% at enrollment, 30% at completion and 20% at placement.
7. **Impact:** funders see aggregates only, as Elastic aggregations: the funnel, dollars leveraged, decision time and cost per outcome.
8. **Directory:** a browsable marketplace of programs, 34 researched free-help resources and the grant tiers.

## Architecture

```mermaid
flowchart LR
    subgraph People
        R["Resident<br/>phone, any language"]
        N["Career navigator"]
        F["Funders and operators<br/>aggregates only"]
    end

    subgraph UI["Next.js 16 · frontend/"]
        P1["/ resident journey"]
        P2["/directory marketplace"]
        P3["/navigator console"]
        P4["/impact dashboard"]
    end

    subgraph API["FastAPI · app/"]
        AI["ai.py<br/>intake + plan drafts"]
        RU["rules.py<br/>who-pays waterfall<br/>benefits check"]
        SE["search.py · resources.py<br/>directory.py · opendata.py"]
    end

    subgraph Mistral["Mistral AI"]
        ML["mistral-large-latest"]
        ME["mistral-embed"]
    end

    subgraph Elastic["Elastic Cloud serverless"]
        INF["inference endpoint<br/>homebase-mistral-embed"]
        I1[("programs<br/>semantic_text")]
        I2[("resources<br/>researched free help")]
        I3[("sf-housing<br/>DataSF MOHCD portfolio")]
        I4[("applications<br/>aggregations")]
    end

    DS["DataSF open data<br/>pyxv-n29e"]

    R --> P1
    R --> P2
    N --> P3
    F --> P4
    UI -- "/api proxy" --> API
    AI --> ML
    SE --> I1 & I2 & I3 & I4
    I1 & I2 --> INF --> ME
    DS -- "load_opendata.py" --> I3
```

### The resident journey, end to end

```mermaid
sequenceDiagram
    autonumber
    actor R as Resident
    participant UI as Next.js
    participant API as FastAPI
    participant M as Mistral Large
    participant ES as Elasticsearch
    actor N as Navigator

    R->>UI: Building code, then "Trabajo de día, tengo dos hijos..."
    UI->>API: POST /api/intake
    API->>M: Extract profile (JSON mode)
    M-->>API: language es, evenings, 2 kids, no laptop
    UI->>API: POST /api/match
    API->>ES: Semantic query on programs (Mistral embeddings) + schedule fit
    ES-->>API: Free-first ranked programs
    UI->>API: POST /api/plan
    API->>API: Who-pays waterfall and benefits check (rules, no AI)
    API->>ES: Free help to check first (resources index)
    API->>M: Draft plan in the resident's language
    API-->>UI: $0 for you, paid to vendors, benefits protected
    R->>UI: Apply
    UI->>API: POST /api/applications
    API->>ES: Index application
    N->>API: Review AI draft, tick benefits checklist, Approve
    API->>ES: Decision and milestone payments to vendors
    UI-->>R: Status flips to Approved
```

### Who pays, in order

```mermaid
flowchart TD
    A["Cost of training:<br/>tuition, child care, transit, laptop, exam fees"] --> B{"Free program<br/>covers tuition?"}
    B -- "yes" --> C["Tuition: $0<br/>Per Scholas, TechSF, Free City College"]
    B -- "no" --> D{"State-listed provider?<br/>WIOA voucher up to $6,000"}
    D -- "yes" --> E["Public aid pays tuition and materials"]
    D -- "no" --> G
    C --> F{"Free help covers a support cost?<br/>SF child care support, Clipper START,<br/>Tech Exchange devices"}
    E --> F
    F -- "check first" --> G["Bridgeline grant pays what's left<br/>Starter $500 · Stay-in-Training $2,500 · Career $6,000"]
    G --> H["Paid straight to providers and vendors<br/>tuition 50% enroll · 30% complete · 20% placed"]
    H --> I{"Benefits check<br/>HUD 24 CFR 5.609"}
    I -- "protected" --> J["Resident pays $0<br/>no cash, so rent is not affected"]
    I -- "review" --> K["Navigator confirms with the operator<br/>and counsel before award"]
```

### Application lifecycle

```mermaid
stateDiagram-v2
    [*] --> submitted: Resident applies
    submitted --> in_review: Navigator opens case
    in_review --> needs_info: Request info
    needs_info --> in_review: Resident replies
    in_review --> declined: Decline
    in_review --> approved: Approve (benefits checklist complete)
    approved --> enrolled: Enrolled · 50% tuition + support costs to vendors
    enrolled --> completed: Completed · 30% tuition
    completed --> placed: Job or raise verified · 20% tuition
    placed --> [*]: Outcomes at 30, 90, 180 days
    declined --> [*]
```

### Elasticsearch data model

```mermaid
erDiagram
    INFERENCE_ENDPOINT ||--o{ PROGRAMS : "embeds description"
    INFERENCE_ENDPOINT ||--o{ RESOURCES : "embeds text"
    PROGRAMS ||--o{ APPLICATIONS : "program_id"
    SF_HOUSING ||--o{ APPLICATIONS : "building_id (optional)"

    INFERENCE_ENDPOINT {
        string id "homebase-mistral-embed"
        string service "mistral"
        string model "mistral-embed"
    }
    PROGRAMS {
        semantic_text description
        keyword level
        keyword schedule
        float tuition_usd
        bool free_to_resident
        bool wioa_etpl
        geo_point location
    }
    RESOURCES {
        semantic_text text
        keyword category
        keyword status
        keyword tags
        bool housing_only
        keyword source_url
    }
    SF_HOUSING {
        keyword id "MOHCD development id"
        search_as_you_type name
        keyword neighborhood
        keyword program
        integer affordable_units
        geo_point location
    }
    APPLICATIONS {
        keyword id
        keyword status
        keyword tier
        float grant_amount
        float free_program_value
        float public_aid
        bool simulated
    }
```

### Roadmap

```mermaid
gantt
    title Bridgeline roadmap (from the program design)
    dateFormat YYYY-MM-DD
    axisFormat %b %Y
    section Validate
    Interviews, 2 operators, 3 training partners, counsel   :p0, 2026-11-01, 2027-01-31
    section Build MVP
    Resident app, navigator console, grant review           :p1, 2027-02-01, 2027-04-30
    section Pilot
    About 1,000 units, first grants, provider reporting     :p2, 2027-05-01, 2027-10-31
    section Prove
    40 grant recipients, outcomes, evaluation               :p3, 2027-11-01, 2028-04-30
    section Expand
    3,000 units, second Bay Area county, licensing          :p4, 2028-05-01, 2028-12-31
```

## Run

```bash
cp .env.example .env            # MISTRAL_API_KEY, ES_URL, ES_API_KEY
uv sync
uv run python scripts/setup_elastic.py --reset
uv run python scripts/load_opendata.py --reset
uv run python scripts/load_resources.py --reset
uv run uvicorn app.main:app --port 8010
cd frontend && npm install && echo 'HOMEBASE_API_URL=http://127.0.0.1:8010' > .env.local && npx next dev -p 3000
```
Tests: `uv run pytest -n auto`.

## Honesty notes

- The pilot cohort on the impact page is **simulated** and labelled that way. Applications made in the app are real records.
- The demo properties are fictional. The DataSF buildings and the 34 researched resources are real; each resource links to its source and shows its status as of November 3, 2026.
- Program facts come from public listings. Every card says to confirm details with the provider.
- Benefits treatment is planning guidance, not legal advice.
