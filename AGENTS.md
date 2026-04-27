# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

---

## SCOPE

All work must stay within the `firecrawl_Supabase/` directory. Do not read, write, or modify files outside this folder.

## LLM CONFIGURATION — LM Studio only

**No cloud AI APIs are permitted.** All LLM calls must route through a locally running LM Studio instance.

LM Studio exposes an OpenAI-compatible REST API at `http://localhost:1234/v1`. Configure your `.env` (or `apps/api/.env`) like this:

```
OPENAI_BASE_URL=http://localhost:1234/v1
OPENAI_API_KEY=lm-studio
MODEL_NAME=<model-id-as-shown-in-lm-studio>
MODEL_EMBEDDING_NAME=<embedding-model-id-or-omit>
```

Alternatively, if you run LM Studio in Ollama-compatible mode (port 11434):
```
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=<model-id>
```

The API auto-selects the provider: if `OLLAMA_BASE_URL` is set it uses the Ollama provider; otherwise it uses OpenAI provider (which LM Studio's `/v1` satisfies). Both paths are in `apps/api/src/lib/generic-ai.ts`.

Do not set `OPENAI_API_KEY` to a real OpenAI key, and do not set `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, or any other cloud provider keys. The `HAS_AI` guard in tests (`apps/api/src/__tests__/snips/lib.ts`) checks for `OPENAI_API_KEY || OLLAMA_BASE_URL` — your local setup satisfies this.

---

## COMMANDS

### Start the full stack (Docker — recommended)
```bash
# From firecrawl/ root
cp apps/api/.env.example apps/api/.env   # then edit with LM Studio settings above
docker compose build
docker compose up
```
API is available at `http://localhost:3002`. Queue admin at `http://localhost:3002/admin/CHANGEME/queues`.

### Development (Node.js, no Docker)
```bash
cd apps/api
pnpm install
pnpm dev           # API server in watch mode
pnpm workers       # Queue workers in watch mode (separate terminal)
```

### Running tests
```bash
# Always use the harness — it starts API + workers automatically
pnpm harness jest <pattern>      # e.g. pnpm harness jest scrape

# Self-hosted / local suite (no external auth needed)
pnpm test:local-no-auth

# Snippet (E2E) tests only
pnpm test:snips
```
The full test suite is slow; run only the relevant pattern locally and let CI run the full suite.

### Python SDK
```bash
cd apps/python-sdk
pip install -r requirements.txt
python example.py
```
Point the client at your local API: `Firecrawl(api_key="local", api_url="http://localhost:3002")`.

---

## ARCHITECTURE

Firecrawl is a monorepo. The production system has these moving parts:

| Component | Path | Role |
|---|---|---|
| **API server** | `apps/api/src/` | Express HTTP server — handles all `/v1` and `/v2` routes |
| **Queue workers** | `apps/api/src/services/queue-worker*` | BullMQ consumers that execute scrape/crawl/extract jobs |
| **Playwright service** | `apps/playwright-service-ts/` | Headless browser microservice (separate Docker container, port 3000) |
| **Redis** | `apps/redis/` | Job queue backing store + rate-limit cache |
| **RabbitMQ** | docker-compose | Alternate message bus for some worker flows |
| **PostgreSQL** | `apps/nuq-postgres/` | Job metadata, crawl state |

### Request flow
```
Client → POST /v1/scrape (or /v2/*)
  → Route handler (apps/api/src/routes/)
    → Validation (zod schemas)
    → Job enqueued to BullMQ (Redis)
      → Queue worker picks up job
        → Scrape engine (cheerio for simple, Playwright microservice for JS-heavy)
        → Optional AI enrichment (generic-ai.ts → LM Studio)
        → Result stored / returned to client
```

### AI layer
- `apps/api/src/lib/generic-ai.ts` — single entry point for all LLM calls. Provider is selected at runtime based on env vars. Supports OpenAI (incl. custom baseURL), Ollama, Anthropic, Groq, Vertex, etc.
- `apps/api/src/config.ts` — validated env schema (Zod). Key AI fields: `MODEL_NAME`, `MODEL_EMBEDDING_NAME`, `OLLAMA_BASE_URL`, `OPENAI_BASE_URL`.

### SDKs
`apps/js-sdk/`, `apps/python-sdk/`, `apps/rust-sdk/`, `apps/java-sdk/`, `apps/elixir-sdk/` — thin clients over the HTTP API. SDK changes rarely need matching API changes.

---

## SCRAPER (`firecrawl/scraper/`)

**From Dump 4 onwards the canonical schema is 5 raw fields only.** The previous 25-field schema is retired. A weekly job scraper reads `firecrawl/KNOWN_PORTALS.md`, scrapes 5 raw fields per job, enriches with LLM (skills only), and loads to Supabase.

### Files

| File | Role |
|---|---|
| `config.py` | Env vars: LM Studio base URL/key/model, Firecrawl URL, output paths |
| `utils.py` | `strip_html`, `is_india`, `job_hash`, `company_slug` |
| `portal_reader.py` | Parses `KNOWN_PORTALS.md` by section → list of portal dicts |
| `scrapers.py` | Workday (POST + India UUID + pagination), SmartRecruiters, Greenhouse, generic GET |
| `firecrawl_client.py` | `scrape(url)` + `crawl(url)` against localhost:3002 with poll loop |
| `enricher.py` | LM Studio enrichment: `enrich_job()` fills null fields; `extract_jobs_from_markdown()` for FC pages |
| `writer.py` | `to_canonical()` → **5-field raw schema** (Dump 4+); `save_jobs()` → deduplicated JSON + CSV; `load_to_supabase()` → upsert pipeline |
| `main.py` | Orchestrator: `--company`, `--ats`, `--dry-run`, `--skip-enrich`, `--resume`, `--enrich-only` |
| `test_llm.py` / `test_pipeline.py` | Test scripts |

### Setup (once)

```bash
cd firecrawl/scraper
cp .env.example .env
# Required: set FIRECRAWL_API_KEY to your paid Firecrawl API key (fc-...)
# If API key is not given, run through Docker — Firecrawl should be configured to run through Docker
# Required: set LM_STUDIO_MODEL to exact model name shown in LM Studio
# LM Studio must be running on localhost:1234 (for --enrich-only phase)
# pip install -r requirements.txt
```

**MCP setup (Codex):**
Edit `~/.Codex/mcp.json` — replace `fc-YOUR_API_KEY_HERE` with your real key.
After editing, restart Codex. The `firecrawl_scrape`, `firecrawl_extract`,
`firecrawl_map`, etc. tools will then be available in your Codex session.

### Run commands

```bash
python main.py --dry-run                 # verify KNOWN_PORTALS.md parsed correctly
python main.py --company "Syngenta"      # test single company
python main.py --ats smartrecruiters     # test one ATS type
python main.py                           # full weekly run
python main.py --resume                  # skip companies already in All_CSV_Outputs (resume interrupted run)
python main.py --resume --skip-enrich    # scrape only, no LLM — use when Docker on, LM Studio off
python main.py --enrich-only             # enrich saved jobs in-place — use when LM Studio on, Docker off
```

### Two-phase run (low-RAM machines)

Split between Firecrawl API (always on, cloud) vs Firecrawl through Docker. When the scraping/crawling through firecrawl is done, only then we start LM Studio (local, RAM-heavy).

**Phase 1 — Scraping** (Firecrawl API key set, LM Studio off):
```bash
python main.py --resume --skip-enrich
```
Scrapes all portals not yet in `All_CSV_Outputs`. Workday: uses CXS API + JD fetch.
JS-heavy: uses `scrape_extract()` via Firecrawl cloud LLM/ else use through docker.
`--skip-enrich` suppresses the LM Studio enrichment pass only.

**Phase 2 — Enrichment** (LM Studio on, no firecrawl needed):
```bash
python main.py --enrich-only
```
Walks every `jobs.json` in `All_CSV_Outputs`, enriches jobs that have `raw_jd_text` but missing `skills_required', rewrites `.json`.

### ATS routing

- **Workday** → direct POST API (India UUID + pagination + CXS JD fetch per job)
- **SmartRecruiters** → direct GET `?country=in` (includes full JD in API response)
- **Greenhouse** → direct GET, India filter in Python (includes full JD in API response)
- **Custom/SAP/Oracle** → direct GET, fallback to Firecrawl extract if HTML response
- **JS-heavy** (Eightfold, Avature, custom SPAs) → `scrape_extract()` via Firecrawl cloud LLM
- All Firecrawl paths now can use the **paid cloud API** (`api.firecrawl.dev`) — can switch to local Docker for testing

### LLM enrichment flow (Dump 4+)

1. Scraper populates `job_description` (raw JD text from ATS or Firecrawl)
2. `enrich_job()` sends first all chars to LM Studio
3. LLM extracts **two fields only**:
   - `main_skills` — top 5 must-have / hard technical skills (from the skill_taxonomy.md)
   - `side_skills` — nice-to-have / soft skills (from skill_taxonomy.md)
4. LLM output is validated by `_validate_enrichment()` before writing — invalid values dropped, not kept
5. Enriched jobs are loaded to Supabase via `load_to_supabase()` / `csv_importer.py`

**Do NOT add other enrichment fields** — seniority, work_mode, employment_type, degree_required, etc. are all retired from the schema. If needed in future, add as a separate enrichment pass, not in the core flow.

### Known issues

- Workday India UUID response structure varies per tenant — if 0 jobs returned, run with `--company` and add debug prints
- Eightfold API 404 as of 2026-04-10 — Firecrawl path may or may not extract clean listings
- Goldman Sachs (TAL.NET) requires browser JS — Firecrawl handles it but markdown quality varies
- MSCI: `careers.msci.com` is 404; Workday slug unknown (skipped in parser)
- Capgemini, HCL: Workday slugs unconfirmed (skipped in parser)

### Recommended test order

Start with low-risk targets before JS-heavy ones: **Stripe → ServiceNow → Salesforce**, then Goldman Sachs / Eightfold portals.

---

## PIPELINE v2 — CANONICAL ARCHITECTURE (Dump 4+)

This is the standardised E2E pipeline used from Dump 4 onwards. Do not deviate from this structure without updating this section.

### Canonical schema — 8 fields total

| Field | Source | Notes |
|---|---|---|
| `job_id` | ATS native ID | Deduplicate on this field |
| `job_title` | ATS / page title | Scraped directly, no LLM |
| `job_description` | ATS JD endpoint or Firecrawl scrape | Full text, HTML stripped |
| `company_name` | KNOWN_PORTALS.md | Static per portal entry |
| `Industry_name` | KNOWN_PORTALS.md | Static per portal entry |
| `Location`  | ATS JD endpoint or Firecrawl scrape | Full text, HTML stripped |
| `apply_url` | ATS direct link or career page URL | Candidate-facing application link |
| `main_skills` | LLM enrichment (Phase 2) | Top 5 must-have skills from JD |
| `side_skills` | LLM enrichment (Phase 2) | Nice-to-have skills from JD |
| `batch_date` | Set at import time in writer.py | Integer YYYYMMDD — tracks which run produced this row |

5 fields are scraped raw. 2 are added by LLM enrichment. 1 (`batch_date`) is stamped automatically. No other fields.

Firecrawl API is **never used** — banned - unless extremely important. Only `scrape_extract()` (1 call per JS-heavy portal) is permitted when a direct ATS API is unavailable or docker is not able to work.

### E2E pipeline stages

```
Phase 1 — Scrape
  → ATS direct API (Workday CXS, SmartRecruiters, Greenhouse, Phenom, etc.)
  → Firecrawl scrape() ONLY as fallback for JS-heavy portals (not crawl) and through docker.
  → Output: 5-field raw JSON per company

Phase 2 — LLM Enrichment (LM Studio)
  → Input: job_description (raw JD text)
  → Output: main_skills (top 5 must-have), side_skills (nice-to-have)
  → _validate_enrichment() enforces controlled vocabulary before writing

Phase 3 — Supabase Load
  → csv_importer.py / load_to_supabase()
  → Upsert on job_id (deduplication)
  → Quality gate: drop jobs with missing job_id or job_title
```

### Firecrawl credit discipline

**Firecrawl is a paid API — credits are finite.** Rules:

1. **Always use the official `firecrawl-py` SDK** — never raw HTTP requests to the API.
   ```python
   from firecrawl import Firecrawl
   app = Firecrawl(api_key="fc-YOUR_API_KEY")
   result = app.scrape(career_url)
   ```
2. **One singleton instance** — `_app` is created at import in `firecrawl_client.py`. Never instantiate `Firecrawl` elsewhere.
3. **Never use `crawl()`** — it is not exposed in `firecrawl_client.py` and must not be added back. N credits per company = too expensive.
4. **Two permitted calls only:** `fc.scrape(url)` (1 credit, validate URL + fetch JS content) and `fc.extract(urls, schema, prompt)` (js-required portals only).
5. `scrape()` use cases: (a) verify a careers URL is reachable, (b) fetch JS-heavy page when no direct ATS API exists.
6. If a direct ATS JSON API exists → use it. If Firecrawl works through docker, make it work. Firecrawl API is always the last resort.

### Supabase table schema (v2)

```sql
CREATE TABLE jobs (
  job_id          TEXT PRIMARY KEY,
  job_title       TEXT NOT NULL,
  job_description TEXT NOT NULL,
  company_name    TEXT NOT NULL,
  Industry	  TEXT NOT NULL,
  Location	  TEXT NOT NULL,
  apply_url       TEXT,
  main_skills     TEXT[],   -- array of up to 5 must-have skill strings
  side_skills     TEXT[],   -- array of nice-to-have skill strings
  batch_date      INTEGER   -- YYYYMMDD integer — tracks which run produced this row
);
```

---

## RUN HISTORY & CURRENT STATE

### Session 2026-04-19 — Portal expansion + JD fix

**Code changes:**
- `scraper/config.py` — `WORKDAY_JD_FETCH_LIMIT` default raised 200→500. Was silently capping JD fetch for all large Workday companies (Accenture 500 jobs had only 200 JDs, State Street 351→200, DBS 285→200).
- `scraper/company_registry.py` — Added 4 new standard Workday tenants (3M, NXP, Autodesk, DXC) with `locationCountry` facet. Added Roche (`locations` facet). Added Barclays (12 India office UUIDs) and Maersk (26 India office UUIDs) using `india_uuids` list support.
- `scraper/scrapers.py` — `india_uuids` list support: `reg.get('india_uuids') or [reg['india_uuid']]` allows multi-UUID facet queries for tenants with per-office location facets (Barclays, Maersk).
- `scraper/probe_cxs.py` — New tool for probing Workday CXS India UUIDs for a list of tenants.

**New companies scraped (2026-04-19):**
| Company | ATS | Jobs | JD% |
|---------|-----|------|-----|
| 3M | Workday (Location_Country) | 81 | 100% |
| NXP Semiconductors | Workday (Location_Country) | 161 | 100% |
| Autodesk | Workday (locationCountry) | 111 | 100% |
| DXC Technology | Workday (locationCountry) | 211 | 100% |
| Barclays | Workday (12 location UUIDs) | 500 | 100% |
| Maersk | Workday (26 location UUIDs) | 97 | 100% |
| Bosch | SmartRecruiters | 100 | 100% |
| Airbnb | Greenhouse | 15 | 100% |
| Razorpay | Greenhouse | 46 | 100% |
| PhonePe | Greenhouse | 43 | 100% |
| Thoughtworks | Greenhouse | 2 | 100% |
| Meesho | Lever | 52 | 100% |
| CRED | Lever | 7 | 100% |
| Paytm | Lever | 203 | 96% |

**Re-scraped to fix JD cap:**
- Accenture: 500 jobs → 100% JD (was 40%)
- State Street: 351 jobs → 100% JD (was 56%)
- DBS Bank: 285 jobs → 100% JD (was 70%)

**Demoted:**
- Publicis Sapient → 🔴 SmartRecruiters returns 0 for all IDs tried; careers site is SPA with unknown ATS
- ING Bank → 🔴 no India locations in ICSGBLCOR portal
- Roche → 🔴 only 1 India job (not worth scraping)

**Unresolved for next session:**
- Societe Generale: SmartRecruiters `SocieteGenerale4` — `country=in` returns 0; try location text filter
- Storable: Greenhouse board confirmed but India jobs TBD
- 74 companies returning 1 Firecrawl blob — need direct API scrapers (see FC-fallback companies list)

### Session 2026-04-17 — Phase 1 full scrape + RAG enrichment pipeline

**Code changes this session:**
- `scraper/rag_skills.py` (NEW) — IDF-weighted keyword inverted index over 35,108 Lightcast L3 skills. `retrieve(text, k=40)` returns the top-k canonical skill names via token overlap scoring (IDF-weighted + length-normalized). No model calls — builds in <0.5s at import. Used in enricher to inject a constrained vocabulary into every LLM prompt.
- `scraper/enricher.py` — RAG-augmented: `enrich_job()` now calls `_retrieve_skills(title + jd[:800], k=40)` and injects the result into `_ENRICH_PROMPT` as "Approved skill vocabulary — choose ONLY from this list". System prompt removed from code (moved to LM Studio GUI for KV-cache reuse across requests). `max_tokens` lowered 300→150. JD truncation 2000→1500 chars.
- `scraper/main.py` — `enrich_only_run()` parallelised with `ThreadPoolExecutor(max_workers=ENRICH_WORKERS)`. Added `from concurrent.futures import ThreadPoolExecutor, as_completed`.
- `scraper/config.py` — added `ENRICH_WORKERS = int(os.getenv("ENRICH_WORKERS", "4"))`.
- `scraper/.env` — added `ENRICH_WORKERS=4`; dual model presets (`MODEL_SPEED=fast` → `google/gemma-3-4b`, `MODEL_SPEED=quality` → `deepseek-r1-0528-qwen3-8b-mlx`).

**LM Studio GUI changes (save as preset `mirror-cv-fast`):**
- System Prompt: "You are a precise job data extractor. Read the job title and description and return a single valid JSON object. No explanation, no markdown, no extra text."
- Limit Response Length: enabled → 150 tokens
- Temperature: 0.0

**Phase 1 run results (2026-04-17):**
- `python main.py --skip-enrich` completed. 94 output files, 2,376 total jobs, 1,730 with `job_description`.
- Output path: `/Users/incognito/Mirror CV/firecrawl/All_CSV_Outputs_thru_firecrawl/` (set via `OUTPUT_BASE` in .env)

**Phase 2 status (in progress as of session close):**
- `python main.py --enrich-only` running as PID 58046, log at `/tmp/enrich_rag.log`
- 1,530 jobs need enrichment (have JD, no main_skills). ~4h ETA at ~10s/job.
- All skills now sourced directly from Lightcast L3 taxonomy via RAG retrieval.

**Next after Phase 2 completes:**
- Run `python csv_importer.py` (Phase 3 — Supabase upsert)
- Verify row count in Supabase matches enriched job count

### Session 2026-04-16 — Taxonomy + Workflow setup

**Code changes this session:**
- `scraper/lightcast_skills_taxonomy.json` — created; full Lightcast Open Skills L1→L2→L3 hierarchy (31 L1, 442 L2, 35,108 L3 skills)
- `scraper/lightcast_skills_flat.csv` — flat table (l1_category, l2_subcategory, l3_skill_name, l3_skill_id, 35,108 rows)
- `scraper/enricher.py` — updated: LLM skills now validated against Lightcast L3 taxonomy only. Three match strategies: exact, stripped-parenthetical ("Docker" → "Docker (Software)"), fuzzy (cutoff=0.88, min 8 chars)
- `.archon/workflows/scraper-weekly-run.yaml` — created; 7-node DAG workflow: check-docker + check-lm + test-portals (parallel) → scrape → enrich → upload → summarize

**Workflow run notes:**
- Ran `archon workflow run scraper-weekly-run --no-worktree` (Phase 1 only — LM Studio was off)
- `check-lm` failed as expected; `scrape` completed in 18 min but scraped **0 new data** because `--resume` was mistakenly left in the workflow command — all 44 companies already had output from 2026-04-12 and were skipped
- **Fixed**: removed `--resume` from the `scrape` node command. Next weekly run will do a full fresh scrape of all companies.

**Current state of All_CSV_Outputs_thru_firecrawl/ (44 companies, last scraped 2026-04-12):**
Accenture (500), Sanofi (596), Novartis (592), Wells Fargo (224), Salesforce (168), Continental (99), Airbus (144), Stripe (66), Volvo Group (43), Shell (32), ServiceNow (35), Fidelity (29), Amazon (81), Michelin (21), LDC (20), WESCO (20), AstraZeneca (25), Schneider Electric (126), Philips (136), Eli Lilly (10), Dell (18), Stellantis (18)
Low/broken: Engie (2), Baker Hughes (2), Morgan Stanley (2), AmEx (3), Google (3), Infosys (3), TCS (3), Wipro (3), Cognizant (0), Alstom (1), Chanel (1), Apple (2), CNHI (3), CMA CGM (0), TotalEnergies (0), Synopsys (0), Mastercard (0), Microsoft (0), Volkswagen (5/excluded)

### Session 2026-04-10 — First full run (interrupted)
- Ran `python main.py` (full run, all portals).
- Run was force-closed mid-way due to memory pressure from running Docker + LM Studio simultaneously.
- **15 companies fully scraped** before interruption:
  Accenture, Airbus, Amazon, American Express, Chanel, Continental, Fidelity Investments,
  LDC (Louis Dreyfus), Morgan Stanley, STMicroelectronics, Sanofi, ServiceNow, Shell, Stripe, Wells Fargo
- Output location: `All_CSV_Outputs/{Company}/Outputs/YYYY_MM_DD/jobs.json` + `jobs.csv`

### Session 2026-04-11 — Phase 1 + Phase 2 COMPLETE ✅

**Code fixes made this session:**
- Workday headers → browser-like UA + Accept-Language + dynamic Referer
- Workday facet param → `_find_india_id()` now returns `(facet_param, uuid)` tuple (tenant-specific names)
- Workday Cloudflare 303 → automatic Firecrawl fallback using `careers_url` (not API URL)
- `--skip-enrich` now suppresses LLM in Firecrawl path; saves `firecrawl_raw.md` staging file
- `--enrich-only` Phase 1 processes all `firecrawl_raw.md` staging files → extract + enrich
- `portal_reader.py` passes `careers_url` field for Workday portals
- No-India-Jobs companies consolidated into a dedicated excluded block in KNOWN_PORTALS.md

**25 companies with enriched jobs.json as of 2026-04-11:**
Accenture (8240), Amazon (92), Wells Fargo (235), Salesforce (169), Continental (99),
Sanofi (93), Stripe (66), ServiceNow (35), Airbus (40), Fidelity (30), Shell (27),
LDC (20), STMicro (3), Morgan Stanley (3), AmEx (3), Chanel (1),
Eli Lilly (3), Google (3), Infosys (3), L'Oréal (3), TCS (3), Wipro (3),
Cognizant (2), Stellantis (3), AstraZeneca (3)

**Still broken / needs next run:**
- Engie, Mastercard, Novartis, Synopsys — Workday fallback URL fix applied; re-run to verify
- Baker Hughes, Philips, TotalEnergies, Volvo Group — need India-filtered URL in KNOWN_PORTALS.md
- Microsoft — Firecrawl crawled Azure error page; needs correct careers URL
- Atlassian (board token changed), Michelin/CNHI/Schneider Electric (404s)
- Alstom, CMA CGM, Air France, SAP — Firecrawl crawl timeout; try `scrape` instead of `crawl`
- Apple, Dell — needs further investigation
- IBM, Goldman Sachs — login-required; users directed to careers page

**Excluded from scraper (confirmed no India jobs) :**
Volkswagen, RTX (Raytheon), Syngenta, Solvay — see `## NO INDIA JOBS` section in KNOWN_PORTALS.md 

---

## DUMP 2 ANALYSIS — Root Cause Diagnosis (2026-04-11)

**Context:** Dump 2 (uploaded 2026-04-11) contained 2,774 jobs from 25 companies but with severe data quality issues. After code inspection, these are confirmed root causes.

### Problem 1 — Workday: zero raw_jd_text (confirmed)
`scrapers.py:76` reads `p.get('jobDescription', '')` from the Workday listing API response. **The listing endpoint `/wday/cxs/{tenant}/{site}/jobs` never returns full JD text** — it returns only metadata (title, location, postedOn, bulletFields). The `jobDescription` key exists but is empty in listing responses. Full JD lives at the individual job detail endpoint: `GET https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs/{externalPath}`. Fix: add a second-pass fetch for each job's `externalPath` to get the actual JD.

### Problem 2 — Accenture: 8,240 jobs scraped, 1,841 unique (6,399 duplicates)
Two sub-issues:
1. **India filter not working**: Accenture's Workday returns ~1,841 unique India jobs (vs expected ~800). The `_find_india_id()` may be matching a broader location facet than just India.
2. **Pagination overlap**: 8,240 records for 1,841 unique items = each job appears ~4.5× on average. Workday offset-based pagination on Accenture's tenant is returning overlapping result sets across pages (known Workday tenant behavior when results change between page requests). Fix: deduplication in `writer.py:save_jobs()` exists but only at save time — need to deduplicate during pagination by tracking seen `jobReqId` values.

### Problem 3 — Firecrawl companies: exactly 3 jobs each
`main.py:109` slices Firecrawl output to `pages[:5]` (first 5 crawled pages), then `enricher.py:extract_jobs_from_markdown()` asks LM Studio to extract listings from that combined markdown. LM Studio on a listing page with typical card layout extracts the first visible 3-5 jobs from the markdown. Not a pagination issue — the LLM just stops after a few. Fix: need either direct API calls for these companies OR increase the crawl depth/page limit and use a more structured extraction prompt.

### Problem 4 — skills_required, seniority_level all empty
These are populated by `enricher.py:enrich_job()` — but enrichment requires `raw_jd_text` to exist first (`_needs_enrichment()` checks `has_jd`). Since `raw_jd_text` is empty for all Workday jobs, enrichment is skipped for all of them. Fix is the same as Problem 1 — once JD text is populated, enrichment will work.

### Recommended Fix Strategy (Option A — hybrid APIs + targeted fixes)

**Priority 1 — Workday JD fetch (fixes ~90% of data):**
Add individual job detail fetching to `scrape_workday()`. After collecting all job listings, fetch each job's full JD via:
```
GET https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{career_site}/jobs/{externalPath}
```
Response has `jobPostingInfo.jobDescription` with full HTML JD. This one change fixes Workday companies: Accenture, Airbus, Chanel, Eli Lilly, Fidelity, Sanofi, Salesforce, Shell, Wells Fargo.

**Priority 2 — Workday deduplication during pagination:**
Track seen `jobReqId` in a set during the `while True` pagination loop. Break early if new page returns >50% already-seen IDs (signals overlapping pagination).

**Priority 3 — Firecrawl extraction improvement:**
For JS-heavy companies (Google, TCS, Wipro, Infosys, etc.) that go through `_scrape_firecrawl()`, increase `fc.crawl(url, limit=40)` and don't slice `pages[:5]` — use all pages. Or better: identify the actual JSON API behind each (Google has `careers/applications/jobs/results` JSON endpoint, Infosys has an XHR endpoint, etc.) and add direct API scrapers.

**Priority 4 — Paid Firecrawl tier:**
User is upgrading to paid Firecrawl. With paid tier, rate limiting is removed. Retry the Firecrawl-dependent companies (SAP timeout companies, Dell, etc.) before rebuilding them with Playwright. Use this only as last resort - before that try to work whether docker is working or not.

### What NOT to do
- Do not switch to Playwright wholesale — Workday, Greenhouse, SmartRecruiters are already solved with direct APIs
- Do not add fields beyond the 5-field raw schema in scrapers — enrich only main_skills and side_skills

---

## MISSION STATEMENT

**Goal:** Keep Firecrawl running to capture all job openings + full JDs from 100+ company portals every 3 days. The JD corpus is used to extract skills required in the age of AI (via LM Studio enrichment → Supabase). Every scraper build decision must serve this mission — if a direct API exists, use it; Firecrawl is the fallback, not the default.

---

## BUILD PLAN — CHUNKS (session-by-session)

### Chunk 1 — Audit existing coverage ✅ COMPLETED 2026-04-16
- Ran `--dry-run`: **106 portals parsed** (43 direct API ⚡, 63 Firecrawl/js-required 🌐)
- Direct API breakdown: Workday (18), SmartRecruiters (4), Greenhouse (2), Custom (5), SAP (6), Oracle (1), Phenom (4), Other-direct (3)
- Firecrawl path: 63 companies (all [other] + eightfold + avature + some custom)
- Missing from parse: Atlassian (broken Greenhouse token), Capgemini/HCL/MSCI (unconfirmed Workday slugs), Technip Energies (Oracle — dropped)

**Spot-check results (5-job test per ATS type):**

| ATS | Company | Jobs | JD populated | Location | Verdict |
|-----|---------|------|-------------|----------|---------|
| Greenhouse | Stripe | 69 | ✅ 3-5k chars | ❌ Empty | Fix location mapping |
| SmartRecruiters | ServiceNow | 29 | ✅ 2-3k chars | ✅ | Working |
| Custom JSON | Amazon | 93 | ✅ 1-3k chars | ❌ None | Fix location mapping |
| Workday | Salesforce | 169 | ❌ 0 chars (0/169 JDs fetched) | ❌ None | JD fetch broken — critical |
| Phenom REST | Schneider Electric | 10 | ✅ 6-12k chars | ❌ None | Fix location mapping |

**Two systemic bugs confirmed and FIXED in Chunk 2:**
1. **Workday JD fetch: 0/N always failing** — Root cause: `cxs_base` was missing `career_site` segment. Was `/wday/cxs/{tenant}{ext}`, should be `/wday/cxs/{tenant}/{career_site}{ext}`. Fixed in `scrapers.py:_fetch_workday_jds()`. Now 169/169 JDs fetched via direct CXS API.
2. **Location = None/empty** — Fixed in `writer.py:to_canonical()`: `raw.get('location_city') or 'India'` — defaults to 'India' when scraper returns empty (all jobs passing the India filter ARE India jobs).
3. **Firecrawl Workday fallback also added** — if CXS API fails (some tenants block it), `_fetch_workday_jds()` falls back to `fc.batch_scrape()` on the human-facing job URL. Threshold set to 500 chars to reject error pages.

**Verified clean after fixes:**
| ATS | Company | Jobs | JD | Location |
|-----|---------|------|-----|----------|
| Workday | Salesforce | 169 | ✅ 8-11k chars | ✅ Real city |
| Greenhouse | Stripe | 69 | ✅ 4-5k chars | ✅ Bengaluru |
| Custom JSON | Amazon | 93 | ✅ 1-3k chars | ✅ City+State+IND |
| Phenom REST | Schneider Electric | 10 | ✅ 6-12k chars | ✅ |

### Chunk 2 — Fix broken direct scrapers (NEXT — run after full scrape reveals which companies fail)
- Verify Phenom REST endpoints: BCG, PMI, Oliver Wyman (🟡 unverified API paths)
- Fix broken Workday slugs: Capgemini, HCL Technologies, MSCI
- Fix SmartRecruiters entries: Zomato, S&P Global, CRISIL (unconfirmed IDs)
- Re-add Atlassian to Greenhouse (find new board token)
- Fix Oracle HCM: Technip Energies (dropped from parse), EXL Digital (verify India filter)
- Target: every ⚡ direct-API company returns ≥5 jobs with populated job_description

### Chunk 3 — New ATS scrapers (where Firecrawl alone is unreliable)
- **Workable scraper**: Elevation Capital (`apply.workable.com/elevation-capital-3/`)
  - API: `GET https://apply.workable.com/api/v3/accounts/{slug}/jobs` with `state=published`
- **Darwinbox scraper**: IIFL Finance (`iifl.darwinbox.in/ms/candidate/careers`)
  - API: POST to Darwinbox candidate search endpoint (inspect XHR)
- **SAP SuccessFactors direct REST**: Monitor Deloitte, GMR Group, CMA CGM, CNHI, Deutsche Bank
  - API: `GET https://{tenant}/odata/v2/JobRequisitionLocale?$filter=...&$format=json`
- Wire all new scrapers into `to_canonical()` → `save_jobs()` (5-field schema only)

### Chunk 4 — Archon 3-day cadence + docs (REPEATS EVERY 3 DAYS automatically)
- Update `.archon/workflows/scraper-weekly-run.yaml` → rename to `scraper-3day-run.yaml`
- Schedule: every 3 days via Archon cron (not weekly)
- After each run: update RUN HISTORY in KNOWN_PORTALS.md + AGENTS.md
- Archon workflow nodes: check-docker + check-lm + test-portals → scrape (--skip-enrich) → enrich (--enrich-only) → upload (csv_importer.py) → summarize
- **This chunk is the repeating operational heartbeat — set it once, it runs itself**

---

## NEXT SESSION — Weekly Scraper Run (Dump 5)

**Goal:** Execute a full fresh weekly scrape of all 100+ companies, enrich with LM Studio, upload to Supabase.

**How to run (requires Docker + LM Studio both on):**
```bash
archon workflow run scraper-weekly-run --no-worktree "Weekly dump $(date +%Y-%m-%d)"
```
- Layer 0: check-docker + check-lm + test-portals (parallel pre-flight)
- Layer 1: scrape — `python main.py --skip-enrich` (full fresh scrape, 40-90 min)
- Layer 2: enrich — `python main.py --enrich-only` (LM Studio, 20-40 min)
- Layer 3: upload — `python csv_importer.py` (Supabase upsert, < 5 min)
- Layer 4: summarize — AI run report

**If LM Studio is off (Phase 1 only):**
```bash
# Scrape runs, enrich/upload skipped automatically
archon workflow run scraper-weekly-run --no-worktree "Weekly dump $(date +%Y-%m-%d)"
# Then later, when LM Studio is on:
archon workflow run scraper-weekly-run --no-worktree --resume "Weekly dump $(date +%Y-%m-%d)"
```

**IMPORTANT — do NOT add --resume for a fresh weekly run.** `--resume` is only for recovering from a mid-run crash within the same session. Using it on a new week skips all companies that already have output folders (18 min run that does nothing).

**Architecture goal (v2):**
```
KNOWN_PORTALS.md  ←  portal config (URL, ATS type, company name)
      ↓
scrapers.py  ←  ATS direct API → 5-field raw JSON per company
  (Firecrawl scrape() only as JS-heavy fallback —  Use through docker for everything - can crawl - can scrape - use API only after confirming.)
      ↓
enricher.py  ←  LM Studio → main_skills + side_skills from job_description
      ↓
csv_importer.py / load_to_supabase()  ←  upsert to Supabase on job_id
```

**What to do for Market Data_V1_of_Scrapers/ folder:**
1. all company-specific scrapers are the first working version of the scrapers. The scrapers in Firecrawl folder are buit with the pricniples of individual scrapers in the Market Data_V1_of_scrapers
2. For any upcoming company scrapers - build it at /Users/incognito/Mirror CV/firecrawl_Supabase/scraper(all new scrapers are placed here) Wire output into `to_canonical()` → `save_jobs()` using the **5-field schema only**
3. KNOWN_PORTALS.md is the URL config source — personal scrapers read endpoint from it and keep updating on it so that endpoints are updated and confirmed after every week.

**Note on LM Studio:** User runs LM Studio locally. Multiple processes can share `localhost:1234` safely — it is stateless per request. If model outputs look wrong, verify `LM_STUDIO_MODEL` in `.env` matches the loaded model.

---

## DEVELOPMENT WORKFLOW

1. Write E2E tests ("snips") in `apps/api/src/__tests__/snips/` before writing code.
   - Minimum: 1 happy path + 1 failure path.
   - E2E is always preferred over unit tests.
   - Unit tests are conducted end-to-end to retrieve 3 jobs from each company in known_portal.md to ensure that all company career pages are able to be scraper through Firecrawl Docker.
   - Always use `scrapeTimeout` from `./lib` for any scrape timeout.
   - Gate tests on capabilities:
     - Requires fire-engine: `!process.env.TEST_SUITE_SELF_HOSTED`
     - Requires AI: `!process.env.TEST_SUITE_SELF_HOSTED || process.env.OPENAI_API_KEY || process.env.OLLAMA_BASE_URL`
2. Run `pnpm harness jest <your-test-file>` — never `pnpm start` manually.
3. Push branch, open PR, let CI verify.