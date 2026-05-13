# Supabase Jobs Reverse-Engineering Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Before the next scrape/enrich/upload run, verify the live Supabase contract and the local importer contract so new job data reaches the consumption layer with minimal compute, Firecrawl credits, and LM Studio time.

**Live Snapshot:** Queried through Supabase REST/OpenAPI on 2026-05-09 using `scraper/.env` service credentials. Secrets were not printed or persisted.

---

## Current Table Shape

`jobs` currently has 22 columns:

| Column group | Columns |
|---|---|
| Identity | `job_id`, `job_title`, `job_description`, `company_name` |
| Industry | `industry`, `industry_group` |
| Location | `location`, `location_raw`, `location_city`, `location_country`, `location_mode`, `location_quality` |
| Apply + role | `apply_url`, `role_domain` |
| Legacy skill arrays | `main_skills`, `side_skills` |
| Run/lifecycle | `batch_date`, `first_seen`, `last_seen`, `is_active`, `change_fingerprint`, `report_count` |

Adjacent consumption tables:

| Table | Live count | Notes |
|---|---:|---|
| `jobs` | 27,160 | Primary job feed table |
| `job_skills` | 226,503 | Consumption-layer skill join table |
| `skills` | 35,108 | Lightcast taxonomy |
| `scrape_diagnostics` | 1,123 | Upload/run diagnostics |
| `job_feed_run_audits` | 0 | Present but not receiving current importer rows |
| `job_versions` | 0 | Present but lifecycle versioning is not yet active |

Resolved live drift from repo SQL:

- Live `job_feed_run_audits.run_id` is `uuid`, but `scraper/csv_importer.py` writes string IDs like `upload_YYYYMMDD_HHMMSS`.
- Live `job_feed_run_audits.source` defaults to `job_feed_importer`, while `scraper/sql/create_job_feed_run_audits.sql` documents `firecrawl_csv_importer`.
- `job_skills.required_level` was added in Supabase on 2026-05-10 and verified by `logs/supabase_contract_probe_20260510_033935.md`.
- Decommissioning must be scoped to companies scraped in the current run only. A missing company is never evidence that all of its jobs closed.

## Data Health Signals

Metadata-only scan of all 27,160 jobs:

| Signal | Result |
|---|---:|
| `job_id`, `job_title`, `location`, `batch_date`, `is_active` populated | 100% |
| `job_description` null / empty | 0 null, 381 empty |
| `industry_group` populated | 18,722 / 27,160 |
| `role_domain` populated | 18,562 / 27,160 |
| `location_country` populated | 11,960 / 27,160 |
| `location_quality = unknown` | 7,723 / 27,160 |
| Jobs with any `job_skills` rows | 20,106 / 27,160 |
| Jobs with at least one primary skill | 20,094 / 27,160 |
| `is_active=false` rows | 0 |

The biggest gap cluster is old data:

| Batch | Jobs | No `job_skills` | No `role_domain` | No `location_country` | Unknown location |
|---:|---:|---:|---:|---:|---:|
| 20260419 | 7,152 | 6,705 | 7,152 | 3,568 | 877 |
| 20260417 | 514 | 301 | 514 | 57 | 57 |
| 20260416 | 769 | 38 | 769 | 261 | 258 |

Newer batches mostly flow through skills and role enrichment, but location normalization remains uneven:

| Batch | Jobs | No `job_skills` | No `role_domain` | No `location_country` | Unknown location |
|---:|---:|---:|---:|---:|---:|
| 20260503 | 267 | 0 | 0 | 84 | 84 |
| 20260502 | 2,352 | 2 | 3 | 621 | 621 |
| 20260501 | 214 | 0 | 0 | 29 | 29 |
| 20260430 | 9,352 | 3 | 16 | 7,016 | 3,375 |
| 20260428 | 5,480 | 0 | 39 | 3,193 | 2,051 |

## Lowest-Cost Reverse-Engineering Sequence

## Graphify Corpus Scope

Use a curated corpus rather than the whole repository. The full repo includes historical experiments and generated output folders, which caused a ~6.5M-word detection result.

Recommended graph corpus:

| Include | Why |
|---|---|
| `scraper/providers/` | Every implemented direct provider and Firecrawl fallback provider |
| `scraper/portal_reader.py` | Parses `KNOWN_PORTALS.md`, applies ATS overrides, builds portal dicts |
| `scraper/providers/registry.py` | Dispatch/fallback policy for live runs |
| `scraper/workday_registry.json` | Workday tenant/site/facet UUID overrides |
| `scraper/generic_registry.json` | Generic direct endpoint routing metadata |
| `scraper/schema.py`, `scraper/writer.py`, `scraper/pipeline_validator.py` | Canonical job shape and quality gates |
| `scraper/csv_importer.py`, `scraper/supabase_enricher.py`, `scraper/sql/` | Supabase upload, backfill, and live table contract |
| `KNOWN_PORTALS.md` | Human-maintained source of known company routes |
| `CLAUDE.md`, `CODEX_HANDOFF.md`, `RUN_HISTORY.md` | Current operating notes and historical route decisions |
| `docs/superpowers/plans/` | Current implementation/reverse-engineering plans |
| Latest `logs/portal_inventory_*.md/json` only | Probe evidence for live hiring state, if needed |

This scope covers every live route/API call the current scraper knows how to run because `portal_reader.parse_portals()` currently resolves 173 active portals across 36 ATS/provider types from these files. It will not cover purely historical one-off notebooks under `Market Data_V1_of_Scrapers/` unless we intentionally pull one in as evidence for a recovered provider.

### Task 1: Freeze The Live Contract

- [x] Add a read-only preflight script, `scraper/supabase_contract_probe.py`, that pulls Supabase OpenAPI metadata for `jobs`, `job_skills`, `skills`, `job_reports`, `scrape_diagnostics`, `job_feed_run_audits`, and `job_versions`.
- [x] Save a sanitized JSON/Markdown report under `logs/` with column names, types, required/default flags, counts, and drift against `scraper/schema.py` plus `scraper/sql/*.sql`.
- [x] Make the probe metadata-only by default: no `job_description`, no secrets, no writes.

Latest full probe: `logs/supabase_contract_probe_20260509_225026.md`.
Latest schema-only probe after running the level migration in Supabase: `logs/supabase_contract_probe_20260510_033935.md`.

### Task 2: Fix The Upload-Blocking Drift First

- [x] Choose one correction for `job_feed_run_audits.run_id`: either migrate live column to `text`, or update `csv_importer.py` to use a UUID run ID and store the human string elsewhere.
- [x] Reconcile `source` defaults between live Supabase and `scraper/sql/create_job_feed_run_audits.sql`.
- [x] Add a dry-run assertion that checks audit insert compatibility before uploading real jobs.

Decision: adapt the importer to the live Supabase UUID contract. `csv_importer.py` now generates a UUID `run_id` and keeps the human-readable `upload_YYYYMMDD_HHMMSS` label in logs. A read-only OpenAPI preflight runs before upload/dry-run import work and exits before writes if the audit table contract drifts again.

### Task 3: Prove One Tiny End-To-End Flow

- [x] Pick one stable direct provider company with low row count, for example Stripe or ServiceNow.
- [x] Run scrape only with a tiny cap, no Firecrawl cloud: `python3 main.py --company "ServiceNow" --skip-enrich --company-cap 3`.
- [x] Run enrichment only for that output with LM Studio on.
- [x] Run `python3 csv_importer.py --company "ServiceNow" --dry-run` and compare local rows against the live table contract.
- [x] Only after dry-run passes, upload the same tiny batch and verify `jobs`, `job_skills`, `scrape_diagnostics`, and `job_feed_run_audits`.

Execution note: Stripe returned 0 India jobs in the live direct-provider smoke, so Ring 1 used ServiceNow instead. Command used `SCRAPE_DIAGNOSTICS_DISABLED=1` to keep the scrape smoke local. ServiceNow scraped 3 jobs, LM Studio enrichment completed 3/3, importer dry-run passed the Supabase audit preflight, and location quality was 0 unknown rows. Dry-run resolved 34 `job_skills` rows.

Upload verification run: `ecd6ac88-a7e3-4fd9-baff-65dfa3f15648`. Verified 3 `jobs` rows, 34 `job_skills` rows, 1 `scrape_diagnostics` row, and 1 `job_feed_run_audits` row. Audit status was `ok`, with 0 unknown locations.

### Task 4: Backfill Existing Data Before Spending On New Scrapes

- [x] Add the `required_level` DB migration as `scraper/sql/add_job_skills_required_level.sql`.
- [x] Make real uploads/backfills stop before writes until live Supabase exposes `job_skills.required_level`.
- [x] Update LM Studio enrichment to emit structured `skills[]` with `required_level`.
- [ ] After running the migration, use `scraper/supabase_enricher.py --dry-run` to count rows with descriptions but missing `job_skills`.
- [ ] Prioritize 20260419, 20260417, and 20260416 rows because they account for most missing role/skill enrichment.
- [ ] Do not use Firecrawl for JD backfill unless `job_description` is missing and the company is high value.

### Task 5: Add A Consumption-Layer Quality Gate

- [x] Gate real uploads on the `job_feed_run_audits` contract and the new `job_skills.required_level` contract.
- [x] Keep `main_skills` and `side_skills` arrays as backward-compatible columns while writing structured skill rows.
- [x] Add upload audit blocking when `location_quality=unknown` exceeds the configured threshold.
- [ ] Add a stricter per-job readiness report for `apply_url`, `industry_group`, `role_domain`, `location_country`, and at least one `job_skills` row.
- [ ] Treat `location_country` and `location_quality` as the highest-priority filter risk for True_Yodha matching.

### Task 5A: Scoped Decommissioning

- [x] Add `csv_importer.py --deactivate-missing` to mark active jobs inactive only for companies represented by one run date.
- [x] Add `--run-date` scoping; real deactivation writes require it, while dry-run can default to the newest dated output folder.
- [x] Keep decommissioning opt-in and skip it when the upload quality gate blocks.
- [x] Add a large-drop guard: per-company deactivation above 75% is blocked unless `--allow-large-deactivation` is explicitly passed.
- [ ] Use decommissioning only after a full non-capped scrape, never after Ring 1 smoke data.

### Task 6: Scale The Next Run In Rings

- [ ] Ring 0: metadata probe only.
- [ ] Ring 1: one company, 3 jobs, direct provider only.
- [ ] Ring 2: three stable direct providers, cap 25 each.
- [ ] Ring 3: all direct providers with `--skip-enrich`, then enrichment only for saved jobs.
- [ ] Ring 4: JS-heavy/Firecrawl fallbacks only after direct providers and DB flow are proven.

## Recommended Immediate Decision

Do not start a full scrape yet. First fix or adapt the `job_feed_run_audits.run_id` mismatch, then run a tiny direct-provider end-to-end smoke. That gives the best probability of catching table-contract failures before spending LM Studio time or Firecrawl credits.
