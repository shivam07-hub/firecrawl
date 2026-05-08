"""
csv_importer.py — Phase 3: upload enriched local JSON to Supabase.

Reads All_CSV_Outputs/*/Outputs/*/jobs.json and:
  1. Upserts core job fields to the `jobs` table (with lifecycle tracking).
  2. Resolves main_skills/side_skills → skill_ids via the `skills` table.
  3. Upserts rows to `job_skills (job_id, skill_id, is_primary)`.
  4. Logs skills that don't resolve (taxonomy drift signal).

Usage:
    python csv_importer.py                        # all companies, latest date folder
    python csv_importer.py --company "Barclays"   # one company
    python csv_importer.py --all-dates            # all date folders, not just latest
    python csv_importer.py --dry-run              # print counts, no writes
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
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
log = logging.getLogger("csv_importer")

from config import OUTPUT_BASE

_JOB_FIELDS = [
    "job_id", "job_title", "job_description",
    "industry", "company_name", "location", "apply_url",
    "role_domain", "batch_date",
    "location_raw", "location_city", "location_country", "location_mode", "location_quality",
]

_BATCH_SIZE = 200
_UNKNOWN_LOCATION_THRESHOLD = 0.10
_LOCATION_PARSER_VERSION = "v1"

# ── Industry group mapping (10 super-categories) ──────────────────────────────

_INDUSTRY_GROUP: dict[str, str] = {
    "Technology":                   "Technology",
    "Semiconductors":               "Technology",
    "Software":                     "Technology",
    "Cloud":                        "Technology",
    "IT Services":                  "Consulting & Professional Services",
    "Consulting":                   "Consulting & Professional Services",
    "Legal":                        "Consulting & Professional Services",
    "BFSI":                         "BFSI",
    "Fintech":                      "BFSI",
    "Insurance":                    "BFSI",
    "Automotive":                   "Manufacturing & Industrial",
    "Manufacturing":                "Manufacturing & Industrial",
    "Engineering":                  "Manufacturing & Industrial",
    "Aerospace & Defense":          "Manufacturing & Industrial",
    "Energy":                       "Energy & Resources",
    "Oil & Gas":                    "Energy & Resources",
    "Chemicals":                    "Energy & Resources",
    "Pharmaceutical":               "Healthcare & Life Sciences",
    "Healthcare":                   "Healthcare & Life Sciences",
    "MedTech":                      "Healthcare & Life Sciences",
    "Biotechnology":                "Healthcare & Life Sciences",
    "Consumer Goods":               "Consumer & Retail",
    "Retail":                       "Consumer & Retail",
    "E-commerce & Retail":          "Consumer & Retail",
    "FMCG":                         "Consumer & Retail",
    "Food & Beverage":              "Consumer & Retail",
    "Media & Entertainment":        "Media & Telecom",
    "Telecom":                      "Media & Telecom",
    "Logistics":                    "Logistics & Supply Chain",
    "Shipping & Logistics":         "Logistics & Supply Chain",
    "Aviation":                     "Logistics & Supply Chain",
    "Conglomerate":                 "Diversified",
    "Real Estate":                  "Diversified",
    "Education":                    "Diversified",
    "Professional Services":        "Consulting & Professional Services",
}

# ── Canonical location parser (deterministic aliases) ─────────────────────────

@dataclass(frozen=True)
class NormalizedLocation:
    location: str | None
    location_raw: str | None
    location_city: str | None
    location_country: str | None
    location_mode: str
    location_quality: str


_SPACE_RE = re.compile(r"\s+")
_MULTI_LOCATION_RE = re.compile(r"\b\d+\s*locations?\b|multiple locations|various locations")
_REMOTE_RE = re.compile(r"\bremote\b|\bwork from home\b|\bwfh\b|\bworldwide\b|\banywhere\b")
_HYBRID_RE = re.compile(r"\bhybrid\b")

_CITY_ALIASES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bbangalore\b|\bbengaluru\b"), "Bengaluru"),
    (re.compile(r"\bhyderabad\b"), "Hyderabad"),
    (re.compile(r"\bmumbai\b|\bbombay\b"), "Mumbai"),
    (re.compile(r"\bpune\b"), "Pune"),
    (re.compile(r"\bchennai\b|\bmadras\b"), "Chennai"),
    (re.compile(r"\bnew delhi\b|\bdelhi\b|\bncr\b"), "Delhi NCR"),
    (re.compile(r"\bgurgaon\b|\bgurugram\b"), "Gurugram"),
    (re.compile(r"\bnoida\b"), "Noida"),
    (re.compile(r"\bkolkata\b|\bcalcutta\b"), "Kolkata"),
    (re.compile(r"\bahmedabad\b"), "Ahmedabad"),
)

_COUNTRY_ALIASES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bindia\b|(?:^|[,\s\-])in(?:$|[,\s\-])"), "India"),
    (re.compile(r"\busa\b|\bunited states\b|\bu\.s\.\b"), "United States"),
    (re.compile(r"\buk\b|\bunited kingdom\b"), "United Kingdom"),
    (re.compile(r"\bsingapore\b"), "Singapore"),
    (re.compile(r"\bcanada\b"), "Canada"),
    (re.compile(r"\bgermany\b"), "Germany"),
    (re.compile(r"\bfrance\b"), "France"),
)

_INDIA_CITIES = {
    "Bengaluru",
    "Hyderabad",
    "Mumbai",
    "Pune",
    "Chennai",
    "Delhi NCR",
    "Gurugram",
    "Noida",
    "Kolkata",
    "Ahmedabad",
}


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _SPACE_RE.sub(" ", value.strip())
    return cleaned or None


def _infer_mode(lower: str) -> str:
    if _HYBRID_RE.search(lower):
        return "hybrid"
    if _REMOTE_RE.search(lower):
        return "remote"
    return "unknown"


def _infer_city(lower: str, raw: str) -> str | None:
    for pattern, canonical in _CITY_ALIASES:
        if pattern.search(lower):
            return canonical

    token = re.split(r"[;,|]", raw, maxsplit=1)[0]
    token = re.split(r"\s+-\s+", token, maxsplit=1)[0].strip()
    if not token or re.search(r"\d", token):
        return None
    token_lower = token.lower()
    if any(word in token_lower for word in ("location", "remote", "hybrid", "worldwide", "anywhere")):
        return None
    return _SPACE_RE.sub(" ", token.title())


def _infer_country(lower: str) -> str | None:
    for pattern, canonical in _COUNTRY_ALIASES:
        if pattern.search(lower):
            return canonical
    return None


def _display_location(
    *,
    city: str | None,
    country: str | None,
    mode: str,
    quality: str,
    raw: str | None,
) -> str | None:
    if quality == "unknown":
        return raw
    if mode == "remote":
        return f"Remote - {country}" if country else "Remote"
    if mode == "hybrid":
        if city and country:
            return f"Hybrid - {city}, {country}"
        if city:
            return f"Hybrid - {city}"
        return f"Hybrid - {country}" if country else "Hybrid"
    if city and country:
        return f"{city}, {country}"
    return city or country or raw


def _normalize_location(value: str | None) -> NormalizedLocation:
    raw = _clean_text(value)
    if raw is None:
        return NormalizedLocation(
            location=None,
            location_raw=None,
            location_city=None,
            location_country=None,
            location_mode="unknown",
            location_quality="unknown",
        )

    lower = raw.lower()
    mode = _infer_mode(lower)
    city = _infer_city(lower, raw)
    country = _infer_country(lower)
    if city in _INDIA_CITIES and not country:
        country = "India"

    if mode == "unknown" and _MULTI_LOCATION_RE.search(lower):
        quality = "unknown"
        city = None
    elif mode == "unknown" and city is None and country is None:
        quality = "unknown"
    else:
        quality = "ok"
    if mode == "unknown" and quality == "ok" and (city or country):
        mode = "onsite"

    return NormalizedLocation(
        location=_display_location(city=city, country=country, mode=mode, quality=quality, raw=raw),
        location_raw=raw,
        location_city=city,
        location_country=country,
        location_mode=mode,
        location_quality=quality,
    )


def _valid_apply_url(url: str | None) -> str | None:
    if not url:
        return None
    if not url.startswith("http"):
        return None
    if re.search(r"\.(png|jpg|jpeg|gif|svg|webp|pdf)(\?|$)", url, re.IGNORECASE):
        return None
    return url


def _industry_group(industry: str | None) -> str | None:
    if not industry:
        return None
    return _INDUSTRY_GROUP.get(industry, "Diversified")


# ── Supabase client ────────────────────────────────────────────────────────────

def _supabase() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in scraper/.env")
        sys.exit(1)
    return create_client(url, key)


# ── Skill ID cache ─────────────────────────────────────────────────────────────

def _build_skill_id_map(sb: Client) -> dict[str, int]:
    log.info("Loading skills table from Supabase...")
    skill_map: dict[str, int] = {}
    page = 0
    page_size = 1000
    while True:
        batch = (
            sb.table("skills")
            .select("id, taxonomy_key")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        ).data or []
        for row in batch:
            if row.get("taxonomy_key") and row.get("id"):
                skill_map[row["taxonomy_key"]] = row["id"]
        if len(batch) < page_size:
            break
        page += 1
    log.info(f"Loaded {len(skill_map)} skills from taxonomy")
    return skill_map


# ── Job file discovery ─────────────────────────────────────────────────────────

def _find_json_files(company_filter: str | None, all_dates: bool) -> list[Path]:
    base = Path(OUTPUT_BASE)
    if not base.exists():
        log.error(f"OUTPUT_BASE not found: {base}")
        return []

    result: list[Path] = []
    for company_dir in sorted(base.iterdir()):
        if not company_dir.is_dir():
            continue
        if company_filter and company_filter.lower() not in company_dir.name.lower():
            continue

        outputs = company_dir / "Outputs"
        if not outputs.exists():
            continue

        date_dirs = sorted(
            [d for d in outputs.iterdir() if d.is_dir()],
            reverse=True,
        )

        if all_dates:
            for d in date_dirs:
                p = d / "jobs.json"
                if p.exists():
                    result.append(p)
        else:
            for d in date_dirs:
                p = d / "jobs.json"
                if p.exists():
                    result.append(p)
                    break

    return result


# ── Core import logic ──────────────────────────────────────────────────────────

def _upsert_jobs(
    sb: Client,
    jobs: list[dict],
    batch_date: int | None,
    location_alias_counter: Counter[str],
) -> tuple[int, int]:
    rows = []
    unknown_location_rows = 0
    for job in jobs:
        if not job.get("job_id"):
            continue

        row = {f: job.get(f) for f in _JOB_FIELDS if job.get(f) is not None}
        normalized_location = _normalize_location(job.get("location"))

        # Derived fields
        row["industry_group"] = _industry_group(job.get("industry"))
        row["location"] = normalized_location.location
        row["location_raw"] = normalized_location.location_raw
        row["location_city"] = normalized_location.location_city
        row["location_country"] = normalized_location.location_country
        row["location_mode"] = normalized_location.location_mode
        row["location_quality"] = normalized_location.location_quality
        row["apply_url"]      = _valid_apply_url(job.get("apply_url"))
        if normalized_location.location_quality == "unknown":
            unknown_location_rows += 1
            if normalized_location.location_raw:
                location_alias_counter[normalized_location.location_raw.lower()] += 1

        # Lifecycle: first_seen set only on insert; last_seen always updated
        effective_date = batch_date or job.get("batch_date")
        if effective_date:
            row["last_seen"]  = effective_date
            row["first_seen"] = effective_date  # ignored on conflict (see upsert below)
            row["is_active"]  = True

        rows.append(row)

    # Deduplicate by job_id — keep last occurrence
    seen_jobs: dict[str, dict] = {}
    for r in rows:
        seen_jobs[r["job_id"]] = r
    rows = list(seen_jobs.values())

    if not rows:
        return 0

    for i in range(0, len(rows), _BATCH_SIZE):
        batch = rows[i:i + _BATCH_SIZE]
        # On conflict: update everything EXCEPT first_seen and is_active
        # (community owns is_active; first_seen is set once at insert)
        sb.table("jobs").upsert(
            batch,
            on_conflict="job_id",
            ignore_duplicates=False,
        ).execute()

    return len(rows), unknown_location_rows


def _resolve_and_upsert_skills(
    sb: Client,
    jobs: list[dict],
    skill_id_map: dict[str, int],
    drift_counter: Counter,
    dry_run: bool,
) -> tuple[int, int]:
    skill_rows: list[dict] = []
    local_drift = 0

    for job in jobs:
        job_id = job.get("job_id")
        if not job_id:
            continue

        for skill in (job.get("main_skills") or []):
            skill_id = skill_id_map.get(skill)
            if skill_id:
                skill_rows.append({"job_id": job_id, "skill_id": skill_id, "is_primary": True})
            else:
                drift_counter[skill] += 1
                local_drift += 1

        for skill in (job.get("side_skills") or []):
            skill_id = skill_id_map.get(skill)
            if skill_id:
                skill_rows.append({"job_id": job_id, "skill_id": skill_id, "is_primary": False})
            else:
                drift_counter[skill] += 1
                local_drift += 1

    # Deduplicate by (job_id, skill_id) — a skill can appear in both main + side;
    # keep is_primary=True if either occurrence is primary.
    seen: dict[tuple[str, int], bool] = {}
    for r in skill_rows:
        key = (r["job_id"], r["skill_id"])
        seen[key] = seen.get(key, False) or r["is_primary"]
    skill_rows = [{"job_id": k[0], "skill_id": k[1], "is_primary": v} for k, v in seen.items()]

    if dry_run or not skill_rows:
        return len(skill_rows), local_drift

    for i in range(0, len(skill_rows), _BATCH_SIZE):
        batch = skill_rows[i:i + _BATCH_SIZE]
        sb.table("job_skills").upsert(
            batch, on_conflict="job_id,skill_id"
        ).execute()

    return len(skill_rows), local_drift


def _write_diagnostic(
    sb: Client,
    run_id: str,
    company: str,
    raw_jobs: int,
    saved_new: int,
    enriched: int,
    drift: int,
) -> None:
    enriched_pct = round(enriched / raw_jobs * 100) if raw_jobs else 0
    sb.table("scrape_diagnostics").insert({
        "run_id":       run_id,
        "scope":        "india",
        "company_name": company,
        "status":       "upload",
        "raw_jobs":     raw_jobs,
        "saved_new":    saved_new,
        "reason":       f"{enriched_pct}% enriched, {drift} skill drift",
    }).execute()


def _write_location_audit(
    sb: Client,
    *,
    run_id: str,
    total_rows: int,
    unknown_location_rows: int,
    unknown_location_rate: float,
    top_unknown_aliases: list[dict[str, int]],
    status: str,
    message: str | None,
) -> None:
    sb.table("job_feed_run_audits").insert({
        "run_id": run_id,
        "source": "firecrawl_csv_importer",
        "parser_version": _LOCATION_PARSER_VERSION,
        "total_rows": total_rows,
        "unknown_location_rows": unknown_location_rows,
        "unknown_location_rate": unknown_location_rate,
        "top_unknown_aliases": top_unknown_aliases,
        "status": status,
        "message": message,
    }).execute()


def import_file(
    sb: Client,
    json_path: Path,
    skill_id_map: dict[str, int],
    drift_counter: Counter,
    unknown_location_counter: Counter[str],
    dry_run: bool,
    run_id: str = "",
) -> dict:
    try:
        jobs = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"path": str(json_path), "error": str(e)}

    if not isinstance(jobs, list) or not jobs:
        return {"path": str(json_path), "jobs": 0, "skill_rows": 0}

    company    = jobs[0].get("company_name", json_path.parent.parent.parent.name)
    date_str   = json_path.parent.name
    batch_date = int(date_str.replace("-", "")) if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str) else None
    enriched   = sum(1 for j in jobs if j.get("main_skills"))

    local_unknown = 0
    if not dry_run:
        jobs_written, local_unknown = _upsert_jobs(sb, jobs, batch_date, unknown_location_counter)
    else:
        jobs_written = sum(1 for j in jobs if j.get("job_id"))
        for job in jobs:
            normalized = _normalize_location(job.get("location"))
            if normalized.location_quality == "unknown":
                local_unknown += 1
                if normalized.location_raw:
                    unknown_location_counter[normalized.location_raw.lower()] += 1

    skill_rows_written, drift = _resolve_and_upsert_skills(
        sb, jobs, skill_id_map, drift_counter, dry_run
    )

    if not dry_run and run_id:
        _write_diagnostic(sb, run_id, company, len(jobs), jobs_written, enriched, drift)

    return {
        "path": str(json_path),
        "company": company,
        "date": date_str,
        "jobs": jobs_written,
        "skill_rows": skill_rows_written,
        "drift": drift,
        "enriched": enriched,
        "unknown_location_rows": local_unknown,
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3: upload enriched jobs to Supabase")
    parser.add_argument("--company",   help="Filter by company slug (substring, case-insensitive)")
    parser.add_argument("--all-dates", action="store_true", help="Import all date folders, not just latest")
    parser.add_argument("--dry-run",   action="store_true", help="Count only — no writes to Supabase")
    args = parser.parse_args()

    sb = _supabase()
    skill_id_map = _build_skill_id_map(sb)

    json_files = _find_json_files(args.company, args.all_dates)
    if not json_files:
        log.warning("No jobs.json files found. Did you run main.py first?")
        return

    log.info(f"Files to import: {len(json_files)}")
    if args.dry_run:
        log.info("DRY RUN — no writes")

    run_id = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log.info(f"Run ID: {run_id}")

    drift_counter: Counter = Counter()
    unknown_location_counter: Counter[str] = Counter()
    total_jobs = total_skill_rows = total_drift = total_unknown_location_rows = 0
    t0 = time.time()

    for json_path in json_files:
        result = import_file(
            sb,
            json_path,
            skill_id_map,
            drift_counter,
            unknown_location_counter,
            args.dry_run,
            run_id,
        )
        if "error" in result:
            log.warning(f"  {result['path']}: {result['error']}")
            continue

        enriched = result.get("enriched", 0)
        enriched_pct = round(enriched / result["jobs"] * 100) if result["jobs"] else 0
        log.info(
            f"  {result['company']} [{result['date']}]: "
            f"{result['jobs']} jobs, {result['skill_rows']} skill rows, "
            f"{enriched_pct}% enriched"
            + (f", {result['drift']} drift" if result['drift'] else "")
            + (f", {result['unknown_location_rows']} unknown locations" if result.get("unknown_location_rows") else "")
        )
        total_jobs       += result["jobs"]
        total_skill_rows += result["skill_rows"]
        total_drift      += result.get("drift", 0)
        total_unknown_location_rows += result.get("unknown_location_rows", 0)

    elapsed = time.time() - t0
    unknown_rate = (total_unknown_location_rows / total_jobs) if total_jobs else 0.0
    top_unknown_aliases = [
        {"alias": alias, "count": count}
        for alias, count in unknown_location_counter.most_common(20)
    ]
    status = "blocked" if unknown_rate > _UNKNOWN_LOCATION_THRESHOLD else "ok"
    message = None
    if status == "blocked":
        message = (
            f"Unknown location rate {unknown_rate:.2%} exceeded threshold "
            f"{_UNKNOWN_LOCATION_THRESHOLD:.2%}"
        )
        log.error(message)
    if not args.dry_run:
        _write_location_audit(
            sb,
            run_id=run_id,
            total_rows=total_jobs,
            unknown_location_rows=total_unknown_location_rows,
            unknown_location_rate=unknown_rate,
            top_unknown_aliases=top_unknown_aliases,
            status=status,
            message=message,
        )

    log.info("─" * 60)
    log.info(f"Done: {total_jobs} jobs, {total_skill_rows} job_skills rows — {elapsed:.0f}s")
    log.info(
        "Location quality: %s unknown rows (%s)",
        total_unknown_location_rows,
        f"{unknown_rate:.2%}",
    )

    if drift_counter:
        log.warning(f"Taxonomy drift: {total_drift} skill strings not in `skills` table")
        log.warning("Top 20 unresolved:")
        for skill, count in drift_counter.most_common(20):
            log.warning(f"  {count:4d}×  {skill!r}")

    if status == "blocked":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
