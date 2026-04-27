"""
Mirror Job Scraper — Weekly Orchestrator (v2, Dump 4+)
=======================================================
Reads KNOWN_PORTALS.md, scrapes each active portal (5 raw fields),
enriches via LM Studio (main_skills + side_skills), writes 7-field JSON
to All_CSV_Outputs/.

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
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor, as_completed
from portal_reader import parse_portals
from scrapers import scrape_workday, scrape_smartrecruiters, scrape_greenhouse, scrape_lever, scrape_get, scrape_extract, scrape_validate, scrape_phenom_api
from enricher import enrich_job
from writer import to_canonical, save_jobs, SCHEMA
from utils import company_slug
from config import OUTPUT_BASE

_VALIDATE_OUTPUT_BASE = str(Path(OUTPUT_BASE).parent / "validation_outputs")
_VALIDATE_MAX_JOBS    = 5

_INTER_COMPANY_DELAY = 2   # seconds between companies


def already_scraped(company: str) -> bool:
    """Return True if this company has any jobs.json in All_CSV_Outputs."""
    outputs_dir = Path(OUTPUT_BASE) / company_slug(company) / "Outputs"
    if not outputs_dir.exists():
        return False
    return any(p.name == "jobs.json" for p in outputs_dir.rglob("jobs.json"))


# ── Logging setup ─────────────────────────────────────────────────────────────

def setup_logging(log_dir: str = "../logs") -> logging.Logger:
    log_path = Path(log_dir) / f"run_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.log"
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
                  validate_mode: bool = False) -> list[dict]:
    ats = portal["ats"]

    if portal.get("js_required"):
        return _scrape_firecrawl_extract(portal, log, max_jobs=max_jobs, validate_mode=validate_mode)

    if ats == "phenom_api":
        return scrape_phenom_api(portal)

    if ats == "workday":
        jobs = scrape_workday(portal, max_jobs=max_jobs)
        if jobs is None:
            log.info(f"    Workday direct API blocked → falling back to Firecrawl")
            fc_portal = dict(portal)
            if portal.get("careers_url"):
                fc_portal["endpoint"] = portal["careers_url"]
            return _scrape_firecrawl_extract(fc_portal, log, max_jobs=max_jobs, validate_mode=validate_mode)
        return jobs

    if ats == "smartrecruiters":
        return scrape_smartrecruiters(portal, max_jobs=max_jobs)

    if ats == "greenhouse":
        return scrape_greenhouse(portal)

    if ats == "lever":
        return scrape_lever(portal)

    # custom / sap / oracle / other — direct GET, fallback to Firecrawl on HTML
    raw = scrape_get(portal)
    if raw and raw[0].get("_needs_firecrawl"):
        return _scrape_firecrawl_extract(portal, log, max_jobs=max_jobs, validate_mode=validate_mode)
    # Oracle HCM REST APIs are auth-gated — return 0 jobs; fall back to Firecrawl
    if not raw and ats == "oracle" and portal.get("careers_url"):
        log.info(f"    Oracle REST returned 0 → falling back to Firecrawl on careers_url")
        fc_portal = {**portal, "endpoint": portal["careers_url"]}
        return _scrape_firecrawl_extract(fc_portal, log, max_jobs=max_jobs, validate_mode=validate_mode)
    return raw


def _scrape_firecrawl_extract(portal: dict, log: logging.Logger,
                               max_jobs: int | None = None, validate_mode: bool = False) -> list[dict]:
    company = portal["company"]
    if validate_mode:
        # No LLM needed: Playwright scrape + markdown parse
        jobs = scrape_validate(portal, max_jobs=max_jobs or 5)
    else:
        jobs = scrape_extract(portal, max_jobs=max_jobs)
    if jobs:
        log.info(f"    Firecrawl {'scrape' if validate_mode else 'extract'}: {len(jobs)} entries")
    else:
        log.warning(f"    Firecrawl returned 0 for {company}")
    return jobs


# ── Company scrapers (bespoke HTTP scripts) ───────────────────────────────────

def run_company_scrapers(log: logging.Logger) -> set[str]:
    """Run all run_*.py scripts in company_scrapers/. Returns set of company slugs scraped."""
    scrapers_dir = Path(__file__).parent / "company_scrapers"
    scripts = sorted(scrapers_dir.glob("run_*.py"))
    log.info(f"company_scrapers: {len(scripts)} scripts found")
    done: set[str] = set()
    for script in scripts:
        log.info(f"  {script.name} ...")
        r = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(Path(__file__).parent),
            env={**os.environ},
            capture_output=True,
            text=True,
        )
        slug = script.stem.replace("run_", "")
        wrote_jobs = "[OK] jobs.json:" in r.stdout
        if r.returncode == 0:
            done.add(slug.lower())
            log.info(f"    OK")
        elif wrote_jobs:
            done.add(slug.lower())
            log.info(f"    OK (exit {r.returncode} — jobs.json written successfully)")
        else:
            log.warning(f"    FAILED (exit {r.returncode})")
            if r.stderr.strip():
                log.warning(f"    stderr: {r.stderr.strip()[-400:]}")
            elif r.stdout.strip():
                log.warning(f"    stdout tail: {r.stdout.strip()[-400:]}")
    return done


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run(portals: list[dict], skip_enrich: bool, log: logging.Logger,
        max_jobs: int | None = None, output_base: str = OUTPUT_BASE,
        validate_mode: bool = False) -> dict:
    summary = {
        "processed": 0, "skipped": 0, "total_new": 0,
        "errors": [], "start": datetime.now().isoformat(),
    }
    total = len(portals)

    for idx, portal in enumerate(portals, 1):
        company = portal["company"]
        ats     = portal["ats"]
        js_flag = "  [JS/Firecrawl extract]" if portal.get("js_required") else ""
        log.info(f"[{idx}/{total}] {company}  ({ats}){js_flag}")

        # ── Scrape ────────────────────────────────────────────────────────────
        try:
            raw_jobs = scrape_portal(portal, log, max_jobs=max_jobs, validate_mode=validate_mode)
        except Exception as e:
            log.error(f"  FATAL scrape error — {company}: {e}")
            summary["errors"].append({"company": company, "stage": "scrape", "error": str(e)})
            summary["skipped"] += 1
            continue

        if not raw_jobs:
            log.info(f"  0 India jobs — skipping")
            summary["skipped"] += 1
            continue

        # Safety truncation for validate mode (scrapers cap internally where efficient,
        # this catches anything that slipped through — e.g. Greenhouse, Phenom)
        if max_jobs:
            raw_jobs = raw_jobs[:max_jobs]

        log.info(f"  {len(raw_jobs)} raw jobs scraped")

        # ── Normalise to 7-field schema ───────────────────────────────────────
        canonical = [to_canonical(j, company) for j in raw_jobs]

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
        try:
            path, new_count = save_jobs(company, enriched, output_base=output_base)
            log.info(f"  Saved {new_count} new jobs → {path}")
            summary["processed"] += 1
            summary["total_new"] += new_count
        except Exception as e:
            log.error(f"  FATAL save error — {company}: {e}")
            summary["errors"].append({"company": company, "stage": "save", "error": str(e)})

        time.sleep(_INTER_COMPANY_DELAY)

    summary["end"] = datetime.now().isoformat()
    return summary


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

        # Write back JSON
        json_path.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding='utf-8')

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
    parser.add_argument("--with-company-scrapers", action="store_true", help="Run company_scrapers/ scripts before KNOWN_PORTALS phase")
    parser.add_argument("--validate",              action="store_true",
                        help=f"Validation run: scrape {_VALIDATE_MAX_JOBS} jobs/company, no enrichment, "
                             f"write to validation_outputs/ — use to verify column coverage across all portals")
    args = parser.parse_args()

    log = setup_logging()

    if args.enrich_only:
        enrich_only_run(log)
        return

    # --validate: cap to 5 jobs/company, no enrichment, separate output folder
    validate_mode = args.validate
    max_jobs      = _VALIDATE_MAX_JOBS if validate_mode else None
    output_base   = _VALIDATE_OUTPUT_BASE if validate_mode else OUTPUT_BASE
    if validate_mode:
        log.info(f"VALIDATE MODE: max {_VALIDATE_MAX_JOBS} jobs/company → {output_base}")

    scraped_slugs: set[str] = set()
    if args.with_company_scrapers:
        scraped_slugs = run_company_scrapers(log)
        log.info(f"company_scrapers done: {len(scraped_slugs)} companies")

    portals = parse_portals()
    if scraped_slugs:
        before = len(portals)
        portals = [p for p in portals
                   if company_slug(p["company"]).lower().replace("_", "") not in
                   {s.replace("_", "") for s in scraped_slugs}]
        log.info(f"Skipping {before - len(portals)} portals already done by company_scrapers")
    if args.company:
        portals = [p for p in portals if args.company.lower() in p["company"].lower()]
    if args.ats:
        portals = [p for p in portals if p["ats"] == args.ats.lower()]
    if args.resume:
        before = len(portals)
        portals = [p for p in portals if not already_scraped(p["company"])]
        skipped = before - len(portals)
        log.info(f"--resume: skipping {skipped} already-scraped companies, {len(portals)} remaining")

    log.info(f"Portals to process: {len(portals)}")
    for p in portals:
        flag = "🌐" if p["js_required"] else "⚡"
        log.info(f"  {flag}  {p['company']:<30} [{p['ats']}]")

    if args.dry_run:
        return

    log.info("─" * 60)
    summary = run(portals, skip_enrich=args.skip_enrich or validate_mode, log=log,
                  max_jobs=max_jobs, output_base=output_base, validate_mode=validate_mode)

    log.info("─" * 60)
    log.info(f"RUN COMPLETE")
    log.info(f"  Companies processed : {summary['processed']}")
    log.info(f"  Companies skipped   : {summary['skipped']}")
    log.info(f"  Total new jobs      : {summary['total_new']}")
    log.info(f"  Started             : {summary['start']}")
    log.info(f"  Ended               : {summary['end']}")

    if summary["errors"]:
        log.warning(f"  Errors ({len(summary['errors'])}):")
        for e in summary["errors"]:
            log.warning(f"    [{e['stage']}] {e['company']}: {e['error']}")


if __name__ == "__main__":
    main()
