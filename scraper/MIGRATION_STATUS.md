# Migration Status - Architecture V3

Use this file as the single handoff status board for Codex/Claude.

## Current Snapshot
- Date: 2026-04-27
- Branch: `main`
- Last completed phase: `Phase 1 - Provider Interface + Registry Skeleton`
- Current in-progress phase: `Phase 2 - Workday Provider Migration`
- Next command to run: `python scraper/main.py --company "Salesforce" --skip-enrich`

## Phase Checklist
- [x] Phase 0 - Baseline Freeze
- [x] Phase 1 - Provider Interface + Registry Skeleton
- [ ] Phase 2 - Workday Provider Migration
- [ ] Phase 3 - Remaining Provider Migrations
- [ ] Phase 4 - Shared Schema/Normalization Module
- [ ] Phase 5 - Deterministic Validation Layer
- [ ] Phase 6 - Observability + Diagnostics Hardening
- [ ] Phase 7 - Final Verification and Go-Live Run

## Latest Handoff
- Phase completed: `Phase 1 - Provider Interface + Registry Skeleton`
- Files changed:
  - `scraper/providers/base.py`
  - `scraper/providers/registry.py`
  - `scraper/providers/workday.py`
  - `scraper/providers/smartrecruiters.py`
  - `scraper/providers/greenhouse.py`
  - `scraper/providers/lever.py`
  - `scraper/providers/phenom.py`
  - `scraper/providers/generic_json.py`
  - `scraper/providers/firecrawl_js.py`
  - `scraper/providers/__init__.py`
  - `scraper/main.py`
  - `scraper/MIGRATION_STATUS.md`
- Behavior changes:
  - `main.py` ATS branching moved to provider registry dispatch
  - Fallback policy centralized in `providers/registry.py` (Workday + Oracle + generic-get HTML fallback)
- Verification commands run:
  - `python scraper/main.py --dry-run` (pass)
  - `python scraper/main.py --validate --skip-enrich` (pass; `run_summary_20260427_213806.json`)
- Known issues remaining:
  - `test_pipeline.py` baseline still has 5 known failing checks (captured in `MIGRATION_BASELINE.md`)
  - Known low-count/0-result portals remain unchanged from baseline
- Next immediate phase/task: Phase 2 — move Workday internals from `scrapers.py` into `providers/workday.py` and keep fallback parity

## Verification Log
- `2026-04-27 20:56` - `cd scraper && python main.py --dry-run` - pass (`159` portals listed)
- `2026-04-27 20:56` - `cd scraper && python main.py --validate --skip-enrich` - pass with warnings (`run_summary_20260427_211642.json`)
- `2026-04-27 21:16` - `cd scraper && python test_pipeline.py` - fail (`5` checks; baseline-captured)
- `2026-04-27 21:18` - `python scraper/main.py --dry-run` - pass (`159` portals listed, provider registry path)
- `2026-04-27 21:18` - `python scraper/main.py --validate --skip-enrich` - pass (`run_summary_20260427_213806.json`)

## Blockers
- None
