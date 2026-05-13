"""
supabase_enricher.py — Two-mode backfill for Supabase `jobs` table.

Mode 1 (default): enrich skills
  Pull rows: job_description present, main_skills empty.
  Run enrich_job() → write job_skills with is_primary + required_level.
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

import requests
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

_SKILL_ID_CACHE: dict[str, int] | None = None


def _job_skills_has_required_level() -> bool:
    """Return True when live Supabase job_skills exposes required_level."""
    url = (os.getenv("SUPABASE_URL", "") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return False

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/openapi+json",
    }
    try:
        response = requests.get(f"{url}/rest/v1/", headers=headers, timeout=30)
        response.raise_for_status()
        spec = response.json()
    except Exception:
        return False

    schemas = spec.get("definitions") or spec.get("components", {}).get("schemas") or {}
    table = schemas.get("job_skills") or schemas.get("public.job_skills") or {}
    return "required_level" in (table.get("properties") or {})


def _get_skill_id_map(sb: Client) -> dict[str, int]:
    """Load skills.taxonomy_key → skills.id map. Cached after first call."""
    global _SKILL_ID_CACHE
    if _SKILL_ID_CACHE is not None:
        return _SKILL_ID_CACHE
    skill_map: dict[str, int] = {}
    page, page_size = 0, 1000
    while True:
        batch = (
            sb.table("skills").select("id, taxonomy_key")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        ).data or []
        for row in batch:
            if row.get("taxonomy_key") and row.get("id"):
                skill_map[row["taxonomy_key"]] = row["id"]
        if len(batch) < page_size:
            break
        page += 1
    _SKILL_ID_CACHE = skill_map
    return skill_map


def _supabase() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in scraper/.env")
        sys.exit(1)
    return create_client(url, key)


# ── Mode 1: Skill enrichment ──────────────────────────────────────────────────

def fetch_unenriched(sb: Client, company: str | None, limit: int | None) -> list[dict]:
    """Pull jobs that have a description but no job_skills rows."""
    # Get all job_ids that already have skills in job_skills
    enriched_ids: set[str] = set()
    page, page_size = 0, 1000
    while True:
        batch = (
            sb.table("job_skills").select("job_id")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        ).data or []
        enriched_ids.update(r["job_id"] for r in batch)
        if len(batch) < page_size:
            break
        page += 1

    results: list[dict] = []
    page = 0
    while True:
        q = (
            sb.table(TABLE)
            .select("job_id,job_title,job_description,company_name,location,industry,apply_url")
            .gt("job_description", "")
            .order("company_name")
            .range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1)
        )
        if company:
            q = q.eq("company_name", company)
        batch = q.execute().data or []
        # Filter out already-enriched jobs
        results.extend(r for r in batch if r["job_id"] not in enriched_ids)
        if len(batch) < PAGE_SIZE:
            break
        if limit and len(results) >= limit:
            break
        page += 1

    results = [r for r in results if len(r.get("job_description") or "") >= MIN_DESC_LEN]
    if limit:
        results = results[:limit]
    return results


def _skill_entries_from_enriched(enriched: dict) -> list[dict]:
    structured = enriched.get("skills")
    if isinstance(structured, list) and structured:
        entries = []
        for item in structured:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            is_primary = bool(item.get("is_primary"))
            level = item.get("required_level")
            if not isinstance(level, int) or level not in (1, 2, 3, 4):
                level = 2 if is_primary else 1
            entries.append({
                "name": name,
                "is_primary": is_primary,
                "required_level": level,
            })
        return entries

    return [
        {"name": skill, "is_primary": True, "required_level": 2}
        for skill in (enriched.get("main_skills") or [])
    ] + [
        {"name": skill, "is_primary": False, "required_level": 1}
        for skill in (enriched.get("side_skills") or [])
    ]


def write_job_skills(sb: Client, job_id: str, skills: list[dict]) -> tuple[int, list[str]]:
    """
    Resolve skill names → skill_ids and upsert to job_skills.
    Returns (rows_written, list_of_unresolved_skill_names).
    Skills not found in the `skills` table are logged as taxonomy drift and skipped.
    """
    skill_id_map = _get_skill_id_map(sb)
    rows: list[dict] = []
    unresolved: list[str] = []

    for skill in skills:
        name = skill["name"]
        sid = skill_id_map.get(name)
        if sid:
            rows.append({
                "job_id": job_id,
                "skill_id": sid,
                "is_primary": skill["is_primary"],
                "required_level": skill["required_level"],
            })
        else:
            unresolved.append(name)

    deduped: dict[tuple[str, int], dict] = {}
    for row in rows:
        key = (row["job_id"], row["skill_id"])
        existing = deduped.get(key)
        if not existing:
            deduped[key] = row
            continue
        existing["is_primary"] = existing["is_primary"] or row["is_primary"]
        existing["required_level"] = max(existing["required_level"], row["required_level"])
    rows = list(deduped.values())

    if rows:
        sb.table("job_skills").upsert(rows, on_conflict="job_id,skill_id").execute()

    return len(rows), unresolved


def _enrich_one(job: dict) -> tuple[str, list[dict]]:
    from enricher import enrich_job
    enriched = enrich_job(job)
    return job["job_id"], _skill_entries_from_enriched(enriched)


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

    if not _job_skills_has_required_level():
        log.error(
            "job_skills.required_level is missing in Supabase. "
            "Run scraper/sql/add_job_skills_required_level.sql before enrichment backfill."
        )
        raise SystemExit(2)

    ok = fail = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_enrich_one, job): job for job in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            job = futures[fut]
            try:
                job_id, skills = fut.result()
                if skills:
                    written, drift = write_job_skills(sb, job_id, skills)
                    if drift:
                        log.warning(f"  [{i}] Taxonomy drift for {job.get('job_title')}: {drift}")
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
