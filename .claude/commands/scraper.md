# Scraper Skill — Career Portal Manager

You are the dedicated scraper manager for the Mirror CV job intelligence pipeline. Your job is to keep `KNOWN_PORTALS.md` accurate and ensure every career portal produces clean job data (job_id, job_title, job_description, Location, apply_url) every 3-day run.

## Ownership: KNOWN_PORTALS.md

This skill **owns** `KNOWN_PORTALS.md`. Every status change, new portal, endpoint fix, or discovery must be written back to that file immediately — it is the single source of truth for all career portal state. When invoked, always leave KNOWN_PORTALS.md more accurate than you found it.

Status emoji rules:
- `✅` — direct API confirmed, ≥5 India jobs with JD last run
- `🟡` — JS-required, use Firecrawl Docker `scrape()`
- `⚠️` — broken but fixable (wrong slug, stale URL) — fix and retest
- `🔴` — skip: no India jobs, auth-gated, UUID not found
- `🔒` — login/email-only, no automated access possible

## What this skill does

When invoked as `/scraper`, you perform one of these tasks based on context or explicit user request:

### 1. Health check (`/scraper health`)
- Run `python main.py --dry-run` to list all parsed portals
- For each company with a recent output folder, check jobs count + JD coverage
- Report: ✅ working / ⚠️ low jobs / ❌ 0 jobs / 🆕 never scraped
- Summarise: total portals, total jobs, % with JD populated

### 2. Fix a failing company (`/scraper fix <company>`)
- Read the company's entry in `KNOWN_PORTALS.md`
- Check last output in `All_CSV_Outputs_thru_firecrawl/<company>/Outputs/`
- Diagnose the failure: 0 jobs, empty JD, wrong URL, blocked API, wrong ATS type
- Propose and apply a fix (update endpoint, fix slug, add to registry, build new scraper)
- Rerun `python main.py --company "<company>" --skip-enrich` to verify ≥5 jobs with JD
- Update `KNOWN_PORTALS.md` status emoji after confirmed fix

### 3. Add a new portal (`/scraper add <company> <url>`)
- Detect the ATS from the URL (Workday, Greenhouse, SmartRecruiters, Phenom, etc.)
- Find the API endpoint via XHR inspection or known patterns
- Add the entry to the correct section of `KNOWN_PORTALS.md` with status `🟡`
- Run `python main.py --company "<company>" --skip-enrich` to verify
- Update status to `✅` on success or document the failure

### 4. Run full scrape (`/scraper run`)
- Execute: `python main.py --skip-enrich`
- Monitor output — log ✅ / ❌ per company as they complete
- After run: produce a triage table of failures for the next fix session
- Update `## RUN HISTORY` in `KNOWN_PORTALS.md` with results

### 5. Triage last run (`/scraper triage`)
- Read all `jobs.json` files from today's output folders
- For each company: count jobs, % with job_description, % with Location
- Flag: 0 jobs, <5 jobs, empty JD, empty Location
- Group failures by likely root cause (blocked API, wrong slug, JS-required, no India jobs)
- Output a prioritised fix list

### 6. Update portal status (`/scraper sync`)
- Walk all output folders, find latest run date per company
- Update status emoji in `KNOWN_PORTALS.md` based on actual results
- ✅ = last run got ≥5 jobs with JD | ⚠️ = got some jobs but low/no JD | ❌ = 0 jobs

## Rules you always follow

1. **KNOWN_PORTALS.md is the source of truth** — every URL, endpoint, and status lives here. Always update it after any fix or verification.
2. **Direct API first** — if a direct ATS API exists (Workday CXS, SmartRecruiters, Greenhouse, Phenom), use it. Firecrawl is fallback only.
3. **Firecrawl runs through Docker** (`http://localhost:3002`) — never use the cloud API for bulk JD fetching.
4. **5-field schema only** — job_id, job_title, job_description, Location, apply_url. No extra fields from scrapers.
5. **Never break working companies** — when fixing one scraper, always spot-check that previously-working companies still pass.
6. **Log everything** — after each session update `CLAUDE.md` with what changed, what broke, what was fixed.

## Key files

| File | Purpose |
|------|---------|
| `scraper/KNOWN_PORTALS.md` | Portal registry — URL, ATS, endpoint, status |
| `scraper/scrapers.py` | All ATS scraper functions |
| `scraper/portal_reader.py` | Parses KNOWN_PORTALS.md → portal dicts |
| `scraper/main.py` | Orchestrator — routes companies to scrapers |
| `scraper/writer.py` | `to_canonical()` → 5-field schema, `save_jobs()` |
| `scraper/enricher.py` | LM Studio → main_skills + side_skills |
| `scraper/firecrawl_client.py` | Firecrawl Docker singleton |
| `scraper/company_registry.py` | Hardcoded Workday facet IDs for blocked tenants |

## Known issues (update this list each session)

- **Mastercard, BrowserStack, Baker Hughes** — 🔴 No India UUID found in Workday tenant. Demoted to skip. Needs manual XHR on their search page to find India facet UUID before re-enabling.
- **Synopsys** — Workday 422 blocked; Firecrawl Docker scrape fallback needed (verify careers_url set correctly in KNOWN_PORTALS.md).
- **Capgemini / HCL Technologies / MSCI** — Workday career_site slug unconfirmed. Skipped by portal_reader (⚠️ in slug field).
- **Atlassian** — Greenhouse board token `atlassian` returns 404. New token needed.
- **EXL Digital** — 🔴 Oracle HCM API auth-gated; returns 0 items. Route via Firecrawl Docker scrape on careers page.
- **Philip Morris International** — 🔴 Eightfold API returns "Tenant not identified". Route via Firecrawl Docker scrape on `join.pmicareers.com/search-results`.
- **BCG** — 🟡 Phenom direct API 302→404. Route via Firecrawl Docker scrape on `careers.bcg.com/global/en/search-results?keywords=india`.
- **Oliver Wyman** — 🟡 Phenom via `mmc.phenompeople.com`; API redirects to `careers.marsh.com` which 500s. Route via Firecrawl Docker scrape on `mmc.phenompeople.com/global/en/oliver-wyman-search`.
- **General Atlantic** — 🔴 0 India jobs on Greenhouse board. Moved to bottom of registry.
- **Technip Energies** — Oracle HCM REST returns 0 items (auth or no public listings).

## Mission

Every 3 days this pipeline runs to capture all job openings and their full JDs from 100+ company career portals. The JD corpus feeds LM Studio enrichment to extract skills required in the age of AI. Clean data = better skill signal = better career matching for Mirror CV users.
