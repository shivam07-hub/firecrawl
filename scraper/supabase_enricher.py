"""
supabase_enricher.py — Two-mode backfill for Supabase `jobs` table.

Mode 1 (default): enrich skills
  Pull rows: job_description present, main_skills empty.
  Run enrich_job() → UPDATE main_skills + side_skills.
  Requires LM Studio running at LM_STUDIO_BASE_URL.

Mode 2 (--fetch-jds): fetch missing job descriptions
  Pull rows: job_description empty, apply_url present.
  Run fc.scrape(apply_url) → UPDATE job_description.
  Requires Firecrawl Docker running at FIRECRAWL_URL.

Usage:
    python supabase_enricher.py                          # enrich skills, all companies
    python supabase_enricher.py --company "Barclays"     # one company
    python supabase_enricher.py --dry-run                # count only, no writes
    python supabase_enricher.py --limit 100              # cap rows processed
    python supabase_enricher.py --fetch-jds              # backfill missing JDs via Firecrawl
    python supabase_enricher.py --fetch-jds --company "AstraZeneca"
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

load_dotenv(_HERE / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("supabase_enricher")

TABLE = "jobs"
PAGE_SIZE = 500
MIN_DESC_LEN = 200
MIN_JD_SCRAPE_LEN = 300  # minimum chars for a scraped JD to be considered valid


def _supabase() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in scraper/.env")
        sys.exit(1)
    return create_client(url, key)


# ── Mode 1: Skill enrichment ──────────────────────────────────────────────────

def fetch_unenriched(sb: Client, company: str | None, limit: int | None) -> list[dict]:
    """Pull rows with job_description but no main_skills."""
    results: list[dict] = []
    page = 0
    while True:
        q = (
            sb.table(TABLE)
            .select("job_id,job_title,job_description,company_name,location,industry,apply_url")
            .or_("main_skills.is.null,main_skills.eq.{}")
            .gt("job_description", "")
            .order("company_name")
            .range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1)
        )
        if company:
            q = q.eq("company_name", company)
        batch = q.execute().data
        results.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        if limit and len(results) >= limit:
            break
        page += 1

    results = [r for r in results if len(r.get("job_description") or "") >= MIN_DESC_LEN]
    if limit:
        results = results[:limit]
    return results


def update_skills(sb: Client, job_id: str, main_skills: list[str], side_skills: list[str]) -> None:
    sb.table(TABLE).update(
        {"main_skills": main_skills, "side_skills": side_skills}
    ).eq("job_id", job_id).execute()


def _enrich_one(job: dict) -> tuple[str, list[str], list[str]]:
    from enricher import enrich_job
    enriched = enrich_job(job)
    return job["job_id"], enriched.get("main_skills") or [], enriched.get("side_skills") or []


def run_enrich(sb: Client, jobs: list[dict], dry_run: bool, workers: int) -> None:
    if not jobs:
        log.info("No eligible jobs found.")
        return

    counts = Counter(j["company_name"] for j in jobs)
    log.info(f"Eligible: {len(jobs)} jobs across {len(counts)} companies")
    for company, n in counts.most_common():
        log.info(f"  {n:4d}  {company}")

    if dry_run:
        log.info("Dry-run — no writes.")
        return

    ok = fail = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_enrich_one, job): job for job in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            job = futures[fut]
            try:
                job_id, ms, ss = fut.result()
                if ms:
                    update_skills(sb, job_id, ms, ss)
                    ok += 1
                else:
                    log.warning(f"  [{i}] No skills: {job.get('job_title')} ({job['job_id']})")
                    fail += 1
            except Exception as e:
                log.warning(f"  [{i}] Failed {job.get('job_title')}: {e}")
                fail += 1

            if i % 50 == 0:
                elapsed = time.time() - t0
                log.info(f"  Progress: {i}/{len(jobs)} — {ok} ok / {fail} failed — {elapsed:.0f}s")

    log.info(f"Done: {ok} enriched, {fail} failed — {time.time() - t0:.0f}s total")


# ── Mode 2: JD fetch ──────────────────────────────────────────────────────────

def fetch_empty_jd_rows(sb: Client, company: str | None, limit: int | None) -> list[dict]:
    """Pull rows with empty job_description but a valid apply_url."""
    results: list[dict] = []
    page = 0
    while True:
        q = (
            sb.table(TABLE)
            .select("job_id,job_title,company_name,apply_url")
            .or_("job_description.is.null,job_description.eq.")
            .not_.is_("apply_url", "null")
            .order("company_name")
            .range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1)
        )
        if company:
            q = q.eq("company_name", company)
        batch = q.execute().data
        results.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        if limit and len(results) >= limit:
            break
        page += 1

    # Exclude rows where apply_url is empty string
    results = [r for r in results if r.get("apply_url", "").startswith("http")]
    if limit:
        results = results[:limit]
    return results


def update_description(sb: Client, job_id: str, description: str) -> None:
    sb.table(TABLE).update({"job_description": description}).eq("job_id", job_id).execute()


def _scrape_one_jd(job: dict) -> tuple[str, str]:
    """Scrape apply_url via Firecrawl, return (job_id, jd_text)."""
    import firecrawl_client as fc
    from utils import strip_html
    url = job["apply_url"]
    md = fc.scrape(url)
    # Firecrawl returns markdown; strip any residual HTML tags
    text = strip_html(md) if md else ""
    return job["job_id"], text


def run_fetch_jds(sb: Client, jobs: list[dict], dry_run: bool, workers: int) -> None:
    if not jobs:
        log.info("No rows with empty job_description found.")
        return

    counts = Counter(j["company_name"] for j in jobs)
    log.info(f"Empty-JD rows: {len(jobs)} across {len(counts)} companies")
    for company, n in counts.most_common():
        log.info(f"  {n:4d}  {company}")

    if dry_run:
        log.info("Dry-run — no writes.")
        return

    ok = fail = short = 0
    t0 = time.time()

    # JD scraping is serial per Firecrawl credit discipline — no parallel batching
    for i, job in enumerate(jobs, 1):
        try:
            job_id, jd = _scrape_one_jd(job)
            if len(jd) >= MIN_JD_SCRAPE_LEN:
                update_description(sb, job_id, jd)
                ok += 1
            else:
                log.warning(f"  [{i}] JD too short ({len(jd)} chars): {job.get('job_title')} — skipped")
                short += 1
        except Exception as e:
            log.warning(f"  [{i}] Failed {job.get('job_title')} ({job.get('apply_url')}): {e}")
            fail += 1

        if i % 20 == 0:
            elapsed = time.time() - t0
            log.info(f"  Progress: {i}/{len(jobs)} — {ok} ok / {short} short / {fail} err — {elapsed:.0f}s")

    log.info(f"Done: {ok} JDs fetched, {short} too short, {fail} failed — {time.time() - t0:.0f}s total")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", help="Process one company only")
    parser.add_argument("--dry-run", action="store_true", help="Count only, no writes")
    parser.add_argument("--limit", type=int, help="Max rows to process")
    parser.add_argument("--workers", type=int, default=int(os.getenv("ENRICH_WORKERS", "4")),
                        help="Parallel workers (mode 1 only)")
    parser.add_argument("--fetch-jds", action="store_true",
                        help="Mode 2: fetch missing job_description via Firecrawl scrape(apply_url)")
    args = parser.parse_args()

    sb = _supabase()

    if args.fetch_jds:
        log.info(f"Mode: fetch-jds{f' for {args.company}' if args.company else ''}")
        jobs = fetch_empty_jd_rows(sb, args.company, args.limit)
        run_fetch_jds(sb, jobs, dry_run=args.dry_run, workers=args.workers)
    else:
        log.info(f"Mode: enrich-skills{f' for {args.company}' if args.company else ''}")
        jobs = fetch_unenriched(sb, args.company, args.limit)
        run_enrich(sb, jobs, dry_run=args.dry_run, workers=args.workers)


if __name__ == "__main__":
    main()
