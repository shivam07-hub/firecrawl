# CLAUDE.md — v3.2

Guidance for Claude Code in this repository.
Run history → `RUN_HISTORY.md`. Portal config → `KNOWN_PORTALS.md`.

> **DURABLE REFERENCE — DO NOT PRUNE.**
> This file is the permanent architecture, design, and mission record for this project.
> Only two sections change across sessions: `CURRENT STATE` (update each run) and `PENDING WORK` (update as tasks move).
> All other sections — MISSION, PIPELINE, SCHEMA, ATS ROUTING, FIRECRAWL DISCIPLINE, LLM ENRICHMENT, CRACK-ONCE, KNOWN ISSUES, COMMUNITY FRESHNESS — are permanent and must never be deleted or truncated, even when tasks complete.

---

## SCOPE

All work must stay within the `firecrawl_Supabase/` directory. Do not read, write, or modify files outside this folder.

---

## MISSION

Weekly global scrape of 100+ company portals → full JDs → LM Studio skill extraction → Supabase.
**Rule:** if a direct ATS API exists, use it. Firecrawl is the fallback, not the default.

---

## CURRENT STATE (as of 2026-05-04)

- **Active portals:** see `KNOWN_PORTALS.md` — file has expanded significantly beyond the previous 164 count; now includes 35+ sections with ATS-grouped companies, industry buckets, blocked lists, and a scrape queue. Exact active count = rows with `✅ working` status.
- **~19,000 jobs** in Supabase (`jobs` table, project `gipvxuugajkugntwkeiz`) — last exact count: 18,991
- **212,742 job_skills rows** resolved and uploaded
- Last full run: `upload_20260504_114053` — zero errors, zero taxonomy drift
- **20 new companies cracked by Codex** (2026-04-30 to 2026-05-02) — see `CODEX_HANDOFF.md` for full list and validation run results

### Output folder location
> **Outside this repo.** CSV/JSON outputs are never committed to git.
> Path: `/Users/incognito/Mirror CV/firecrawl_Supabase/All_CSV_Outputs_thru_firecrawl`
> Structure: 134 company folders, each containing `Outputs/<YYYYMMDD>/jobs.json` + `jobs.csv`
> This folder is the source of truth for Phase 3 (`csv_importer.py`) — it reads from here to upsert to Supabase.

---

## SCRAPER COMMANDS

```bash
cd scraper

# Phase 1 — scrape (Docker on, LM Studio off)
python main.py --dry-run                                        # verify portals parsed
python main.py --company "Stripe"                               # single company test
python main.py --skip-enrich --scope global --global-cap 2000  # full scrape, no LLM

# Inventory — safe by default (no Docker/Firecrawl)
python portal_inventory.py --no-probe                           # route/status inventory only
python portal_inventory.py --probe --sample-size 3              # direct providers only: current hiring sample
python portal_inventory.py --probe --sample-size 3 --limit 25   # batched direct-provider probe
python portal_inventory.py --merge ../logs/portal_inventory_*.json # merge batch reports
python portal_inventory.py --probe --include-js --sample-size 3 # includes JS routes; requires Docker/Firecrawl
python portal_inventory.py --probe --include-js --from-inventory ../logs/portal_inventory_<merged>.json --probe-states skipped_needs_docker,fallback_needs_docker --needs-docker-only --limit 10 --offset 0
                                                               # re-probe only prior Docker-needed rows

# Phase 2 — enrich (LM Studio on, Docker off)
python main.py --enrich-only

# Phase 3 — upload to Supabase
python csv_importer.py --dry-run    # verify counts, no writes
python csv_importer.py              # full upsert
python csv_importer.py --company "Stripe"  # single company smoke test
```

**Two-phase run required** — Docker and LM Studio can't run simultaneously (RAM constraint).
**Never use `--resume` for a fresh weekly run** — it skips companies with existing output folders.
**Docker is only needed for** full scrape fallback paths or `portal_inventory.py --probe --include-js`.

---

## SCRAPER PIPELINE

```
KNOWN_PORTALS.md  ←  portal config (URL, ATS type, company name)
      ↓
main.py + providers/  ←  ATS direct API → raw JSON per company
  (Firecrawl scrape() only as JS-heavy fallback, via Docker)
      ↓
enricher.py  ←  LM Studio → main_skills + side_skills from job_description
      ↓
csv_importer.py  ←  upsert to Supabase on job_id
                 ←  writes per-company health to scrape_diagnostics
```

**Key files:**

| File | Role |
|---|---|
| `config.py` | Env vars: LM Studio URL/key/model, Firecrawl URL, output paths |
| `portal_reader.py` | Parses `KNOWN_PORTALS.md` → list of portal dicts |
| `schema.py` | `Portal` TypedDict + `CANONICAL_FIELDS` — single source of truth |
| `providers/` | One module per ATS type — all scraping logic lives here |
| `workday_registry.json` | Per-tenant: India UUID, facet params, `blocked=true` flag — auto-written |
| `generic_registry.json` | Per-company: which JSON keys worked — auto-written on first success |
| `company_industries.json` | Company → Industry mapping — manual |
| `rag_skills.py` | IDF index over 35,108 Lightcast L3 skills — vocab for LLM |
| `enricher.py` | `enrich_job()` → RAG vocab → LM Studio → `main_skills` + `side_skills` |
| `writer.py` | `to_canonical()` → deduped JSON+CSV saved to output folder |
| `main.py` | Orchestrator — all CLI flags |
| `csv_importer.py` | Phase 3 upsert: dedup, lifecycle, apply_url gate, industry_group, location_city |
| `sql/` | Migration files — run manually via Supabase dashboard |

---

## CANONICAL SCHEMA (v3.1)

| Field | Source | Notes |
|---|---|---|
| `job_id` | ATS native ID | dedup key |
| `job_title` | ATS / page title | no LLM |
| `job_description` | ATS JD endpoint or Firecrawl | full text |
| `company_name` | KNOWN_PORTALS.md | |
| `industry` | company_industries.json | raw category (43 values) |
| `industry_group` | csv_importer mapping dict | 10-bucket super-category for UX filters |
| `role_domain` | LLM Phase 2 | 15-value controlled vocab |
| `location` | csv_importer `_normalize_location` | display string derived from raw |
| `location_raw` | ATS or Firecrawl | original scraped location string |
| `location_city` | csv_importer `_normalize_location` | canonical city name |
| `location_country` | csv_importer `_normalize_location` | canonical country — **required for True_Yodha match filter** |
| `location_mode` | csv_importer `_normalize_location` | `onsite` / `hybrid` / `remote` / `unknown` |
| `location_quality` | csv_importer `_normalize_location` | `ok` / `unknown` — hydration sentinel in True_Yodha |
| `apply_url` | ATS direct link | null if image/invalid URL |
| `main_skills` | LLM Phase 2 | top 5 must-have, Lightcast L3 |
| `side_skills` | LLM Phase 2 | nice-to-have, Lightcast L3 |
| `batch_date` | writer.py | integer YYYYMMDD |
| `first_seen` | csv_importer | set on INSERT only |
| `last_seen` | csv_importer | updated every run |
| `is_active` | community-owned | true on INSERT; only `job_reports` trigger sets false |
| `report_count` | job_reports trigger | incremented per report; at 5 → is_active=false |

### job_skills table (FK join table — canonical skill source)

`job_skills` is the source of truth for skill↔job relationships in True_Yodha.
`main_skills` / `side_skills` TEXT arrays on `jobs` are legacy and will be dropped once the contract test passes.

| Column | Type | Notes |
|---|---|---|
| `job_id` | uuid FK → jobs | |
| `skill_id` | uuid FK → skills | resolved via `skills.taxonomy_key` |
| `is_primary` | boolean | true = main_skill, false = side_skill |
| `required_level` | int (1–5) | **NOT YET ADDED** — see Pending Work §6 below |

**`required_level` contract (agreed 2026-05-07):**
- True_Yodha currently uses a heuristic: `is_primary → 4`, `is_primary=False → 2`
- This heuristic fires **only when `required_level` IS NULL**
- Once this column is populated by the scraper, True_Yodha automatically uses the real values — no code change needed
- Definition: the minimum proficiency level (1–5) a candidate needs in this skill to be considered qualified for the job role

---

## COMMUNITY FRESHNESS LAYER

Scraper = discovery (new jobs). Community = freshness (is this still open?).

### job_reports table (live in Supabase)
- Single "Report as Inactive" button — no reason dropdown
- Auth required (True_Yodha user account)
- 1 report per user per job — UNIQUE(job_id, user_id) enforced in DB
- Max 3 reports/day per user — backend guard in True_Yodha
- Reporter earns +10 XP → written to `daily_logs.skills_delta` as `community_reporter`
- **5 reports → Supabase trigger sets `is_active = false`**

### is_active ownership
- `csv_importer` sets `is_active = true` on INSERT only
- `csv_importer` **NEVER sets `is_active = false`** — partial scrapes cause false negatives
- Only `job_reports` trigger deactivates jobs

### Backend + frontend lives in True_Yodha repo
Full spec: `/Users/incognito/True_Yodha/docs/REPORT_INACTIVE_FEATURE.md`

---

## ATS ROUTING

| ATS | Method | Companies |
|---|---|---|
| Workday | Direct POST CXS API — India UUID + pagination + per-job JD fetch | Accenture, Thomson Reuters, 30+ others |
| SmartRecruiters | Direct GET `?country=in` — full JD in response | |
| Greenhouse | Direct GET — India filter in Python — full JD in response | |
| Lever | Direct GET `?location=india` | |
| Phenom | REST API per tenant | |
| Phenom SSR | GET search-results page → embedded `phApp.ddo.eagerLoadRefineSearch.data.jobs` → per-job JSON-LD detail | Adobe, ABB, Cisco, P&G |
| PCSX (Phenom CX) | GET `/api/pcsx/search?domain=X&location=india&start=N` + per-job HTML JSON-LD | |
| Pinpoint | GET `/en/postings.json?location_id[]=ID1&location_id[]=ID2` | |
| Darwinbox | POST `/ms/candidateapi/job/alljobs` — requires CF cookies in env vars | Swiggy, Flipkart, Myntra, OYO, IIFL |
| Oracle HCM | GET finder=findReqs + India locationId; JD from API or HTML `og:description` fallback | |
| Taleo (Oracle TBE) | POST `/services/jobs/search/` + per-job HTML BeautifulSoup | HCL Technologies |
| TalentBrew | Direct paginated HTML — India location filter in URL path + per-job detail page | Intuit, ADP |
| Siemens ExternalJobs | GET `/SearchJobs` paginate with `folderOffset` → per-job `/JobDetail/{id}` HTML | Siemens |
| H&M WP Jobs | POST `/wp-json/hm/v1/sr/jobs/search` with `{"locations":["cou:in"],"page":N}` | H&M |
| Yello (Recsolu) | GET `/job_boards/{board_id}/search?filters={country_id}&page_number=N` → per-job detail page | EY India |
| SAP Jobs2Web HTML | GET `/search/?locationsearch=india&startrow=N` paginated HTML → per-job detail page | Alstom, Monitor Deloitte, EY India Experienced |
| PepsiCo Jobs API | GET `pepsicojobs.com/api/jobs?country=India&page=N` JSON | PepsiCo |
| Deloitte USI (BrassRing) | GET `usijobs.deloitte.com/careersUSI/SearchJobs?jobOffset=N` paginated HTML | Deloitte India |
| Skima Careers | GET HTML `?page=N` → per-job `/{uuid}` detail page | Nykaa |
| Aditya Birla (custom) | GET `/api/v3/jobs` + per-job `/api/v3/job/{jcode}` — Bearer token | |
| Generic JSON | Configurable field mapping per company — auto-saved to `generic_registry.json` | Atlassian + others |
| JS-heavy (Eightfold, Avature, SPAs) | `scrape_extract()` via Firecrawl (Docker first, cloud last resort) | Goldman Sachs, Eightfold tenants |

---

## FIRECRAWL CREDIT DISCIPLINE

1. Always use `firecrawl-py` SDK — never raw HTTP.
2. One singleton `_app` instance in `firecrawl_client.py`. Never instantiate elsewhere.
3. Never use `crawl()`.
4. Two permitted calls: `fc.scrape(url)` (1 credit) and `fc.extract(urls, schema, prompt)` (JS-heavy only).
5. Priority order: Direct ATS API → Docker → Firecrawl cloud.

---

## LLM ENRICHMENT FLOW

1. `job_description` populated by scraper
2. `rag_skills.py` retrieves top-40 Lightcast L3 skills from JD as vocabulary
3. `enrich_job()` sends vocab + JD to LM Studio (`gemma-3-4b`, max_tokens=150, temp=0.0)
4. LLM returns `main_skills` (top 5 must-have) + `side_skills` (nice-to-have)
5. `_validate_enrichment()` validates against Lightcast L3 — invalid values dropped

---

## "CRACK ONCE, REUSE FOREVER" — CORE PRINCIPLE

| Registry | Purpose | Auto-written? |
|---|---|---|
| `workday_registry.json` | Per-tenant: India UUID, facet params, `blocked=true` | Yes |
| `generic_registry.json` | Per-company: which JSON keys worked | Yes |
| `company_industries.json` | Company → Industry | Manual |

**`blocked=true`** = Cloudflare blocks all POSTs. Scraper skips API, goes straight to Firecrawl.
Confirmed blocked: Engie, GE Aerospace, Bank of America, Ford, Medtronic, Inspire Brands, Hitachi Vantara, Intuit, AMD, ANZ Bank, Keysight, Deutsche Bank, Standard Chartered Bank, Eli Lilly.

**Darwinbox CF Turnstile** (Swiggy, Flipkart, Myntra, OYO, IIFL Finance): provider built, needs `DARWINBOX_CF_BM` + `DARWINBOX_SESSION` env vars. Get from browser devtools → Network → `alljobs` POST → Copy as cURL. Cookies expire in 30 min, IP-bound.

---

## KNOWN ISSUES

- Eightfold API returning 404 as of 2026-04-10 — Firecrawl fallback quality varies
- Goldman Sachs (TAL.NET) requires browser JS — Firecrawl markdown quality varies
- MSCI: `careers.msci.com` 404; Workday slug unknown — skipped
- Dell: Workday returns 200+empty — suspected CF-blocked; add `blocked=true` if confirmed
- ARM Holdings: TalentBrew cURL was wrong file (not jobs API) — need XHR to actual JSON endpoint
- EY India Experienced (`sap_jobs2web_html`): many postings have JD text of only `Requisition Id : <id>` — descriptions too short, ~50% drop rate

---

## PENDING WORK

### 1 — ATS Crack Hunt (uncracked companies)

**Workflow:** Open career page → DevTools → Network → XHR tab → find JSON request with job titles → Copy as cURL → paste here → Claude tests + saves to registry.

| Company | Career URL | Suspected ATS | Notes |
|---|---|---|---|
| 🟡 IIFL Finance | iifl.darwinbox.in | Darwinbox | Provider ready — needs CF cookies |
| 🟡 Flipkart | flipkartcareers.com | Darwinbox | Provider ready — needs CF cookies |
| 🟡 OYO | oyorooms.com/about/ | Darwinbox | Provider ready — needs CF cookies |
| LTIMindtree | ltimindtree.com/careers | Unknown | Inspect XHR |
| AMD | amd.com/en/corporate/careers | iCIMS | Find exact XHR endpoint |
| Netflix | jobs.netflix.com | Custom Next.js | Find JSON API |
| Meta | metacareers.com/jobs | Custom GraphQL | Find GraphQL endpoint + params |
| Deutsche Bank | careers.db.com | SAP SuccessFactors | Find tenant + OData endpoint |
| Standard Chartered | sc.com/en/global-careers | Workday CF-blocked | Find India UUID |
| Keysight Technologies | jobs.keysight.com | SAP SF suspected | Inspect XHR |
| ANZ Bank | careers.anz.com | Workday CF-blocked | Find India UUID |
| Eli Lilly | careers.lilly.com | Phenom | CF-blocks `/api/jobs` |
| Societe Generale | careers.societegenerale.com | Workday CF-blocked | Inspect XHR |
| IndusInd Bank | indusind.bank.in | Unknown | Inspect XHR |
| Mu Sigma | mu-sigma.com/careers | Unknown | Inspect XHR |
| Ola Electric | olaelectric.com/careers | Unknown | Inspect XHR |
| Kearney | kearney.com/about/locations/india | Unknown | Inspect XHR |

**Workday CF-blocked** (need India UUID via browser, then add to workday_registry.json):
Engie, GE Aerospace, Bank of America, Ford, Medtronic, Inspire Brands, Hitachi Vantara, Intuit, Societe Generale, Standard Chartered, ANZ Bank.

### 2 — Fix broken direct scrapers
- Verify Phenom REST endpoints: BCG, PMI, Oliver Wyman (unverified API paths)
- Fix Workday slugs: Capgemini, MSCI (HCL cracked via Taleo — done)
- Fix SmartRecruiters: Zomato, S&P Global, CRISIL (unconfirmed IDs)
- Fix HP/HPE Phenom endpoint (returning HTML — needs correct slug)

### 3 — New ATS providers still needed
- **Workable**: `GET https://apply.workable.com/api/v3/accounts/{slug}/jobs?state=published`
- **SAP SuccessFactors**: `GET https://{tenant}/odata/v2/JobRequisitionLocale?$filter=...&$format=json` — targets: GMR Group, Deutsche Bank
- **Ashby**: `GET https://api.ashbyhq.com/posting-api/job-board/{slug}` — target: Mondee

### 4 — Architecture (remaining)
- **Firecrawl result cache** — `firecrawl_cache.json` keyed by URL, 7-day TTL. Cache hit → skip re-scrape, save credits.
- **Provider override consolidation** — if a future route needs special handling, add it through `portal_reader.py` + `scraper/providers/`, not a bespoke script folder.

### 6 — Add `required_level` to `job_skills` (unblocks True_Yodha skill gap display)

**What:** Add `required_level INT` column to `job_skills` table. Scraper populates it during Phase 2 enrichment.

**Why:** True_Yodha shows `L0→L4` skill gap cards on the home dashboard. Until this column exists, it uses a heuristic (primary=4, secondary=2). Real values will improve accuracy.

**SQL migration (run via Supabase dashboard):**
```sql
ALTER TABLE job_skills ADD COLUMN IF NOT EXISTS required_level INT CHECK (required_level BETWEEN 1 AND 5);
```

**Scraper change (`enricher.py` / LLM prompt):**
For each skill returned by the LLM, also return `required_level` (1–5).
LLM prompt addition: *"For each skill, also output `required_level` (1=aware, 2=practitioner, 3=proficient, 4=expert, 5=master) — the minimum level needed to succeed in this role."*

**`csv_importer.py` change:**
When writing to `job_skills`, include `required_level` from the enriched skill dict if present. Null is fine — True_Yodha falls back to heuristic.

**True_Yodha contract:** no code change needed — fallback already handles NULL.

### 5 — Archon weekly cadence
- Weekly cron: `0 2 * * 0` via `.archon/workflows/scraper-weekly-run.yaml`
- After each run: update `RUN_HISTORY.md` + `KNOWN_PORTALS.md`

---

## CLAUDE CODE SKILLS

| Skill | Trigger |
|---|---|
| `graphify` | `/graphify` |
| `triage-issue` | `/triage-issue` |
| `to-issues` | `/to-issues` |
| `to-prd` | `/to-prd` |
| `review` | `/review` |
| `security-review` | `/security-review` |
| `tdd` | `/tdd` |
| `simplify` | `/simplify` |
| `improve-codebase-architecture` | `/improve-codebase-architecture` |
| `caveman` | `/caveman` |
| `grill-me` | `/grill-me` |
| `find-skills` | `/find-skills` |
| `karpathy-guidelines` | `/karpathy-guidelines` |
| `fewer-permission-prompts` | `/fewer-permission-prompts` |
