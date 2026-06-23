"""
csv_importer.py — Phase 3: upload enriched local JSON to Supabase.

Reads All_CSV_Outputs/*/Outputs/*/jobs.json and:
  1. Upserts core job fields to the `jobs` table (with lifecycle tracking).
  2. Resolves the flat `skills` list (or legacy main_skills fallback) → skill_ids.
  3. Upserts rows to `job_skills (job_id, skill_id, is_primary, required_level)`.
     One bucket: is_primary is always True; importance lives in required_level (1-4).
  4. Logs skills that don't resolve (taxonomy drift signal).

Usage:
    python csv_importer.py                        # all companies, latest date folder
    python csv_importer.py --company "Barclays"   # one company
    python csv_importer.py --all-dates            # all date folders, not just latest
    python csv_importer.py --dry-run              # print counts, no writes
    python csv_importer.py --dry-run --deactivate-missing
                                                  # inspect newest output date without writes
    python csv_importer.py --deactivate-missing --run-date 20260510
                                                  # opt-in stale-job decommission, one run date only
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
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
log = logging.getLogger("csv_importer")

from config import OUTPUT_BASE

_JOB_FIELDS = [
    "job_id", "job_title", "job_description", "job_summary",
    "industry", "company_name", "location", "apply_url",
    "role_domain", "main_skills", "side_skills", "batch_date",
    "location_raw", "location_city", "location_country", "location_mode", "location_quality",
    "locations",
    "date_posted", "seniority_level", "work_mode",
    "min_years_experience", "max_years_experience",
]

_BATCH_SIZE = 200
_UNKNOWN_LOCATION_THRESHOLD = 0.10
_MAX_DEACTIVATION_RATE = 0.75
_LOCATION_PARSER_VERSION = "v1"


def _parse_batch_date(value: str | int | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if re.match(r"^\d{8}$", text):
        return int(text)
    normalized = text.replace("_", "-")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", normalized):
        return int(normalized.replace("-", ""))
    return None

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
    locations: tuple[str, ...] = ()


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


def _canonical_city_list(raw_locations: list | tuple | None) -> list[str]:
    """Canonicalize a provider's per-city array into ordered, deduped city names."""
    out: list[str] = []
    for entry in raw_locations or []:
        if not isinstance(entry, str):
            continue
        s = _clean_text(entry)
        if not s:
            continue
        canonical = _infer_city(s.lower(), s)
        if canonical and canonical not in out:
            out.append(canonical)
    return out


def _normalize_location(
    value: str | None,
    raw_locations: list | tuple | None = None,
) -> NormalizedLocation:
    raw = _clean_text(value)
    if raw is None and not raw_locations:
        return NormalizedLocation(
            location=None,
            location_raw=None,
            location_city=None,
            location_country=None,
            location_mode="unknown",
            location_quality="unknown",
            locations=(),
        )

    # Cities the provider enumerated (multi-location postings, firecrawl #6).
    multi = _canonical_city_list(raw_locations)

    if raw is None:
        # No scalar string, but the provider gave a city array — synthesize.
        lower = ""
        mode = "unknown"
        city = None
        country = None
        quality = "unknown"
    else:
        lower = raw.lower()
        mode = _infer_mode(lower)
        city = _infer_city(lower, raw)
        country = _infer_country(lower)
        if city in _INDIA_CITIES and not country:
            country = "India"

        if mode == "unknown" and _MULTI_LOCATION_RE.search(lower):
            quality = "unknown"
            city = None  # "N Locations" phrase carries no real city by itself
        elif mode == "unknown" and city is None and country is None:
            quality = "unknown"
        else:
            quality = "ok"

    # Recover cities from the array when the scalar parse failed / was a count phrase.
    if multi:
        if city is None:
            city = multi[0]
        if country is None:
            for entry in raw_locations or []:
                inferred = _infer_country((entry or "").lower()) if isinstance(entry, str) else None
                if inferred:
                    country = inferred
                    break
        if city in _INDIA_CITIES and not country:
            country = "India"
        if quality == "unknown" and city:
            quality = "ok"

    if mode == "unknown" and quality == "ok" and (city or country):
        mode = "onsite"

    # Final locations array: scalar primary city first, then the rest, deduped.
    locations: list[str] = []
    if city:
        locations.append(city)
    for c in multi:
        if c not in locations:
            locations.append(c)

    return NormalizedLocation(
        location=_display_location(city=city, country=country, mode=mode, quality=quality, raw=raw),
        location_raw=raw,
        location_city=city,
        location_country=country,
        location_mode=mode,
        location_quality=quality,
        locations=tuple(locations),
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


def _assert_location_audit_contract(run_id: str) -> None:
    """Read-only guard: fail before uploads if the run-audit table shape drifted."""
    url = (os.getenv("SUPABASE_URL", "") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in scraper/.env")
        sys.exit(1)

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/openapi+json",
    }
    try:
        response = requests.get(f"{url}/rest/v1/", headers=headers, timeout=30)
        response.raise_for_status()
        spec = response.json()
    except Exception as exc:
        log.error("Could not read Supabase OpenAPI schema for preflight: %s", exc)
        raise SystemExit(2) from exc

    schemas = spec.get("definitions") or spec.get("components", {}).get("schemas") or {}
    table = schemas.get("job_feed_run_audits") or schemas.get("public.job_feed_run_audits") or {}
    columns = table.get("properties") or {}
    required = {
        "run_id",
        "source",
        "parser_version",
        "total_rows",
        "unknown_location_rows",
        "unknown_location_rate",
        "top_unknown_aliases",
        "status",
    }
    missing = sorted(required - set(columns))
    if missing:
        log.error("job_feed_run_audits is missing required preflight columns: %s", ", ".join(missing))
        raise SystemExit(2)

    run_id_type = columns.get("run_id", {}).get("format") or columns.get("run_id", {}).get("type")
    if run_id_type == "uuid":
        try:
            uuid.UUID(run_id)
        except ValueError as exc:
            log.error("job_feed_run_audits.run_id expects uuid; generated run_id is invalid: %s", run_id)
            raise SystemExit(2) from exc
    log.info("Supabase audit contract preflight OK")


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


def _jobs_has_locations_column() -> bool:
    """Return True when live Supabase jobs exposes the locations[] column.

    _upsert_jobs sends `locations` on every row, so this MUST exist before real
    writes or the whole upsert batch fails (firecrawl #6).
    """
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
    table = schemas.get("jobs") or schemas.get("public.jobs") or {}
    return "locations" in (table.get("properties") or {})


# Card-data columns added for the job_summary + structured-chip work.
# _upsert_jobs sends these on every row, so they MUST exist before real writes.
_CARD_COLUMNS = (
    "job_summary", "date_posted", "seniority_level",
    "work_mode", "min_years_experience", "max_years_experience",
)


def _jobs_missing_card_columns() -> list[str]:
    """Return card columns absent from live Supabase jobs (empty list = all present)."""
    url = (os.getenv("SUPABASE_URL", "") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return list(_CARD_COLUMNS)

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
        return list(_CARD_COLUMNS)

    schemas = spec.get("definitions") or spec.get("components", {}).get("schemas") or {}
    table = schemas.get("jobs") or schemas.get("public.jobs") or {}
    props = table.get("properties") or {}
    return [c for c in _CARD_COLUMNS if c not in props]


def _job_skill_entries(job: dict) -> list[dict]:
    """One flat bucket of needed skills → job_skills rows.

    There is no primary/side split: is_primary is always True and importance is
    carried by required_level (1-4). The structured `skills` list (model levels)
    is preferred; legacy main_skills/side_skills name lists are the fallback for
    older dump files (no model levels → default L2).
    """
    structured = job.get("skills")
    if isinstance(structured, list) and structured:
        result = []
        for item in structured:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            level = item.get("required_level")
            if not isinstance(level, int) or level not in (1, 2, 3, 4):
                level = 2
            result.append({
                "name": name,
                "is_primary": True,
                "required_level": level,
            })
        return result

    names = list(job.get("main_skills") or []) + list(job.get("side_skills") or [])
    return [
        {"name": skill, "is_primary": True, "required_level": 2}
        for skill in names if isinstance(skill, str) and skill.strip()
    ]


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

        # Drop None always; drop "" only for smallint numeric columns (Postgres
        # rejects "" for smallint). Empty strings are kept for text columns to
        # preserve prior insert behavior (e.g. NOT NULL job_description).
        _INT_FIELDS = {"min_years_experience", "max_years_experience"}
        row = {}
        for f in _JOB_FIELDS:
            v = job.get(f)
            if v is None or (v == "" and f in _INT_FIELDS):
                continue
            row[f] = v
        normalized_location = _normalize_location(job.get("location"), job.get("locations"))

        # Derived fields
        row["industry_group"] = _industry_group(job.get("industry"))
        row["location"] = normalized_location.location
        row["location_raw"] = normalized_location.location_raw
        row["location_city"] = normalized_location.location_city
        row["location_country"] = normalized_location.location_country
        row["location_mode"] = normalized_location.location_mode
        row["location_quality"] = normalized_location.location_quality
        row["locations"] = list(normalized_location.locations)
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
    supports_required_level: bool,
) -> tuple[int, int]:
    skill_rows: list[dict] = []
    local_drift = 0

    for job in jobs:
        job_id = job.get("job_id")
        if not job_id:
            continue

        for skill_entry in _job_skill_entries(job):
            skill = skill_entry["name"]
            skill_id = skill_id_map.get(skill)
            if skill_id:
                row = {
                    "job_id": job_id,
                    "skill_id": skill_id,
                    "is_primary": skill_entry["is_primary"],
                    "required_level": skill_entry["required_level"],
                }
                skill_rows.append(row)
            else:
                drift_counter[skill] += 1
                local_drift += 1

    # Deduplicate by (job_id, skill_id) — keep the strongest required_level.
    # (is_primary is uniformly True; the primary/side split was removed.)
    seen: dict[tuple[str, int], dict] = {}
    for r in skill_rows:
        key = (r["job_id"], r["skill_id"])
        existing = seen.get(key)
        if not existing:
            seen[key] = r
            continue
        existing["required_level"] = max(existing["required_level"], r["required_level"])
    skill_rows = list(seen.values())

    if dry_run or not skill_rows:
        return len(skill_rows), local_drift

    if not supports_required_level:
        log.error(
            "job_skills.required_level is missing in Supabase. "
            "Run scraper/sql/add_job_skills_required_level.sql before uploading enriched skills."
        )
        raise SystemExit(2)

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


def _sync_baseline_ledger(company: str, jobs: list[dict], raw_jobs: int, run_id: str) -> None:
    """Forward-only sync of the official load count into baseline_ledger.json.

    This is the source of truth for the self-healing diagnostic's regression
    detection: next run, diagnose.py diffs the scrape against this last-good
    count. Only count>0 ever writes (a bad run is the regression signal, not a
    new baseline). Best-effort — never fail an import over the ledger.
    """
    try:
        from datetime import date
        from heal.baseline import load_ledger, save_ledger, update_ledger
        ledger = load_ledger()
        ats = (jobs[0].get("ats", "") if jobs else "") or ""
        if update_ledger(ledger, company, ats, raw_jobs, run_id, updated=date.today().isoformat()):
            save_ledger(ledger)
    except Exception:  # noqa: BLE001 — ledger sync must never break a load
        pass


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


def _fetch_active_jobs_for_company(sb: Client, company: str) -> list[dict]:
    rows: list[dict] = []
    page = 0
    page_size = 1000
    while True:
        batch = (
            sb.table("jobs")
            .select("job_id,job_title,company_name,batch_date,last_seen,is_active")
            .eq("company_name", company)
            .eq("is_active", True)
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        ).data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return rows


def _deactivate_missing_jobs(
    sb: Client,
    *,
    company: str,
    current_job_ids: set[str],
    batch_date: int,
    dry_run: bool,
    allow_large_deactivation: bool,
) -> dict:
    active_rows = _fetch_active_jobs_for_company(sb, company)
    missing = [row for row in active_rows if row.get("job_id") not in current_job_ids]
    missing_rate = (len(missing) / len(active_rows)) if active_rows else 0.0
    result = {
        "company": company,
        "active": len(active_rows),
        "current": len(current_job_ids),
        "missing": len(missing),
        "changed": 0,
        "blocked": False,
        "missing_rate": missing_rate,
    }
    if (
        missing
        and active_rows
        and missing_rate > _MAX_DEACTIVATION_RATE
        and not allow_large_deactivation
    ):
        result["blocked"] = True
        result["reason"] = (
            f"would deactivate {missing_rate:.1%} of active rows; "
            "rerun a full scrape or pass --allow-large-deactivation"
        )
        return result

    if dry_run or not missing:
        return result

    missing_ids = [row["job_id"] for row in missing if row.get("job_id")]
    for i in range(0, len(missing_ids), _BATCH_SIZE):
        chunk = missing_ids[i:i + _BATCH_SIZE]
        sb.table("jobs").update({"is_active": False}).in_("job_id", chunk).execute()

    version_rows = []
    for row in missing:
        old_snapshot = {**row, "is_active": True}
        new_snapshot = {**row, "is_active": False}
        version_rows.append({
            "job_id": row["job_id"],
            "company_name": company,
            "batch_date": batch_date,
            "change_type": "deactivate",
            "changed_fields": ["is_active"],
            "old_snapshot": old_snapshot,
            "new_snapshot": new_snapshot,
        })
    for i in range(0, len(version_rows), _BATCH_SIZE):
        sb.table("job_versions").insert(version_rows[i:i + _BATCH_SIZE]).execute()

    result["changed"] = len(missing)
    return result


def import_file(
    sb: Client,
    json_path: Path,
    skill_id_map: dict[str, int],
    drift_counter: Counter,
    unknown_location_counter: Counter[str],
    dry_run: bool,
    supports_required_level: bool,
    run_id: str = "",
) -> dict:
    try:
        jobs = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"path": str(json_path), "error": str(e)}

    if not isinstance(jobs, list) or not jobs:
        date_str = json_path.parent.name
        return {
            "path": str(json_path),
            "company": json_path.parent.parent.parent.name,
            "date": date_str,
            "batch_date": _parse_batch_date(date_str),
            "job_ids": set(),
            "jobs": 0,
            "skill_rows": 0,
            "drift": 0,
            "enriched": 0,
            "unknown_location_rows": 0,
        }

    company    = jobs[0].get("company_name", json_path.parent.parent.parent.name)
    date_str   = json_path.parent.name
    batch_date = _parse_batch_date(date_str) or _parse_batch_date(jobs[0].get("batch_date"))
    enriched   = sum(1 for j in jobs if j.get("main_skills"))

    local_unknown = 0
    if not dry_run:
        jobs_written, local_unknown = _upsert_jobs(sb, jobs, batch_date, unknown_location_counter)
    else:
        jobs_written = sum(1 for j in jobs if j.get("job_id"))
        for job in jobs:
            normalized = _normalize_location(job.get("location"), job.get("locations"))
            if normalized.location_quality == "unknown":
                local_unknown += 1
                if normalized.location_raw:
                    unknown_location_counter[normalized.location_raw.lower()] += 1

    skill_rows_written, drift = _resolve_and_upsert_skills(
        sb, jobs, skill_id_map, drift_counter, dry_run, supports_required_level
    )

    if not dry_run and run_id:
        _write_diagnostic(sb, run_id, company, len(jobs), jobs_written, enriched, drift)
        _sync_baseline_ledger(company, jobs, len(jobs), run_id)

    return {
        "path": str(json_path),
        "company": company,
        "date": date_str,
        "batch_date": batch_date,
        "job_ids": {j.get("job_id") for j in jobs if j.get("job_id")},
        "jobs": jobs_written,
        "skill_rows": skill_rows_written,
        "drift": drift,
        "enriched": enriched,
        "unknown_location_rows": local_unknown,
    }


# ── Myro intel-page refresh ─────────────────────────────────────────────────--

def _refresh_analytics_snapshot() -> None:
    """Tell the Myro backend to recompute its public intel snapshot after a load.

    Fire-and-forget: never raises, so a refresh failure cannot fail the import.
    Skipped silently if either env var is absent. Sends the secret in a header
    (not the query string) so it does not leak into HTTP access / proxy logs.
    """
    backend_url = (os.getenv("MYRO_BACKEND_URL", "") or "").rstrip("/")
    secret = (os.getenv("MYRO_ANALYTICS_REFRESH_SECRET", "") or "").strip()
    if not backend_url or not secret:
        log.info("Intel refresh skipped: MYRO_BACKEND_URL / MYRO_ANALYTICS_REFRESH_SECRET not set")
        return

    endpoint = f"{backend_url}/jobs/analytics/refresh-snapshot"
    try:
        resp = requests.post(
            endpoint,
            headers={"X-Myro-Refresh-Secret": secret},
            timeout=30,
        )
        if resp.status_code == 200:
            log.info("Intel refresh: backend snapshot refreshed (%s)", endpoint)
        else:
            log.warning(
                "Intel refresh: backend returned %s (%s) — snapshot may be stale",
                resp.status_code,
                endpoint,
            )
    except requests.RequestException as e:
        log.warning("Intel refresh failed (%s): %s — snapshot may be stale", endpoint, e)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3: upload enriched jobs to Supabase")
    parser.add_argument("--company",   help="Filter by company slug (substring, case-insensitive)")
    parser.add_argument("--all-dates", action="store_true", help="Import all date folders, not just latest")
    parser.add_argument("--dry-run",   action="store_true", help="Count only — no writes to Supabase")
    parser.add_argument(
        "--run-date",
        help="With --deactivate-missing, scope decommissioning to one output date (YYYYMMDD, YYYY-MM-DD, or YYYY_MM_DD)",
    )
    parser.add_argument(
        "--deactivate-missing",
        action="store_true",
        help="After a successful import, mark active jobs missing from this run inactive for imported companies only",
    )
    parser.add_argument(
        "--allow-large-deactivation",
        action="store_true",
        help="Allow a company import to deactivate more than 75%% of currently active rows",
    )
    args = parser.parse_args()

    if args.deactivate_missing and args.all_dates:
        log.error("--deactivate-missing is only safe with the latest date folder, not --all-dates")
        raise SystemExit(2)
    if args.deactivate_missing and not args.dry_run and not args.run_date:
        log.error("Real deactivation writes require --run-date YYYYMMDD/YYYY-MM-DD/YYYY_MM_DD")
        raise SystemExit(2)

    sb = _supabase()
    skill_id_map = _build_skill_id_map(sb)

    json_files = _find_json_files(args.company, args.all_dates)
    if not json_files:
        log.warning("No jobs.json files found. Did you run main.py first?")
        return

    deactivation_batch_date = _parse_batch_date(args.run_date)
    if args.deactivate_missing:
        if args.run_date and deactivation_batch_date is None:
            log.error("--run-date must be YYYYMMDD, YYYY-MM-DD, or YYYY_MM_DD")
            raise SystemExit(2)
        available_dates = {
            parsed for parsed in (_parse_batch_date(path.parent.name) for path in json_files)
            if parsed is not None
        }
        if deactivation_batch_date is None and available_dates:
            deactivation_batch_date = max(available_dates)
        if deactivation_batch_date is None:
            log.error("--deactivate-missing requires dated output folders")
            raise SystemExit(2)
        before_count = len(json_files)
        json_files = [
            path for path in json_files
            if _parse_batch_date(path.parent.name) == deactivation_batch_date
        ]
        log.info(
            "Deactivation scoped to run date %s: %s/%s files",
            deactivation_batch_date,
            len(json_files),
            before_count,
        )
        if not json_files:
            log.error("No jobs.json files found for deactivation run date %s", deactivation_batch_date)
            raise SystemExit(2)

    log.info(f"Files to import: {len(json_files)}")
    if args.dry_run:
        log.info("DRY RUN — no writes")

    run_label = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_id = str(uuid.uuid4())
    log.info(f"Run ID: {run_id} ({run_label})")
    _assert_location_audit_contract(run_id)
    supports_required_level = _job_skills_has_required_level()
    if supports_required_level:
        log.info("job_skills.required_level contract OK")
    else:
        log.warning(
            "job_skills.required_level is missing; dry-run can continue, "
            "but real enriched uploads require scraper/sql/add_job_skills_required_level.sql"
        )
        if not args.dry_run:
            log.error("Stopping before writes to avoid a partial jobs-only upload.")
            raise SystemExit(2)

    if _jobs_has_locations_column():
        log.info("jobs.locations[] contract OK")
    else:
        log.warning(
            "jobs.locations[] column is missing; dry-run can continue, "
            "but real uploads require scraper/sql/add_jobs_locations_array.sql"
        )
        if not args.dry_run:
            log.error(
                "Stopping before writes: _upsert_jobs sends locations[] on every row, "
                "so the upsert would fail. Run scraper/sql/add_jobs_locations_array.sql "
                "in the Supabase SQL editor first."
            )
            raise SystemExit(2)

    _missing_card_cols = _jobs_missing_card_columns()
    if not _missing_card_cols:
        log.info("jobs card columns (job_summary + chips) contract OK")
    else:
        log.warning(
            "jobs is missing card columns %s; dry-run can continue, "
            "but real uploads require scraper/sql/add_jobs_summary_cols.sql",
            ", ".join(_missing_card_cols),
        )
        if not args.dry_run:
            log.error(
                "Stopping before writes: _upsert_jobs sends %s on every row, "
                "so the upsert would fail. Run scraper/sql/add_jobs_summary_cols.sql "
                "in the Supabase SQL editor first.",
                ", ".join(_missing_card_cols),
            )
            raise SystemExit(2)

    drift_counter: Counter = Counter()
    unknown_location_counter: Counter[str] = Counter()
    imported_company_job_ids: dict[str, set[str]] = {}
    imported_company_batch_dates: dict[str, int] = {}
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
            supports_required_level,
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
        if result.get("company") and result.get("jobs"):
            company = result["company"]
            imported_company_job_ids.setdefault(company, set()).update(result.get("job_ids", set()))
            if result.get("batch_date"):
                imported_company_batch_dates[company] = result["batch_date"]

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

    total_missing = total_deactivated = blocked_deactivation = 0
    if args.deactivate_missing:
        if status == "blocked":
            log.error("Skipping deactivation because the import quality gate is blocked.")
        else:
            for company, job_ids in sorted(imported_company_job_ids.items()):
                batch_date = imported_company_batch_dates.get(company) or int(datetime.now().strftime("%Y%m%d"))
                result = _deactivate_missing_jobs(
                    sb,
                    company=company,
                    current_job_ids=job_ids,
                    batch_date=batch_date,
                    dry_run=args.dry_run,
                    allow_large_deactivation=args.allow_large_deactivation,
                )
                total_missing += result["missing"]
                total_deactivated += result["changed"]
                if result["blocked"]:
                    blocked_deactivation += 1
                    log.error(
                        "  %s: deactivation blocked — %s active, %s current, %s missing (%s)",
                        company,
                        result["active"],
                        result["current"],
                        result["missing"],
                        result.get("reason"),
                    )
                elif args.dry_run:
                    log.info(
                        "  %s: would deactivate %s missing active jobs (%s active, %s current)",
                        company,
                        result["missing"],
                        result["active"],
                        result["current"],
                    )
                else:
                    log.info(
                        "  %s: deactivated %s missing active jobs (%s active, %s current)",
                        company,
                        result["changed"],
                        result["active"],
                        result["current"],
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

    if args.deactivate_missing:
        action = "would deactivate" if args.dry_run else "deactivated"
        count = total_missing if args.dry_run else total_deactivated
        log.info("Decommissioning: %s %s missing jobs across imported companies", action, count)
        if blocked_deactivation:
            log.error("Decommissioning blocked for %s companies; no inactive writes were made for those companies.", blocked_deactivation)

    if status == "blocked" or blocked_deactivation:
        raise SystemExit(2)

    # Clean, real load only — tell the Myro intel page to refresh its snapshot.
    if not args.dry_run:
        _refresh_analytics_snapshot()


if __name__ == "__main__":
    main()
