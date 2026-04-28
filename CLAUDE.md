# CLAUDE.md — v2.0

Guidance for Claude Code in this repository.
Run history → `RUN_HISTORY.md`. Portal config → `KNOWN_PORTALS.md`.

---

## VERSION HISTORY

| Version | Date | Summary |
|---------|------|---------|
| **v2.0** | 2026-04-28 | Architecture V3 complete (A1–D1). First production run under modular provider architecture. |
| v1.x | 2026-04-19 | V2 scraper with monolithic scrapers.py + company_registry.py (deprecated). |

**v2.0 architecture changes:**
- `scrapers.py` deleted → all ATS logic in `providers/` modules
- `company_registry.py` deleted → data in `workday_registry.json`
- `COMPANY_INDUSTRY` dict deleted → data in `company_industries.json`
- `Pipeline_validator.py` — single validation module (3 gates)
- `schema.py` — typed `Portal` TypedDict + canonical field list
- `base.py` — `ScrapeReason` enum + `ProviderResult` typed return
- All module-level singletons lazy-initialized (import is side-effect free)

---

## SCOPE

All work must stay within the `firecrawl_Supabase/` directory. Do not read, write, or modify files outside this folder.

---

## MISSION

Weekly global scrape of 100+ company portals → full JDs → LM Studio skill extraction → Supabase.
**Rule:** if a direct ATS API exists, use it. Firecrawl is the fallback, not the default.

---

## LLM CONFIGURATION — LM Studio only

No cloud AI APIs permitted. All LLM calls route through LM Studio at `http://localhost:1234/v1`.

```
OPENAI_BASE_URL=http://localhost:1234/v1
OPENAI_API_KEY=lm-studio
MODEL_NAME=<model-id-as-shown-in-lm-studio>
MODEL_EMBEDDING_NAME=<embedding-model-id-or-omit>
```

Ollama-compatible mode (port 11434):
```
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=<model-id>
```

Provider selection: `OLLAMA_BASE_URL` set → Ollama; otherwise OpenAI-compatible (`apps/api/src/lib/generic-ai.ts`).
Do not set real keys for `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, or any cloud provider.

---

## COMMANDS

### Full stack (Docker — recommended)
```bash
cp apps/api/.env.example apps/api/.env   # edit with LM Studio settings
docker compose build
docker compose up
```
API: `http://localhost:3002`. Queue admin: `http://localhost:3002/admin/CHANGEME/queues`.

### Development (Node.js)
```bash
cd apps/api
pnpm install
pnpm dev        # API server watch mode
pnpm workers    # Queue workers (separate terminal)
```

### Tests
```bash
pnpm harness jest <pattern>   # always use harness — starts API + workers
pnpm test:local-no-auth       # self-hosted suite, no external auth
pnpm test:snips               # E2E snippet tests only
```

### Python SDK
```bash
cd apps/python-sdk
pip install -r requirements.txt
python example.py
# Point at local: Firecrawl(api_key="local", api_url="http://localhost:3002")
```

### Weekly scraper run (Archon)
```bash
archon workflow run scraper-weekly-run --no-worktree "Weekly dump $(date +%Y-%m-%d)"
```
Layers: check-docker + check-lm + test-portals → scrape → enrich → upload → summarize.

**Do NOT pass `--resume` for a fresh weekly run.** `--resume` is recovery-only — it skips companies that already have output folders.

### Scraper direct commands
```bash
cd scraper
python main.py --dry-run                                          # verify KNOWN_PORTALS.md parsed
python main.py --company "Stripe"                                 # single company test
python main.py --ats greenhouse                                   # single ATS type
python main.py --skip-enrich --scope global --global-cap 2000    # Phase 1: scrape all, no LLM
python main.py --enrich-only                                      # Phase 2: LLM enrichment only
python csv_importer.py                                            # Phase 3: Supabase upsert
```

### Two-phase run (low-RAM — Docker and LM Studio can't run simultaneously)
```bash
# Phase 1 — Docker on, LM Studio off
python main.py --skip-enrich --scope global --global-cap 2000

# Phase 2 — LM Studio on, Docker off
python main.py --enrich-only
```

---

## ARCHITECTURE

### Firecrawl (monorepo)

| Component | Path | Role |
|---|---|---|
| API server | `apps/api/src/` | Express HTTP — all `/v1` and `/v2` routes |
| Queue workers | `apps/api/src/services/queue-worker*` | BullMQ consumers — scrape/crawl/extract jobs |
| Playwright service | `apps/playwright-service-ts/` | Headless browser microservice (port 3000) |
| Redis | `apps/redis/` | Job queue + rate-limit cache |
| RabbitMQ | docker-compose | Alternate message bus for some worker flows |
| PostgreSQL | `apps/nuq-postgres/` | Job metadata, crawl state |

```
Client → POST /v1/scrape
  → Route handler → Zod validation
    → BullMQ (Redis)
      → Queue worker
        → Scrape engine (cheerio or Playwright)
        → AI enrichment (generic-ai.ts → LM Studio)
        → Result stored / returned
```

AI layer: `apps/api/src/lib/generic-ai.ts` — runtime provider selection via env vars.
Config: `apps/api/src/config.ts` — Zod-validated. Key fields: `MODEL_NAME`, `OLLAMA_BASE_URL`, `OPENAI_BASE_URL`.

### Scraper pipeline (`scraper/`)

```
KNOWN_PORTALS.md  ←  portal config (URL, ATS type, company name)
      ↓
scrapers.py  ←  ATS direct API → 5-field raw JSON per company
  (Firecrawl scrape() only as JS-heavy fallback, via Docker)
      ↓
enricher.py  ←  LM Studio → main_skills + side_skills from job_description
      ↓
csv_importer.py  ←  upsert to Supabase on job_id
```

**Scraper files:**

| File | Role |
|---|---|
| `config.py` | Env vars: LM Studio URL/key/model, Firecrawl URL, output paths |
| `utils.py` | `strip_html`, `is_india`, `job_hash`, `company_slug` |
| `portal_reader.py` | Parses `KNOWN_PORTALS.md` → list of portal dicts |
| `workday_registry.json` | Workday tenant overrides (facet params, India UUIDs, search_text mode) — edit to add tenants |
| `rag_skills.py` | IDF-weighted inverted index over 35,108 Lightcast L3 skills — vocab injection for LLM |
| `enricher.py` | `enrich_job()` → RAG vocab → LM Studio → `main_skills` + `side_skills` |
| `writer.py` | `to_canonical()` → 5-field schema; `save_jobs()` → deduped JSON+CSV; `load_to_supabase()` |
| `main.py` | Orchestrator: `--company`, `--ats`, `--dry-run`, `--skip-enrich`, `--resume`, `--enrich-only`, `--scope`, `--global-cap` |
| `csv_importer.py` | Supabase upsert with lifecycle tracking (`first_seen`, `last_seen`, `is_active`, `job_versions`) |

### Scraper setup (once)
```bash
cd scraper
cp .env.example .env
# Set FIRECRAWL_API_KEY (fc-...) or run via Docker
# Set LM_STUDIO_MODEL to exact model name shown in LM Studio
pip install -r requirements.txt
```

**MCP setup:** Edit `~/.claude/mcp.json` — replace `fc-YOUR_API_KEY_HERE`. Restart Claude Code.

---

## CANONICAL SCHEMA (Dump 4+)

8 fields total. No others. Do not add enrichment fields (seniority, work_mode, etc.) to the core flow.

| Field | Source |
|---|---|
| `job_id` | ATS native ID — dedup key |
| `job_title` | ATS / page title — no LLM |
| `job_description` | ATS JD endpoint or Firecrawl scrape |
| `company_name` | KNOWN_PORTALS.md |
| `Industry` | KNOWN_PORTALS.md |
| `Location` | ATS JD endpoint or Firecrawl scrape |
| `apply_url` | ATS direct link or career page URL |
| `main_skills` | LLM Phase 2 — top 5 must-have from JD |
| `side_skills` | LLM Phase 2 — nice-to-have from JD |
| `batch_date` | writer.py — integer YYYYMMDD |

### Supabase table
```sql
CREATE TABLE jobs (
  job_id          TEXT PRIMARY KEY,
  job_title       TEXT NOT NULL,
  job_description TEXT NOT NULL,
  company_name    TEXT NOT NULL,
  Industry        TEXT NOT NULL,
  Location        TEXT NOT NULL,
  apply_url       TEXT,
  main_skills     TEXT[],
  side_skills     TEXT[],
  batch_date      INTEGER
);
```

---

## ATS ROUTING

| ATS | Method |
|---|---|
| Workday | Direct POST CXS API — India UUID + pagination + per-job JD fetch |
| SmartRecruiters | Direct GET `?country=in` — full JD in response |
| Greenhouse | Direct GET — India filter in Python — full JD in response |
| Lever | Direct GET `?location=india` |
| Phenom | REST API per tenant |
| Custom/SAP/Oracle | Direct GET — fallback to Firecrawl extract if HTML |
| JS-heavy (Eightfold, Avature, SPAs) | `scrape_extract()` via Firecrawl (Docker first, cloud last resort) |

---

## FIRECRAWL CREDIT DISCIPLINE

Credits are finite. Rules:

1. Always use `firecrawl-py` SDK — never raw HTTP to the API.
2. One singleton `_app` instance at import in `firecrawl_client.py`. Never instantiate elsewhere.
3. Never use `crawl()` — it is not exposed and must not be added back.
4. Two permitted calls: `fc.scrape(url)` (1 credit) and `fc.extract(urls, schema, prompt)` (JS-heavy portals only).
5. Direct ATS API → Docker → Firecrawl cloud (in that priority order).

---

## LLM ENRICHMENT FLOW

1. `job_description` populated by scraper (raw JD text)
2. `rag_skills.py` retrieves top-40 Lightcast L3 skills from JD as approved vocabulary
3. `enrich_job()` sends vocab + JD to LM Studio
4. LLM returns `main_skills` (top 5 must-have) + `side_skills` (nice-to-have)
5. `_validate_enrichment()` validates against Lightcast L3 — invalid values dropped
6. Enriched jobs upserted to Supabase

**LM Studio preset (`mirror-cv-fast`):**
- System prompt: "You are a precise job data extractor. Return a single valid JSON object. No explanation, no markdown."
- Max tokens: 150 — Temperature: 0.0

---

## KNOWN ISSUES

- Workday India UUID structure varies per tenant — if 0 jobs, run `--company` with debug prints
- Eightfold API returning 404 as of 2026-04-10 — Firecrawl path may or may not extract clean listings
- Goldman Sachs (TAL.NET) requires browser JS — Firecrawl handles it but markdown quality varies
- MSCI: `careers.msci.com` is 404; Workday slug unknown (skipped)
- Capgemini, HCL: Workday slugs unconfirmed (skipped)

**Recommended test order:** Stripe → ServiceNow → Salesforce → Goldman Sachs / Eightfold portals.

---

## BUILD PLAN

### ✅ Arch-Phases A–D — COMPLETE (v2.0, 2026-04-28)

All 7 architecture chunks completed. Architecture V3 is production-ready.

| Phase | What changed |
|-------|-------------|
| A1 | `scrapers.py` deleted — ATS logic in `providers/` |
| A2 | All singletons lazy-init (`_client`, `_L3_INDEX`, `_app`, `batch_date`) |
| B1 | `Portal` TypedDict in `schema.py` — typed throughout |
| B2 | `COMPANY_INDUSTRY` dict → `company_industries.json` |
| C1 | `pipeline_validator.py` — single `run_gate()` with 3 stages |
| C2 | `ScrapeReason` enum + `ProviderResult` — zero bare `return []` in provider interface |
| D1 | `company_registry.py` deleted → `workday_registry.json` (JSON, no Python edit needed) |

---

### Chunk 2 — Fix broken direct scrapers
- Verify Phenom REST endpoints: BCG, PMI, Oliver Wyman (unverified API paths)
- Fix Workday slugs: Capgemini, HCL Technologies, MSCI
- Fix SmartRecruiters: Zomato, S&P Global, CRISIL (unconfirmed IDs)
- Re-add Atlassian to Greenhouse (find new board token)
- Fix Oracle HCM: EXL Digital (verify India filter)
- Target: every direct-API company returns ≥5 jobs with populated `job_description`

### Chunk 3 — New ATS scrapers
- **Workable**: `GET https://apply.workable.com/api/v3/accounts/{slug}/jobs?state=published`
- **Darwinbox**: POST to candidate search endpoint (inspect XHR on `iifl.darwinbox.in`)
- **SAP SuccessFactors**: `GET https://{tenant}/odata/v2/JobRequisitionLocale?$filter=...&$format=json`
  - Targets: Deloitte, GMR Group, CMA CGM, CNHI, Deutsche Bank
- Wire all into `to_canonical()` → `save_jobs()` (5-field schema only)

### Chunk 4 — Archon weekly cadence (operational)
- Weekly cron: `0 2 * * 0` via `.archon/workflows/scraper-weekly-run.yaml`
- Scrape phase: `python main.py --skip-enrich --scope global --global-cap 2000`
- After each run: update `RUN_HISTORY.md` + `KNOWN_PORTALS.md`

---

## DEVELOPMENT WORKFLOW

1. Write E2E tests in `apps/api/src/__tests__/snips/` before writing code.
   - Minimum: 1 happy path + 1 failure path.
   - E2E preferred over unit tests.
   - Unit tests: retrieve 3 jobs per company in `KNOWN_PORTALS.md` end-to-end.
   - Use `scrapeTimeout` from `./lib` for any scrape timeout.
   - Gate on capabilities:
     - Requires fire-engine: `!process.env.TEST_SUITE_SELF_HOSTED`
     - Requires AI: `!process.env.TEST_SUITE_SELF_HOSTED || process.env.OPENAI_API_KEY || process.env.OLLAMA_BASE_URL`
2. Run `pnpm harness jest <your-test-file>` — never `pnpm start` manually.
3. Push branch, open PR, let CI verify.

---

## CLAUDE CODE SKILLS

| Skill | Trigger | Purpose |
|---|---|---|
| `improve-codebase-architecture` | `/improve-codebase-architecture` | ADR-informed refactor suggestions |
| `graphify` | `/graphify` | Any input → knowledge graph |
| `triage-issue` | `/triage-issue` | Root-cause a bug, file GitHub issue |
| `request-refactor-plan` | `/request-refactor-plan` | Interview-driven refactor plan |
| `to-issues` | `/to-issues` | Break plan/spec/PRD into GitHub issues |
| `to-prd` | `/to-prd` | Turn conversation into PRD |
| `review` | `/review` | Review current branch PR |
| `security-review` | `/security-review` | Security review of pending branch changes |
| `tdd` | `/tdd` | Red-green-refactor TDD loop |
| `simplify` | `/simplify` | Review changed code for quality |
| `brooks-design` | `/brooks-design` | Brooks' design philosophy audit |
| `ousterhout-design` | `/ousterhout-design` | Ousterhout deep module principles |
| `init` | `/init` | Initialize CLAUDE.md |
| `qa` | `/qa` | Interactive QA → GitHub issues |
| `grill-me` | `/grill-me` | Resolve plan/design ambiguities |
| `github-triage` | `/github-triage` | Label-based GitHub issue triage |
| `frontend-design` | `/frontend-design` | Production-grade frontend interfaces |
| `schedule` | `/schedule` | Schedule recurring/one-time remote agents |
| `loop` | `/loop` | Run prompt on recurring interval |
| `claude-api` | `/claude-api` | Build/debug Claude API / Anthropic SDK apps |
| `archon` | `/archon` | Run Archon AI workflows |
| `caveman` | `/caveman` | Ultra-compressed communication mode |
| `find-skills` | `/find-skills` | Discover and install agent skills |
| `karpathy-guidelines` | `/karpathy-guidelines` | Reduce common LLM coding mistakes |
| `update-config` | `/update-config` | Configure Claude Code harness via settings.json |
| `fewer-permission-prompts` | `/fewer-permission-prompts` | Add allowlist to reduce permission prompts |
| `keybindings-help` | `/keybindings-help` | Customize keyboard shortcuts |
