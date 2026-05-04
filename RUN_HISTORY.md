# RUN HISTORY

Chronological log of scraper sessions, data quality incidents, and resolved bugs.
Current architecture and run commands live in `CLAUDE.md`. Portal config lives in `KNOWN_PORTALS.md`.

---

## Session 2026-05-02 — Procter & Gamble cracked via Phenom SSR embed

**Scope:** Parser + portal docs update for P&G direct route (no Firecrawl fallback).

**Validation evidence:**
- `GET https://www.pgcareers.com/in/en/search-results?m=3&location=MUMBAI%2C%20India` returns embedded `phApp.ddo.eagerLoadRefineSearch.data.jobs`.
- Same page embeds fields needed by scraper: `jobSeqNo`, `jobId/reqId`, `title`, `location/country`, `applyUrl`, `descriptionTeaser`.
- Country aggregation in snapshot confirms India results are available; global India facet count observed as `23`.

**Code/docs updated:**
- `scraper/portal_reader.py`: PHENOM section override added for `Procter & Gamble` → `ats=phenom_ssr`, endpoint `https://www.pgcareers.com/in/en/search-results?qcountry=India`.
- `KNOWN_PORTALS.md`: P&G row updated to `✅ CRACKED 2026-05-02` with route details.

**Targeted run result:**
- Command: `python3 scraper/main.py --company \"Procter & Gamble\" --skip-enrich --company-cap 200`
- Result: `23 raw` scraped, `23` saved.
- Output: `All_CSV_Outputs_thru_firecrawl/Procter_Gamble/Outputs/2026_05_02/jobs.json`

---

## Session 2026-05-02 — H&M cracked via WordPress jobs API

**Scope:** Added direct provider route for H&M (no manual DevTools cURL required at runtime).

**Validation evidence:**
- Careers URL observed: `https://career.hm.com/in-en/search/?l=cou%3Ain`
- Jobs endpoint confirmed: `POST https://career.hm.com/in-en/wp-json/hm/v1/sr/jobs/search?_locale=user`
- India payload filter confirmed: `{"locations":["cou:in"],"page":N}`
- API response contains `jobs[]` + `total`; snapshot observed `111` India jobs.

**Code/docs updated:**
- Added provider: `scraper/providers/hm_wp_jobs.py`
- Registered provider: `scraper/providers/registry.py` (`hm_wp_jobs`)
- Parser mapping: `scraper/portal_reader.py` (`H&M -> ats=hm_wp_jobs`, `india_only=True`)
- Schema comment updated: `scraper/schema.py`
- Industry mapping updated: `scraper/company_industries.json` (`"H&M": "Retail"`)
- Portal registry updated: `KNOWN_PORTALS.md` (OTHER PLATFORMS row + tracker entry)
- Handoff updated: `CODEX_HANDOFF.md` (progress table + validation signal)

**Targeted run result:**
- Command: `python main.py --company "H&M" --skip-enrich --company-cap 300`
- Result: `111 raw` scraped, `111` saved.
- Output: `All_CSV_Outputs_thru_firecrawl/HM/Outputs/2026_05_02/jobs.json`
- Run summary: `logs/run_summary_20260502_132049.json`

---

## Session 2026-05-02 — Nykaa cracked via Skima careers SSR HTML

**Scope:** Code + registry + docs update for direct Nykaa route (no Firecrawl fallback).

**Validation evidence:**
- `GET https://careers.nykaa.com/` returns server-rendered job listing HTML with UUID links (no auth/cookies).
- Pagination confirmed via `data-last-page` + query param `?page=N` (snapshot: 2 pages, 11 jobs).
- Job detail pages (`/{job_uuid}`) return full JD in `.job-description-panel`.

**Code/docs updated:**
- Added provider: `scraper/providers/skima_careers.py` (listing + pagination + detail scraping).
- Routed Nykaa to provider: `portal_reader.py` (`Nykaa -> ats=skima_careers`, `india_only=True`).
- Registered provider in `scraper/providers/registry.py`.
- `KNOWN_PORTALS.md`: Nykaa changed to `✅ CRACKED 2026-05-02` with Skima route notes.

**Targeted run result:**
- Command: `python3 scraper/main.py --company \"Nykaa\" --skip-enrich --company-cap 200`
- Result: `11 raw` scraped, `11` saved.
- Output: `All_CSV_Outputs_thru_firecrawl/Nykaa/Outputs/2026_05_02/jobs.json`

---

## Session 2026-05-02 — Atlassian route confirmed from browser cURL + bundle inspection

**Scope:** Parser + documentation update for direct JSON route.

**Validation evidence:**
- `https://www.atlassian.com/company/careers/all-jobs?team=Interns%2CGraduates&location=&search=` resolves as JS-rendered careers shell.
- Bundled careers code points production listings to `GET /endpoint/careers/listings`.
- `GET https://www.atlassian.com/endpoint/careers/listings` returns JSON array (82 jobs in snapshot).
- Job objects include `id`, `title`, `locations`, `overview`, `responsibilities`, `qualifications`, `applyUrl`.

**Code/docs updated:**
- `scraper/providers/generic_json.py`: added support for `locations[]`, sectioned JD fields, and `applyUrl` mapping.
- `KNOWN_PORTALS.md`: Atlassian moved from broken Greenhouse row to `CUSTOM / PROPRIETARY APIs` as `✅ CRACKED 2026-05-02`.
- `KNOWN_PORTALS.md`: Atlassian removed from `SCRAPE_QUEUE`.
- `AGENTS.md` and `CODEX_HANDOFF.md`: updated with Atlassian validation notes.

---

## Session 2026-05-02 — Cisco route confirmed from browser cURL

**Scope:** Documentation + handoff status update (no scraper code change in this session).

**Validation evidence:**
- `https://careers.cisco.com/global/en/search-results?qcountry=India` returns embedded `phApp.ddo.eagerLoadRefineSearch` payload.
- India filter present in payload: `ui_selections.country=["India"]`; country aggregation reports `India=226`.
- Pagination confirmed with `from=10&s=1` (10 jobs/page payload).
- Job objects include `jobId/reqId`, `title`, `location`, `descriptionTeaser`, `applyUrl`.

**Docs updated:**
- `KNOWN_PORTALS.md`: Cisco changed from `🔍 needs investigation` to `✅ cracked 2026-05-02`; queue item removed.
- `AGENTS.md`: new run-history entry for Cisco crack confirmation.
- `CODEX_HANDOFF.md`: progress table and validation notes updated with Cisco route.

---

## Session 2026-05-02 — Tech Mahindra route confirmed

**Scope:** Documentation + handoff status update (no scraper code change in this session).

**Validation evidence:**
- `https://www.techmahindra.com/en-in/careers/` is 404.
- `https://www.techmahindra.com/careers/` is live and links out to `https://careers.techmahindra.com/`.
- `https://careers.techmahindra.com/` returns listing cards with direct `JobDetails.aspx?JobCode=...` links.
- `JobDetails.aspx` pages include full JD sections and apply controls; suitable for direct scrape + India filter by location text.

**Docs updated:**
- `KNOWN_PORTALS.md`: Tech Mahindra moved from broken/url-changed to `✅ cracked 2026-05-02`.
- `KNOWN_PORTALS.md`: removed Tech Mahindra from `SCRAPE_QUEUE`.
- `AGENTS.md`: run-history entry added for Tech Mahindra crack.

---

## Session 2026-04-27 — Global scope controls + lifecycle/versioning + diagnostics

**Code changes:**
- `scraper/main.py`
  - Added `--scope india|global` (default `india`) and `--global-cap` (default `2000`).
  - Added unresolved-company diagnostics in run summary JSON (`no_jobs_returned`, scrape/save exceptions).
  - Added best-effort Supabase diagnostics sink (`scrape_diagnostics` table).
- `scraper/scrapers.py`
  - Removed placeholder fallback rows from Firecrawl paths (`scrape_validate`, `scrape_extract` now return `[]` when no links are parseable).
  - Made provider filters scope-aware so `india_only` can be forced by run scope.
  - Added adapter-level cap wiring for global mode (`greenhouse`, `lever`, `phenom_api`, generic JSON parse path).
- `csv_importer.py`
  - Default quality gate changed to `--min-score 0` to keep all valid non-placeholder jobs.
  - Added mixed-schema normalization support (legacy + canonical).
  - Added lifecycle/versioning logic:
    - `first_seen`, `last_seen`, `is_active`, `change_fingerprint`.
    - Meaningful-change version events (`insert` / `update` / `deactivate`) in `job_versions`.
    - **Inactive after 1 miss** (if a previously active job is absent in a successful company run).
- `.archon/workflows/scraper-weekly-run.yaml`
  - Switched cadence to weekly.
  - Made dry-run and scrape phases global-scope by default.
- New docs/scripts:
  - `scraper/ARCHITECTURE_V3_MODULAR_PLAN.md`
  - `scraper/sql/create_scrape_diagnostics.sql`
  - `scraper/sql/create_job_lifecycle.sql`
  - `scraper/sql/create_jobs_india_view.sql`

**Data quality impact (2026-04-27):**
- Placeholder cleanup completed (historic Firecrawl placeholder rows removed from Supabase).
- Import path now preserves real low-count companies instead of forcing synthetic 1-row placeholders.
- Confirmed global-scope smoke test: `Thoughtworks` returned 46 jobs in one company run.

**Infrastructure status (confirmed by user):**
- All 3 SQL scripts executed successfully on Supabase:
  - `create_scrape_diagnostics.sql`
  - `create_job_lifecycle.sql`
  - `create_jobs_india_view.sql`

**Operating model decision (locked):**
- Weekly full run in **global** scope.
- On-demand full/targeted dumps anytime the scraper agent is called.
- India dataset is derived downstream from global via `jobs_india` view/filter.
- Global per-company cap: `2000`.
- Versioning tracks **meaningful changes only** (`job_title`, `job_description`, `location`, `apply_url`).

---

## Session 2026-04-19 — Portal expansion + JD fix

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
- Publicis Sapient → SmartRecruiters returns 0 for all IDs tried; careers site is SPA with unknown ATS
- ING Bank → no India locations in ICSGBLCOR portal
- Roche → only 1 India job (not worth scraping)

**Unresolved:**
- Societe Generale: SmartRecruiters `SocieteGenerale4` — `country=in` returns 0; try location text filter
- Storable: Greenhouse board confirmed but India jobs TBD
- 74 companies returning 1 Firecrawl blob — need direct API scrapers

---

## Session 2026-04-17 — Phase 1 full scrape + RAG enrichment pipeline

**Code changes this session:**
- `scraper/rag_skills.py` (NEW) — IDF-weighted keyword inverted index over 35,108 Lightcast L3 skills. `retrieve(text, k=40)` returns top-k canonical skill names via token overlap scoring (IDF-weighted + length-normalized). Builds in <0.5s at import. Used in enricher to inject constrained vocabulary into every LLM prompt.
- `scraper/enricher.py` — RAG-augmented: `enrich_job()` calls `_retrieve_skills(title + jd[:800], k=40)`, injects into `_ENRICH_PROMPT` as "Approved skill vocabulary — choose ONLY from this list". System prompt moved to LM Studio GUI for KV-cache reuse. `max_tokens` 300→150. JD truncation 2000→1500 chars.
- `scraper/main.py` — `enrich_only_run()` parallelised with `ThreadPoolExecutor(max_workers=ENRICH_WORKERS)`.
- `scraper/config.py` — added `ENRICH_WORKERS = int(os.getenv("ENRICH_WORKERS", "4"))`.
- `scraper/.env` — added `ENRICH_WORKERS=4`; dual model presets (`MODEL_SPEED=fast` → `google/gemma-3-4b`, `MODEL_SPEED=quality` → `deepseek-r1-0528-qwen3-8b-mlx`).

**LM Studio GUI preset (`mirror-cv-fast`):**
- System Prompt: "You are a precise job data extractor. Read the job title and description and return a single valid JSON object. No explanation, no markdown, no extra text."
- Limit Response Length: 150 tokens
- Temperature: 0.0

**Phase 1 run results:**
- `python main.py --skip-enrich` completed. 94 output files, 2,376 total jobs, 1,730 with `job_description`.
- Output path: `/Users/incognito/Mirror CV/firecrawl/All_CSV_Outputs_thru_firecrawl/` (set via `OUTPUT_BASE` in .env)

---

## Session 2026-04-16 — Taxonomy + Workflow setup

**Code changes:**
- `scraper/lightcast_skills_taxonomy.json` — created; full Lightcast Open Skills L1→L2→L3 hierarchy (31 L1, 442 L2, 35,108 L3 skills)
- `scraper/lightcast_skills_flat.csv` — flat table (l1_category, l2_subcategory, l3_skill_name, l3_skill_id, 35,108 rows)
- `scraper/enricher.py` — LLM skills validated against Lightcast L3 taxonomy. Three match strategies: exact, stripped-parenthetical ("Docker" → "Docker (Software)"), fuzzy (cutoff=0.88, min 8 chars)
- `.archon/workflows/scraper-weekly-run.yaml` — created; 7-node DAG: check-docker + check-lm + test-portals (parallel) → scrape → enrich → upload → summarize

**Workflow run notes:**
- `check-lm` failed as expected (LM Studio was off); `scrape` completed in 18 min but scraped 0 new data because `--resume` was mistakenly left in the workflow command — all 44 companies already had output from 2026-04-12 and were skipped.
- **Fixed**: removed `--resume` from the `scrape` node command.

**State of All_CSV_Outputs_thru_firecrawl/ at session close (44 companies, last scraped 2026-04-12):**
Accenture (500), Sanofi (596), Novartis (592), Wells Fargo (224), Salesforce (168), Continental (99), Airbus (144), Stripe (66), Volvo Group (43), Shell (32), ServiceNow (35), Fidelity (29), Amazon (81), Michelin (21), LDC (20), WESCO (20), AstraZeneca (25), Schneider Electric (126), Philips (136), Eli Lilly (10), Dell (18), Stellantis (18)
Low/broken: Engie (2), Baker Hughes (2), Morgan Stanley (2), AmEx (3), Google (3), Infosys (3), TCS (3), Wipro (3), Cognizant (0), Alstom (1), Chanel (1), Apple (2), CNHI (3), CMA CGM (0), TotalEnergies (0), Synopsys (0), Mastercard (0), Microsoft (0), Volkswagen (5/excluded)

---

## Session 2026-04-11 — Phase 1 + Phase 2 COMPLETE

**Code fixes:**
- Workday headers → browser-like UA + Accept-Language + dynamic Referer
- Workday facet param → `_find_india_id()` returns `(facet_param, uuid)` tuple (tenant-specific names)
- Workday Cloudflare 303 → automatic Firecrawl fallback using `careers_url`
- `--skip-enrich` suppresses LLM in Firecrawl path; saves `firecrawl_raw.md` staging file
- `--enrich-only` processes all `firecrawl_raw.md` staging files → extract + enrich
- `portal_reader.py` passes `careers_url` field for Workday portals
- No-India-Jobs companies consolidated into excluded block in KNOWN_PORTALS.md

**25 companies with enriched jobs.json:**
Accenture (8240), Amazon (92), Wells Fargo (235), Salesforce (169), Continental (99),
Sanofi (93), Stripe (66), ServiceNow (35), Airbus (40), Fidelity (30), Shell (27),
LDC (20), STMicro (3), Morgan Stanley (3), AmEx (3), Chanel (1),
Eli Lilly (3), Google (3), Infosys (3), L'Oréal (3), TCS (3), Wipro (3),
Cognizant (2), Stellantis (3), AstraZeneca (3)

---

## Session 2026-04-10 — First full run (interrupted)

- Ran `python main.py` (full run, all portals).
- Force-closed mid-way due to memory pressure from running Docker + LM Studio simultaneously.
- 15 companies scraped before interruption: Accenture, Airbus, Amazon, American Express, Chanel, Continental, Fidelity Investments, LDC (Louis Dreyfus), Morgan Stanley, STMicroelectronics, Sanofi, ServiceNow, Shell, Stripe, Wells Fargo.
- Output location: `All_CSV_Outputs/{Company}/Outputs/YYYY_MM_DD/jobs.json` + `jobs.csv`

---

## DUMP 2 ANALYSIS — Root Cause Diagnosis (2026-04-11)

**Context:** Dump 2 contained 2,774 jobs from 25 companies with severe data quality issues.

### Problem 1 — Workday: zero raw_jd_text
`scrapers.py:76` reads `p.get('jobDescription', '')` from the listing endpoint `/wday/cxs/{tenant}/{site}/jobs`. That endpoint never returns full JD — it returns only metadata. Full JD lives at the individual job detail endpoint: `GET https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs/{externalPath}`.
**Fix applied:** second-pass fetch per job's `externalPath`. Now 169/169 JDs fetched.

### Problem 2 — Accenture: 8,240 jobs scraped, 1,841 unique (6,399 duplicates)
- India filter matched broader facet than just India.
- Workday offset-based pagination returns overlapping result sets on Accenture's tenant.
**Fix applied:** deduplicate by `jobReqId` during pagination loop; break early if >50% already-seen IDs.

### Problem 3 — Firecrawl companies: exactly 3 jobs each
`main.py:109` sliced Firecrawl output to `pages[:5]`; LM Studio extracted first 3-5 visible jobs and stopped.
**Fix applied:** removed `pages[:5]` slice; use all pages. Longer-term: direct ATS APIs where possible.

### Problem 4 — skills_required, seniority_level all empty
Enrichment skipped because `raw_jd_text` was empty (Problem 1). Resolved by fixing Problem 1.

### BUILD CHUNK 1 — Audit + fixes (COMPLETED 2026-04-16)

**Dry-run results:** 106 portals parsed (43 direct API, 63 Firecrawl/js-required).

**Spot-check (5-job test per ATS type):**
| ATS | Company | Jobs | JD populated | Location | Verdict |
|-----|---------|------|-------------|----------|---------|
| Greenhouse | Stripe | 69 | ✅ 3-5k chars | ❌ Empty | Fix location mapping |
| SmartRecruiters | ServiceNow | 29 | ✅ 2-3k chars | ✅ | Working |
| Custom JSON | Amazon | 93 | ✅ 1-3k chars | ❌ None | Fix location mapping |
| Workday | Salesforce | 169 | ❌ 0 chars | ❌ None | JD fetch broken — critical |
| Phenom REST | Schneider Electric | 10 | ✅ 6-12k chars | ❌ None | Fix location mapping |

**Fixes applied:**
1. Workday JD fetch — `cxs_base` was missing `career_site` segment. Fixed in `scrapers.py:_fetch_workday_jds()`.
2. Location empty — `writer.py:to_canonical()` now defaults to `'India'` when location is empty.
3. Firecrawl Workday fallback — if CXS API fails, falls back to `fc.batch_scrape()` on human-facing job URL.

**Verified clean after fixes:**
| ATS | Company | Jobs | JD | Location |
|-----|---------|------|-----|----------|
| Workday | Salesforce | 169 | ✅ 8-11k chars | ✅ Real city |
| Greenhouse | Stripe | 69 | ✅ 4-5k chars | ✅ Bengaluru |
| Custom JSON | Amazon | 93 | ✅ 1-3k chars | ✅ City+State+IND |
| Phenom REST | Schneider Electric | 10 | ✅ 6-12k chars | ✅ |
