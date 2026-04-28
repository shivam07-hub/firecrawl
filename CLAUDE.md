# CLAUDE.md

Guidance for Claude Code in this repository.
Run history → `RUN_HISTORY.md`. Portal config → `KNOWN_PORTALS.md`.

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
| `scrapers.py` | **DEPRECATED shim** — lazy-import forwarding only; target for deletion in Arch-Phase A1 |
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

## BUILD PLAN — OPEN CHUNKS

### Arch-Phase A — Foundation (do first, unblocks B–D)

**Goal:** eliminate the two things that block testing and graceful degradation.

#### A1 — Delete `scrapers.py` shim + fix circular import
- **Why:** `scrapers.py` (83 lines) is pure boilerplate. It exists only because `providers/firecrawl_js.py` imports `scrapers` at module level, creating a cycle: `providers/__init__ → registry → firecrawl_js → scrapers`. Lazy imports paper over it but every new provider must add a forwarding stub here.
- **Fix:** Remove the `import scrapers` line in `providers/firecrawl_js.py`. Inline whatever `scrapers` provided directly into `firecrawl_js.py`. Delete `scrapers.py`. Update `company_scrapers/` V1 scripts and `test_pipeline.py` that still import via the shim.
- **Done when:** `scrapers.py` is gone; all imports come directly from `providers/`.

#### A2 — Defer module-level singletons to lazy init
- **Why:** Four globals init at import time: `_client` (enricher.py:25), `_L3_INDEX` (enricher.py:68), `_app` (firecrawl_client.py:35), `_BATCH_DATE` (writer.py:24). Consequences: (a) `--skip-enrich` crashes if LM Studio is offline because `enricher.py` is imported regardless; (b) missing taxonomy file silently disables skill validation with no error; (c) pipeline crossing midnight stamps wrong `batch_date`; (d) tests require live services at import time.
- **Fix:** Set all four to `None` at module level. Add `_get_client()`, `_get_l3_index()`, `_get_app()`, `_get_batch_date()` lazy-init functions called on first use. `_BATCH_DATE` should be computed at the start of each `save_jobs()` call, not at import.
- **Done when:** `python -c "import enricher"` succeeds with LM Studio offline and taxonomy file absent.

---

### Arch-Phase B — Data Contract (depends on A)

**Goal:** replace the untyped `portal` dict nerve bundle with a schema that fails loudly on misconfiguration.

#### B1 — Typed `Portal` dataclass
- **Why:** The `portal` dict carries ATS-specific fields (`tenant`, `sr_id`, `board_token`, `lever_slug`, `india_facet_param`) plus cross-cutting flags (`india_only`, `js_required`). No schema means: `india_only` silently ignored by `greenhouse.py`, has different semantics in `lever.py`, applied only on the searchText path in `workday.py`. Adding a new ATS means editing `portal_reader.py`, `registry.py`, and the provider — with no type error if a required field is missing.
- **Fix:** Add `@dataclass class Portal` in `schema.py` with all known fields typed (use `Optional` for ATS-specific ones). `portal_reader.py` returns `list[Portal]` not `list[dict]`. Providers receive `Portal`. `india_only` becomes a first-class field with a docstring stating its semantics. All providers that read it must declare they handle it.
- **Done when:** `portal_reader.py` returns typed objects; `mypy scraper/` passes on provider files.

#### B2 — Move `COMPANY_INDUSTRY` to `KNOWN_PORTALS.md`
- **Why:** 200+ company→industry mappings are hardcoded in `portal_reader.py:22-233`. If a company name in `KNOWN_PORTALS.md` doesn't exactly match the key, industry silently becomes `''`. Updates require a Python edit. The dict is the longest block in `portal_reader.py`, burying the parsing logic.
- **Fix:** Add `industry: <value>` as an optional field per portal entry in `KNOWN_PORTALS.md`. `portal_reader.py` reads it directly. Remove the `COMPANY_INDUSTRY` dict. Emit a loud warning (not silent empty string) if `industry` is absent on a portal.
- **Done when:** `COMPANY_INDUSTRY` dict deleted; dry-run shows no empty industry fields for existing portals.

---

### Arch-Phase C — Pipeline Integrity (depends on B)

**Goal:** make failure visible — both validation drops and provider errors.

#### C1 — Consolidate three validation gates into one module
- **Why:** Validation is split across three files and three stages: identity checks in `validation.py:21-78`, description check in `main.py:210-215`, skill taxonomy check in `enricher.py:199-222`. A job with valid identity but empty description passes Gate 1, fails Gate 2, but its drop is never counted in validation stats (line 251). To understand what gets dropped and why you must read three files.
- **Fix:** Create `pipeline_validator.py` with a single `validate(job, stage: Literal["post_scrape", "pre_enrich", "post_enrich"]) -> ValidationResult` function. Move all three gates here, in dependency order: identity → description → skills. `main.py` calls one function per stage. All drop reasons funnel into one counter.
- **Done when:** `validation.py` content merged in; `main.py` validation calls reduced to one per stage; all drop reasons visible in one place.

#### C2 — Typed error returns from all providers
- **Why:** Providers return failure in three incompatible ways: `break` (workday), `return []` (smartrecruiters, greenhouse), `ProviderResult.fallback()` (workday on block, oracle on empty). `main.py` can't distinguish "no India jobs today" from "API blocked" from "wrong endpoint" without parsing log strings. `ProviderResult.fallback_policy` exists but most providers never populate it.
- **Fix:** Mandate all providers return `ProviderResult` with a `reason` field (use an enum: `SUCCESS`, `NO_JOBS`, `API_BLOCKED`, `CONFIG_ERROR`, `TIMEOUT`). Remove all bare `return []` from provider error paths. `registry.py` dispatch logs the reason. `main.py` decides on fallback based on typed reason, not log line parsing.
- **Done when:** Zero `return []` in provider error paths; `main.py` no longer inspects log strings to decide on fallback.

---

### Arch-Phase D — Config Consolidation (depends on B1)

**Goal:** eliminate the hidden second config file for Workday tenants.

#### D1 — Merge `company_registry.py` into `KNOWN_PORTALS.md`
- **Why:** `company_registry.py` (132 lines) is a mini-database of Workday tenant workarounds: non-standard facet names, missing India UUIDs, Cloudflare-blocked tenants. It's disconnected from `KNOWN_PORTALS.md` where the portal metadata lives. Adding a new Workday company requires editing both files. If a company appears in `KNOWN_PORTALS.md` but not the registry, the scraper silently attempts UUID discovery which may block. No audit trail of why entries exist.
- **Fix:** Add optional Workday-specific fields to `KNOWN_PORTALS.md` per portal: `workday_facet_param`, `workday_india_uuids`, `workday_search_text`. `portal_reader.py` (already updated in B1) populates these onto the `Portal` dataclass. `providers/workday.py` reads them from the typed portal; fallback to dynamic discovery only when absent. Delete `company_registry.py`.
- **Done when:** `company_registry.py` deleted; `--dry-run` shows all Workday portals parse correctly; Workday scraper results match pre-refactor baseline.

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
