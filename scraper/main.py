"""
Mirror Job Scraper — Weekly Orchestrator
========================================
Reads KNOWN_PORTALS.md, routes active portals through providers, enriches via
LM Studio (main_skills + side_skills), and writes canonical JSON/CSV output.

Firecrawl credit rules:
  - crawl() is NEVER called — too expensive (N credits per company)
  - scrape_extract() (fc.extract) is used ONLY for js_required portals (1 call)
  - scrape() is only called inside individual scrapers for JD fetch, not here

Usage:
    python main.py                      # all active portals
    python main.py --company "Stripe"   # single company (substring match)
    python main.py --ats workday        # one ATS type only
    python main.py --dry-run            # parse portals only, no scraping
    python main.py --skip-enrich        # scrape only, skip LLM enrichment
    python main.py --resume             # skip companies already scraped
    python main.py --enrich-only        # enrich saved jobs (LM Studio on)
"""
import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor, as_completed
from portal_reader import parse_portals
from providers import dispatch_scrape
from enricher import enrich_job
from writer import to_canonical, save_jobs, SCHEMA, COMPLETE_MARKER_NAME, write_complete_marker
from run_checkpoint import RunCheckpoint
from typing import Callable
from utils import company_slug
from config import OUTPUT_BASE
from validation import LOW_COUNT_THRESHOLD
from pipeline_validator import run_gate

_VALIDATE_OUTPUT_BASE = str(Path(OUTPUT_BASE).parent / "validation_outputs")
_VALIDATE_MAX_JOBS    = 5
_GLOBAL_SCOPE_DEFAULT_CAP = 2000
_DEFAULT_COMPANY_CAP = 1000

_INTER_COMPANY_DELAY = 2   # seconds between companies


def already_scraped(company: str) -> bool:
    """Return True if this company has a *complete* scrape.

    Priority:
      1. jobs.complete marker present in any date folder (new system).
      2. Legacy: jobs.json exists in a past date folder and no marker
         (pre-marker era runs — assume complete if not today).
    A partial jobs.json in today's folder without a marker = incomplete.
    """
    outputs_dir = Path(OUTPUT_BASE) / company_slug(company) / "Outputs"
    if not outputs_dir.exists():
        return False

    today = datetime.now().strftime("%Y_%m_%d")

    for date_dir in outputs_dir.iterdir():
        if not date_dir.is_dir():
            continue
        if (date_dir / COMPLETE_MARKER_NAME).exists():
            return True
        # Legacy fallback: past date folder with jobs.json but no marker
        if date_dir.name < today and (date_dir / "jobs.json").exists():
            return True

    return False


# ── Logging setup ─────────────────────────────────────────────────────────────

def setup_logging(log_dir: str = "../logs") -> logging.Logger:
    log_path = Path(log_dir) / f"run_{datetime.now().strftime('%Y_%m_%d_%H%M%S_%f')}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s  %(levelname)-7s  %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
    log = logging.getLogger("mirror")
    log.info(f"Log file: {log_path.resolve()}")
    return log


# ── Dispatch ──────────────────────────────────────────────────────────────────

def scrape_portal(portal: dict, log: logging.Logger, max_jobs: int | None = None,
                  validate_mode: bool = False, on_page_complete=None) -> list[dict]:
    return dispatch_scrape(
        portal,
        log,
        max_jobs=max_jobs,
        validate_mode=validate_mode,
        on_page_complete=on_page_complete,
    )


# ── Page-flush callback ───────────────────────────────────────────────────────

def _make_page_callback(
    company: str,
    output_base: str,
    checkpoint: RunCheckpoint | None,
    log: logging.Logger,
) -> Callable[[list[dict], int], None]:
    """Return a callback that normalises + saves a raw page chunk to disk.

    Called by Workday/Taleo after each page's JDs are fetched.
    Writes jobs.complete=False (write_marker=False) so already_scraped() correctly
    sees the run as incomplete until the final save_jobs() stamps the marker.
    """
    pages_flushed = [0]

    def on_page_complete(raw_page_jobs: list[dict], page: int) -> None:
        if not raw_page_jobs:
            return
        canonical_chunk = [to_canonical(j, company) for j in raw_page_jobs]
        canonical_chunk = [j for j in canonical_chunk if j.get("job_id")]
        if not canonical_chunk:
            return
        try:
            _, new_count = save_jobs(company, canonical_chunk,
                                     output_base=output_base, write_marker=False)
            pages_flushed[0] += 1
            total_so_far = pages_flushed[0] * len(canonical_chunk)
            if checkpoint:
                checkpoint.update_progress(company, page=page, jobs_so_far=total_so_far)
            if new_count:
                log.debug(f"  [PAGE {page}] flushed {new_count} new jobs ({company})")
        except Exception as e:
            log.warning(f"  [PAGE FLUSH] error at page {page} for {company}: {e}")

    return on_page_complete


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run(portals: list[dict], skip_enrich: bool, log: logging.Logger,
        max_jobs: int | None = None, output_base: str = OUTPUT_BASE,
        validate_mode: bool = False, scope: str = "india",
        checkpoint: RunCheckpoint | None = None) -> dict:
    summary = {
        "scope": scope,
        "run_id": checkpoint.run_id if checkpoint else datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        "processed": 0, "skipped": 0, "total_new": 0,
        "total_validation_drops": 0,
        "unresolved": [],
        "low_count": [],
        "company_stats": [],
        "errors": [], "start": datetime.now().isoformat(),
    }
    total = len(portals)

    for idx, portal in enumerate(portals, 1):
        company = portal["company"]
        ats     = portal["ats"]
        js_flag = "  [JS/Firecrawl extract]" if portal.get("js_required") else ""
        log.info(f"[{idx}/{total}] {company}  ({ats}){js_flag}")

        if checkpoint:
            checkpoint.start(company, ats)

        # ── Scrape ────────────────────────────────────────────────────────────
        page_cb = _make_page_callback(company, output_base, checkpoint, log)
        try:
            raw_jobs = scrape_portal(portal, log, max_jobs=max_jobs, validate_mode=validate_mode,
                                     on_page_complete=page_cb)
        except Exception as e:
            log.error(f"  FATAL scrape error — {company}: {e}")
            if checkpoint:
                checkpoint.mark_failed(company, reason=f"scrape_exception: {e}")
            summary["errors"].append({"company": company, "stage": "scrape", "error": str(e)})
            summary["unresolved"].append({
                "company": company,
                "ats": ats,
                "scope": scope,
                "reason": "scrape_exception",
                "details": str(e),
            })
            summary["skipped"] += 1
            continue

        if not raw_jobs:
            log.info(f"  0 {scope} jobs — skipping")
            if checkpoint:
                checkpoint.mark_failed(company, reason="no_jobs_returned")
            summary["unresolved"].append({
                "company": company,
                "ats": ats,
                "scope": scope,
                "reason": "no_jobs_returned",
                "details": "scraper returned empty result set",
            })
            summary["company_stats"].append({
                "company": company,
                "ats": ats,
                "raw_jobs": 0,
                "saved_new": 0,
                "status": "no_jobs",
            })
            summary["skipped"] += 1
            continue

        # Safety truncation for validate mode (scrapers cap internally where efficient,
        # this catches anything that slipped through — e.g. Greenhouse, Phenom)
        if max_jobs:
            raw_jobs = raw_jobs[:max_jobs]

        log.info(f"  {len(raw_jobs)} raw jobs scraped")

        # ── Normalise to 7-field schema ───────────────────────────────────────
        canonical = [to_canonical(j, company) for j in raw_jobs]

        # ── Gate 1: post_scrape — identity + placeholder ──────────────────────
        g1 = run_gate(canonical, "post_scrape")
        if g1.drop_count:
            log.warning(f"  {g1.drop_count} jobs dropped [post_scrape] — {g1.reasons}")
        summary["total_validation_drops"] += g1.drop_count

        # ── Gate 2: pre_enrich — description present + min length ─────────────
        g2 = run_gate(g1.passed, "pre_enrich")
        if g2.drop_count:
            log.warning(f"  {g2.drop_count} jobs dropped [pre_enrich] — {g2.reasons}")
        summary["total_validation_drops"] += g2.drop_count

        canonical = g2.passed

        # ── Enrich (main_skills + side_skills from job_description) ──────────
        if skip_enrich:
            enriched = canonical
            log.info(f"  LLM enrichment skipped (--skip-enrich)")
        else:
            enriched = []
            ok = fail = 0
            for job in canonical:
                try:
                    enriched.append(enrich_job(job))
                    ok += 1
                except Exception as e:
                    log.warning(f"  enrich failed for '{job.get('job_title')}': {e}")
                    enriched.append(job)
                    fail += 1
            log.info(f"  LLM enrichment: {ok} ok  {fail} failed")

        # ── Save ──────────────────────────────────────────────────────────────
        _run_id = checkpoint.run_id if checkpoint else ""
        try:
            path, new_count = save_jobs(company, enriched, output_base=output_base, run_id=_run_id)
            log.info(f"  Saved {new_count} new jobs → {path}")
            if checkpoint:
                checkpoint.mark_complete(company, job_count=len(enriched))
            if len(raw_jobs) < LOW_COUNT_THRESHOLD:
                log.warning(f"  LOW COUNT: {len(raw_jobs)} scraped job(s) for {company}")
                summary["low_count"].append({
                    "company": company,
                    "ats": ats,
                    "raw_jobs": len(raw_jobs),
                    "saved_new": new_count,
                    "reason": "below_5_scraped_jobs",
                })
            summary["company_stats"].append({
                "company": company,
                "ats": ats,
                "raw_jobs": len(raw_jobs),
                "validation_drops": g1.drop_count + g2.drop_count,
                "saved_new": new_count,
                "status": "ok",
            })
            summary["processed"] += 1
            summary["total_new"] += new_count
        except Exception as e:
            log.error(f"  FATAL save error — {company}: {e}")
            if checkpoint:
                checkpoint.mark_failed(company, reason=f"save_exception: {e}")
            summary["unresolved"].append({
                "company": company,
                "ats": ats,
                "scope": scope,
                "reason": "save_exception",
                "details": str(e),
            })
            summary["company_stats"].append({
                "company": company,
                "ats": ats,
                "raw_jobs": len(raw_jobs),
                "saved_new": 0,
                "status": "save_error",
                "error": str(e),
            })
            summary["errors"].append({"company": company, "stage": "save", "error": str(e)})

        time.sleep(_INTER_COMPANY_DELAY)

    summary["end"] = datetime.now().isoformat()
    return summary


def _persist_diagnostics_to_supabase(summary: dict, log: logging.Logger) -> None:
    """
    Best-effort write of run diagnostics to Supabase.
    If table/env is missing, this no-ops with a warning (does not fail the run).
    """
    table = os.getenv("SCRAPE_DIAGNOSTICS_TABLE", "scrape_diagnostics")
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not supabase_key:
        log.info("  Diagnostics table skipped: SUPABASE_URL/SUPABASE_SERVICE_KEY not set")
        return

    try:
        from supabase import create_client
    except Exception as e:
        log.warning(f"  Diagnostics table skipped: could not import supabase client ({e})")
        return

    unresolved_map = {u.get("company"): u for u in summary.get("unresolved", [])}
    rows = []
    for stat in summary.get("company_stats", []):
        company = stat.get("company")
        unresolved = unresolved_map.get(company, {})
        rows.append({
            "run_id": summary.get("run_id"),
            "scope": summary.get("scope"),
            "started_at": summary.get("start"),
            "ended_at": summary.get("end"),
            "company_name": company,
            "ats": stat.get("ats"),
            "raw_jobs": stat.get("raw_jobs", 0),
            "saved_new": stat.get("saved_new", 0),
            "status": stat.get("status", "unknown"),
            "reason": unresolved.get("reason"),
            "details": unresolved.get("details"),
        })

    if not rows:
        return

    try:
        sb = create_client(supabase_url, supabase_key)
        batch_size = 200
        for i in range(0, len(rows), batch_size):
            sb.table(table).insert(rows[i:i + batch_size]).execute()
        log.info(f"  Diagnostics table rows : {len(rows)} inserted into `{table}`")
    except Exception as e:
        log.warning(f"  Diagnostics table write failed (`{table}`): {e}")


# ── Enrich-only pass ──────────────────────────────────────────────────────────

def _needs_enrichment(job: dict) -> bool:
    """True if the job has job_description but no skills enrichment yet."""
    has_jd     = bool((job.get('job_description') or '').strip())
    has_skills = bool(job.get('main_skills'))
    return has_jd and not has_skills


def enrich_only_run(log: logging.Logger) -> None:
    """
    Walk All_CSV_Outputs/*/Outputs/*/jobs.json — enrich unenriched jobs in-place.
    LM Studio must be running. No Firecrawl calls are made.
    """
    base = Path(OUTPUT_BASE)
    json_files = sorted(base.rglob("jobs.json"))
    log.info(f"Enrich-only mode: found {len(json_files)} jobs.json file(s)")

    total_enriched = total_failed = 0

    for json_path in json_files:
        try:
            jobs = json.loads(json_path.read_text(encoding='utf-8'))
        except Exception as e:
            log.warning(f"  Could not read {json_path}: {e}")
            continue

        to_enrich = [j for j in jobs if _needs_enrichment(j)]
        if not to_enrich:
            log.info(f"  {json_path.parent.parent.parent.name}: all jobs already enriched — skipping")
            continue

        company = jobs[0].get('company_name', json_path.parent.parent.parent.name) if jobs else '?'
        log.info(f"  {company}: enriching {len(to_enrich)}/{len(jobs)} jobs")

        ok = fail = 0
        _workers = int(os.getenv("ENRICH_WORKERS", "4"))
        with ThreadPoolExecutor(max_workers=_workers) as pool:
            futures = {
                pool.submit(enrich_job, job): job
                for job in jobs if _needs_enrichment(job)
            }
            for fut in as_completed(futures):
                try:
                    fut.result()
                    ok += 1
                except Exception as e:
                    log.warning(f"    enrich failed for '{futures[fut].get('job_title')}': {e}")
                    fail += 1

        log.info(f"    {ok} ok  {fail} failed")
        total_enriched += ok
        total_failed   += fail

        # Write back JSON (atomic: tmp → rename)
        tmp_path = json_path.with_name("jobs.tmp.json")
        tmp_path.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding='utf-8')
        tmp_path.rename(json_path)

        # Rewrite CSV
        csv_path = json_path.with_name("jobs.csv")
        with csv_path.open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=SCHEMA, extrasaction='ignore')
            w.writeheader()
            for job in jobs:
                row = dict(job)
                row['main_skills'] = ', '.join(job.get('main_skills') or [])
                row['side_skills'] = ', '.join(job.get('side_skills') or [])
                w.writerow(row)

        # Marker after both JSON and CSV succeed
        write_complete_marker(json_path.parent, len(jobs), ok)

    log.info(f"Enrich-only complete — {total_enriched} enriched, {total_failed} failed")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Mirror Job Scraper (v2)")
    parser.add_argument("--company",               help="Filter by company name (substring, case-insensitive)")
    parser.add_argument("--ats",                   help="Filter by ATS type (workday, smartrecruiters, …)")
    parser.add_argument("--dry-run",               action="store_true", help="List portals only, no scraping")
    parser.add_argument("--skip-enrich",           action="store_true", help="Skip LLM enrichment, save raw scraped data")
    parser.add_argument("--resume",                action="store_true", help="Skip companies that already have output in All_CSV_Outputs")
    parser.add_argument("--enrich-only",           action="store_true", help="Enrich already-scraped jobs (no scraping, LM Studio only)")
    parser.add_argument("--scope", choices=["india", "global"], default="india",
                        help="Job geography scope (default: india).")
    parser.add_argument("--company-cap", type=int, default=_DEFAULT_COMPANY_CAP,
                        help=f"Max jobs per company for all runs (default: {_DEFAULT_COMPANY_CAP}). Set 0 for no cap.")
    parser.add_argument("--global-cap", type=int, default=None,
                        help=f"Alias for --company-cap (kept for backward compat).")
    parser.add_argument("--resume-run", metavar="RUN_ID",
                        help="Resume a specific interrupted run by its run_id "
                             "(e.g. 20260430_141922). Skips companies marked complete in that run.")
    parser.add_argument("--validate",              action="store_true",
                        help=f"Validation run: scrape {_VALIDATE_MAX_JOBS} jobs/company, no enrichment, "
                             f"write to validation_outputs/ — use to verify column coverage across all portals")
    args = parser.parse_args()

    log = setup_logging()

    if args.enrich_only:
        enrich_only_run(log)
        return

    # --validate: cap to 5 jobs/company, no enrichment, separate output folder
    # --company-cap: per-company limit applied on all runs (default 1000); 0 = unlimited
    validate_mode = args.validate
    if validate_mode:
        max_jobs = _VALIDATE_MAX_JOBS
    else:
        # --global-cap is a backward-compat alias; explicit --company-cap wins
        raw_cap = args.global_cap if args.global_cap is not None else args.company_cap
        max_jobs = raw_cap if raw_cap else None
    output_base = _VALIDATE_OUTPUT_BASE if validate_mode else OUTPUT_BASE
    if validate_mode:
        log.info(f"VALIDATE MODE: max {_VALIDATE_MAX_JOBS} jobs/company → {output_base}")
    elif max_jobs:
        log.info(f"Cap: {max_jobs} jobs/company")

    portals = parse_portals()
    if args.company:
        portals = [p for p in portals if args.company.lower() in p["company"].lower()]
    if args.ats:
        portals = [p for p in portals if p["ats"] == args.ats.lower()]
    # ── Determine resume checkpoint (--resume-run or auto-detect via --resume) ──
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    resume_checkpoint: RunCheckpoint | None = None

    if args.resume_run:
        resume_checkpoint = RunCheckpoint.load(args.resume_run, log_dir)
        if not resume_checkpoint:
            log.warning(f"--resume-run: checkpoint {args.resume_run} not found — running fresh")
    elif args.resume:
        resume_checkpoint = RunCheckpoint.load_latest_partial(log_dir)
        if resume_checkpoint:
            log.info(f"--resume: auto-detected partial run {resume_checkpoint.run_id}")

    # ── Filter already-done companies ─────────────────────────────────────────
    if resume_checkpoint:
        before = len(portals)
        portals = [p for p in portals if not resume_checkpoint.is_complete(p["company"])]
        label = f"--resume-run {resume_checkpoint.run_id}" if args.resume_run else "--resume (checkpoint)"
        log.info(f"{label}: skipping {before - len(portals)} complete, {len(portals)} remaining")
    elif args.resume:
        # No checkpoint found — fall back to file-date comparison
        before = len(portals)
        portals = [p for p in portals if not already_scraped(p["company"])]
        log.info(f"--resume (file-date): skipping {before - len(portals)} already-scraped, {len(portals)} remaining")

    # Scope override:
    # india  -> force India filtering across adapters
    # global -> disable India filtering where adapter supports it
    for p in portals:
        p["india_only"] = (args.scope == "india")

    log.info(f"Scope: {args.scope}")
    log.info(f"Portals to process: {len(portals)}")
    for p in portals:
        flag = "🌐" if p["js_required"] else "⚡"
        log.info(f"  {flag}  {p['company']:<30} [{p['ats']}]")

    if args.dry_run:
        return

    # Create checkpoint for this run (always — not only on --resume)
    run_id  = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    checkpoint = resume_checkpoint or RunCheckpoint.new(run_id, log_dir)
    if resume_checkpoint:
        log.info(f"Resuming run_id={checkpoint.run_id}")
    else:
        log.info(f"Checkpoint: logs/checkpoint_{run_id}.json")

    log.info("─" * 60)
    summary = run(portals, skip_enrich=args.skip_enrich or validate_mode, log=log,
                  max_jobs=max_jobs, output_base=output_base,
                  validate_mode=validate_mode, scope=args.scope,
                  checkpoint=checkpoint)

    log.info("─" * 60)
    log.info(f"RUN COMPLETE")
    log.info(f"  Run ID              : {checkpoint.run_id}")
    log.info(f"  Companies processed : {summary['processed']}")
    log.info(f"  Companies skipped   : {summary['skipped']}")
    log.info(f"  Total new jobs      : {summary['total_new']}")
    log.info(f"  Started             : {summary['start']}")
    log.info(f"  Ended               : {summary['end']}")
    cp_summary = checkpoint.summary()
    log.info(f"  Checkpoint states   : complete={cp_summary['complete']} "
             f"failed={cp_summary['failed']} partial={cp_summary['in_progress']}")

    if summary["errors"]:
        log.warning(f"  Errors ({len(summary['errors'])}):")
        for e in summary["errors"]:
            log.warning(f"    [{e['stage']}] {e['company']}: {e['error']}")

    if summary["low_count"]:
        log.warning(f"  Low-count companies (<5 scraped jobs): {len(summary['low_count'])}")
        for row in summary["low_count"]:
            log.warning(f"    {row['company']} [{row['ats']}]: scraped={row['raw_jobs']} saved_new={row['saved_new']}")

    reports_dir = Path(__file__).resolve().parent.parent / "logs"
    reports_dir.mkdir(parents=True, exist_ok=True)
    summary_path = reports_dir / f"run_summary_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log.info(f"  Run summary JSON    : {summary_path}")
    _persist_diagnostics_to_supabase(summary, log)


if __name__ == "__main__":
    main()
