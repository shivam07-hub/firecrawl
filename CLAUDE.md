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

## CURRENT STATE (as of 2026-05-13)

- **Discovery-mode override for the current crack hunt:** do **not** block on tests, smoke runs, or full scrape verification when a likely ATS/XHR endpoint has been identified. For this phase, **capturing the endpoint/host/domain/siteNumber/locationId and saving it into `KNOWN_PORTALS.md`, `portal_reader.py`, or a provider registry is more important than proving it end-to-end.** Validation will happen later in a dedicated pass.
- **Firecrawl cloud is now approved as a discovery microscope** for endpoint hunting. Use `map -> selective scrape`, then promote the durable direct route. Do not leave Firecrawl as the final architecture unless the portal is genuinely anti-bot / JS-opaque.
- **American Express moved off the broken Eightfold assumption and onto Oracle Candidate Experience**:
  - careers shell: `https://careers.americanexpress.com/en/sites/CX_1/jobs`
  - API host: `egug.fa.us2.oraclecloud.com`
  - site number: `CX_1`
  - India location ID: `300000000228786`
  - response path: `recruitingCEJobRequisitions?finder=findReqs`
- **Direct-route promotions completed (earlier sessions):** `STMicroelectronics`, `GMR Group`, `HP (HPE)`, `HiLabs`, `Black Brix`, `American Express`.
- **Crack-hunt session 2026-05-13 — new promotions:**
  - `Nestlé` ✅ — SAP Jobs2Web HTML at `jobdetails.nestle.com/search/?q=&locationsearch=india`; 31 India jobs across 4 pages; routed via `_ATS_OVERRIDES` + `_OTHER_ENDPOINT_OVERRIDES` in `portal_reader.py`
  - `ITC Limited` ✅ — Zoho Recruit SSR portal at `recruitment.itcportal.com/jobs/Careers`; 62 India jobs; new provider at `providers/zoho_recruit.py`; apply URL pattern: `SingleJobDetail.na?sys_id={id}&page_id=48611000000181149`
  - `Adidas` ✅ — SAP Jobs2Web HTML at `jobs.adidas-group.com/search/?q=&optionsFacetsDD_country=IN`; routing fixed in `portal_reader.py`
  - `Unilever` ✅ — TalentBrew at `careers.unilever.com/en/location/india-jobs/34155/1269750/2`; moved from WORKDAY section (was CF-blocked) to CONSUMER GOODS; endpoint override in `portal_reader.py`
  - `Oracle` ✅ — Oracle CE (NOT Workday) confirmed via XHR cURL; API host `eeho.fa.us2.oraclecloud.com`; siteNumber `CX_45001`; `location=India` text param (no numeric locationId); moved from WORKDAY to ORACLE HCM section; `_ORACLE_ENDPOINT_OVERRIDES` in `portal_reader.py`; 5+ live India jobs verified
- **portal_reader.py fixes this session:**
  - `_workday()` skip condition now checks `'⚠️' in tenant` (not just instance/career_site) — prevents Unilever and other moved entries from leaking through as broken Workday portals
  - `_OTHER_ENDPOINT_OVERRIDES` dict added — allows `_other()` to use a different endpoint than the `Careers URL` column (used by Nestlé, Unilever, ITC Limited)
  - `_ATS_OVERRIDES` + `_INDIA_ONLY_OVERRIDES` extended for Adidas, Nestlé, Unilever, ITC Limited
  - `_ORACLE_ENDPOINT_OVERRIDES` dict added — Oracle Corp uses `location=India` text param instead of numeric locationId; override bypasses standard endpoint builder
- **Bank of America** — `careers.bankofamerica.com/en/jobs/` URL tested → 404; Workday entry unchanged; still needs correct Oracle CE or Workday URL from browser XHR
- **Grant Thornton status:** TalentRecruit (`gtprod.talentrecruit.com`) is an **internal SSO-gated ATS** — not a public career page. FC map found `/career-page/jobs` but scrape returns login screen. No public portal found on `grantthornton.in`. Marked as internal/inaccessible in PENDING WORK.
- **Firecrawl cloud discovery signals captured this session:**
  - `Vehere Interactive`: Firecrawl surfaced durable `/positions/...` detail URLs even though direct requests still hit Cloudflare 403.
  - `Meta`: Firecrawl can read the India jobs shell at `https://www.metacareers.com/jobs/?locations[0]=India`, but the stable direct JSON/GraphQL route still needs XHR capture.
  - `Mondee Holdings`: Ashby board confirmed at `https://jobs.ashbyhq.com/mondee`; obvious posting API slug still unresolved / effectively empty.
- **Important handoff note:** if `main.py` hangs on a portal during this discovery phase, that is **not** a reason to defer capturing the endpoint. Save the endpoint first, move on, and leave runtime verification for later.

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
enricher.py  ←  LM Studio → role_domain + structured skills with required_level
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
| `enricher.py` | `enrich_job()` → RAG vocab → LM Studio → structured `skills` + back-compat arrays |
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
| `required_level` | smallint (1–4) | scraper-owned proficiency signal; migration file: `scraper/sql/add_job_skills_required_level.sql` |

**`required_level` contract (updated 2026-05-10):**
- L1 = awareness/basic, L2 = working proficiency, L3 = advanced/practitioner, L4 = expert/authority
- LM Studio returns `skills[]` objects: `{name, is_primary, required_level}`
- `_validate_enrichment()` canonicalizes skill names, caps primary skills at 5 and side skills at 8, and derives legacy `main_skills` / `side_skills`
- `csv_importer.py` and `supabase_enricher.py` stop before real writes if Supabase has not run `scraper/sql/add_job_skills_required_level.sql`
- True_Yodha should read `job_skills.required_level` directly and keep any heuristic only as a fallback

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
- Community reports can still deactivate jobs through the `job_reports` trigger
- Scraper decommissioning is opt-in: `csv_importer.py --deactivate-missing`
- Scraper decommissioning only compares companies represented by one run date; real writes require `--run-date YYYYMMDD`
- Dry-run decommissioning can omit `--run-date` to inspect the newest output date without writes
- Companies absent from that run date are never touched
- The importer blocks deactivation if upload quality fails or if one company would deactivate more than 75% of active rows, unless `--allow-large-deactivation` is explicitly passed

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
4. Three permitted discovery/extraction calls:
   - `fc.map_site(url, ...)` — discovery-first URL enumeration (1 credit per site)
   - `fc.scrape(url)` — targeted markdown fetch (1 credit per URL)
   - `fc.extract(urls, schema, prompt)` — JS-heavy structured fallback only
5. Preferred workflow for crack-hunt sessions: **Direct ATS guess → Firecrawl `map_site()` → selective `scrape()` on the best 1-3 URLs → save the direct endpoint.**
6. Priority order: Direct ATS API → Firecrawl map/scrape for discovery → Docker/Firecrawl fallback for opaque portals → later validation.
7. During the current endpoint-capture phase, **do not spend credits on broad verification runs**. Capture the route and move forward.

---

## LLM ENRICHMENT FLOW

1. `job_description` populated by scraper
2. `rag_skills.py` retrieves top-40 Lightcast L3 skills from JD as vocabulary
3. `enrich_job()` sends vocab + JD to LM Studio (`gemma-3-4b`, max_tokens=512, temp=0.0)
4. LLM returns `role_domain` + `skills[]` with `is_primary` and `required_level`
5. `_validate_enrichment()` validates against Lightcast L3, bounds levels to 1–4, and derives `main_skills` / `side_skills`

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

**Workflow:** Open career page → DevTools → Network → XHR tab → find JSON request with job titles → Copy as cURL → paste here → Claude saves the route into `KNOWN_PORTALS.md` / `portal_reader.py` / provider registry.

**Explicit priority rule for this phase:** if an endpoint *looks like the correct ATS endpoint*, capture it and move on. **No test is required before promotion.** A later validation pass can prove whether it runs cleanly.

| Company | Career URL | Suspected ATS | Notes |
|---|---|---|---|
| Meta | https://www.metacareers.com/jobs/?locations[0]=India | Custom GraphQL / JSON | Firecrawl can read listing shell; capture GraphQL/XHR route next |
| Vehere Interactive | https://vehere.com/company/careers/ | Custom | Firecrawl surfaced `/positions/...` URLs; direct requests still 403 |
| Mondee Holdings | https://jobs.ashbyhq.com/mondee | Ashby | Board confirmed; posting API slug unresolved / likely empty board |
| Oliver Wyman | https://mmc.phenompeople.com/global/en/oliver-wyman-search | Phenom + downstream detail blocker | Listings exist; full JD route still unresolved |
| Morgan Stanley | https://morganstanley.eightfold.ai/careers?location=INDIA&domain=morganstanley.com | Eightfold / PCSX | Direct API 403; needs browser/XHR clue |
| Micron Technology | https://micron.eightfold.ai/careers?location=India&hl=en | Eightfold / PCSX | Direct API 403 |
| Qualcomm | https://careers.qualcomm.com | Eightfold hosted / custom | Firecrawl usable; direct API/domain still missing |
| HSBC | https://hsbc.eightfold.ai/careers?location=India&hl=en | Eightfold | SPA shell only; needs browser/XHR clue |
| Philip Morris International | https://join.pmicareers.com/search-results | Eightfold hosted | Tenant not identified from direct API |
| Grant Thornton India | https://gtprod.talentrecruit.com/career-page/jobs | TalentRecruit | **Internal SSO-gated ATS** — not a public portal; FC scrape returns login screen; check `grantthornton.in` for separate public career page or mark inaccessible |
| Godrej Consumer Products | https://careers.godrejindustries.com/in/en/search-results?qcountry=India | Phenom SSR | DNS corrected — see KNOWN_PORTALS.md CONSUMER GOODS section; probe PCSX `domain=godrejindustries.com` or Phenom SSR to crack |
| Alvarez & Marsal | https://alvarezandmarsal.wd1.myworkdayjobs.com | Workday | CF-blocked; need browser XHR for India UUID → `workday_registry.json` |
| 🟡 IIFL Finance | iifl.darwinbox.in | Darwinbox | Provider ready — needs CF cookies if/when validation happens |
| 🟡 Flipkart | flipkartcareers.com | Darwinbox | Provider ready — needs CF cookies if/when validation happens |
| 🟡 OYO | oyorooms.com/about/ | Darwinbox | Provider ready — needs CF cookies if/when validation happens |

**Workday CF-blocked** (need India UUID via browser, then add to workday_registry.json):
Engie, GE Aerospace, Bank of America, Ford, Medtronic, Inspire Brands, Hitachi Vantara, Intuit, Societe Generale, Standard Chartered, ANZ Bank, Alvarez & Marsal.

### 2 — Fix broken direct scrapers
- Capture direct detail/JD routes without blocking on runtime:
  - Oliver Wyman full JD source
  - Meta GraphQL payload + params
  - Vehere reusable detail pattern under `/positions/...`
  - Mondee Ashby job-board slug if a non-empty posting API exists
- Fix Workday slugs: Capgemini, MSCI (HCL cracked via Taleo — done)
- Fix SmartRecruiters: Zomato, S&P Global, CRISIL (unconfirmed IDs)

### 3 — New ATS providers still needed
- **Workable**: `GET https://apply.workable.com/api/v3/accounts/{slug}/jobs?state=published`
- **SAP SuccessFactors**: `GET https://{tenant}/odata/v2/JobRequisitionLocale?$filter=...&$format=json` — targets: GMR Group, Deutsche Bank
- **Ashby**: `GET https://api.ashbyhq.com/posting-api/job-board/{slug}` — target: Mondee

### 4 — Architecture (remaining)
- **Firecrawl result cache** — `firecrawl_cache.json` keyed by URL, 7-day TTL. Cache hit → skip re-scrape, save credits.
- **Firecrawl discovery cache** — `map_site()` is now cached too; use it first during endpoint hunting.
- **Provider override consolidation** — if a future route needs special handling, add it through `portal_reader.py` + `scraper/providers/`, not a bespoke script folder.

### 6 — Backfill real `required_level` values into existing `job_skills`

Migration is complete and verified on 2026-05-10. Existing rows currently carry the default `required_level=2`; newly enriched uploads will write model-derived levels. Run a targeted LM Studio backfill only if level accuracy on existing jobs is needed before the next fresh scrape.

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
