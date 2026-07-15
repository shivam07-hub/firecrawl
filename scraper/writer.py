"""
Normalize raw scraper dicts to the 10-field canonical schema and
persist to All_CSV_Outputs/{Company}/Outputs/YYYY_MM_DD/jobs.json (+ CSV).

Schema (v2, Dump 4+):
  job_id, job_title, job_description,
  industry, role_domain,          ← static from portal / LLM-derived
  company_name, apply_url,
  main_skills, side_skills,       ← LLM-derived
  batch_date                      ← auto-stamped integer YYYYMMDD

Completion contract:
  jobs.complete is written ONLY after both jobs.json and jobs.csv succeed.
  already_scraped() in main.py uses this marker as the canonical signal.
  Legacy runs (no marker) are detected via date-folder comparison.
"""
import json
import csv
import hashlib
from datetime import datetime
from pathlib import Path
from utils import company_slug
from config import OUTPUT_BASE
from job_seniority import normalize_job_seniority
from schema import CANONICAL_FIELDS, RAW_FIELD_MAP, MIN_JOB_DESCRIPTION_LEN, MISSING_JD_NOTE

# SCHEMA kept as alias for backward-compat imports (e.g. main.py: from writer import SCHEMA)
SCHEMA = CANONICAL_FIELDS


def _skills_to_csv(skills) -> str:
    """Serialize the structured skills list to a human-readable CSV cell: 'name:level | …'.
    JSON remains the importer's source of truth; this is only for the human-facing CSV."""
    out = []
    for s in skills or []:
        if isinstance(s, dict) and s.get('name'):
            out.append(f"{s['name']}:{s.get('required_level', 2)}")
    return ' | '.join(out)

COMPLETE_MARKER_NAME = "jobs.complete"


def write_complete_marker(folder: Path, job_count: int, new_count: int, run_id: str = "") -> None:
    """Write jobs.complete after both JSON and CSV are confirmed written."""
    payload: dict = {
        "completed_at": datetime.now().isoformat(),
        "job_count":    job_count,
        "new_jobs":     new_count,
    }
    if run_id:
        payload["run_id"] = run_id
    (folder / COMPLETE_MARKER_NAME).write_text(json.dumps(payload), encoding='utf-8')

def _today() -> int:
    return int(datetime.now().strftime("%Y%m%d"))


def job_content_hash(job: dict) -> str:
    """Stable signal for re-embedding when JD/title/skills materially change."""
    skills = job.get("main_skills") or []
    if not isinstance(skills, list):
        skills = [str(skills)] if skills else []
    payload = {
        "job_title": str(job.get("job_title") or "").strip(),
        "job_description": str(job.get("job_description") or "").strip(),
        "main_skills": [str(skill).strip() for skill in skills if str(skill or "").strip()],
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def stamp_job_content_hash(job: dict) -> dict:
    job["job_content_hash"] = job_content_hash(job)
    return job


def to_canonical(raw: dict, company_name: str) -> dict:
    """Map raw scraper dict to canonical schema using RAW_FIELD_MAP for renames."""
    def _get(raw_key: str, canonical_key: str, default=''):
        # Try canonical key first (already-mapped field), then raw key alias
        return raw.get(canonical_key) or raw.get(raw_key) or default

    location = _get('location_city', 'location') or raw.get('Location') or raw.get('location_raw') or 'India'
    source_job_description = _get('raw_jd_text', 'job_description')
    job_description = source_job_description
    metadata_only = len(str(source_job_description or '').strip()) < MIN_JOB_DESCRIPTION_LEN
    if metadata_only:
        job_description = MISSING_JD_NOTE
    normalized_seniority = normalize_job_seniority({
        **raw,
        "job_title": _get('title', 'job_title'),
        # The card may hide a short JD, but its source text can still contain
        # a deterministic experience requirement such as "12+ years".
        "job_description": source_job_description,
    })

    row = {
        "job_id":           raw.get('job_id') or '',
        "job_title":        _get('title', 'job_title'),
        "job_description":  job_description,
        "job_summary":      MISSING_JD_NOTE if metadata_only else (raw.get('job_summary') or ''),
        "industry":         raw.get('industry') or '',
        "industry_group":   raw.get('industry_group') or '',
        "company_name":     company_name,
        "location":         location,
        "location_raw":     raw.get('location_raw') or location,
        "location_city":    raw.get('location_city') or location,
        "location_country": raw.get('location_country') or ('India' if location else ''),
        "location_mode":    raw.get('location_mode') or '',
        "location_quality": raw.get('location_quality') or '',
        # per-city raw strings for multi-location postings (firecrawl #6).
        # csv_importer._normalize_location canonicalizes; empty list → derived from scalar.
        "locations":        [l for l in (raw.get('locations') or []) if isinstance(l, str) and l.strip()],
        "apply_url":        _get('job_url', 'apply_url'),
        "source_url":       raw.get('source_url') or raw.get('source_api_url') or '',
        "source_platform":  raw.get('source_platform') or raw.get('ats') or '',
        "ingestion_source": raw.get('ingestion_source') or 'scraper',
        "quality_status":   raw.get('quality_status') or 'auto_extracted',
        "role_domain":      raw.get('role_domain') or raw.get('business_unit') or '',
        # One flat skill list. `skills` carries model required_level → job_skills;
        # `main_skills` mirrors the names (True_Yodha chips); `side_skills` always [].
        "skills":           raw.get('skills') or [],
        "main_skills":      raw.get('main_skills') or [],
        "side_skills":      [],
        "candidate_profile":        raw.get('candidate_profile') or {},
        "candidate_profile_version": raw.get('candidate_profile_version') or '',
        "candidate_profile_hash":    raw.get('candidate_profile_hash') or '',
        "candidate_profile_model":   raw.get('candidate_profile_model') or '',
        "job_content_hash":          raw.get('job_content_hash') or '',
        # Structured source facts. Seniority is normalized deterministically from
        # provider metadata, title, and JD during the forward scrape; no LLM pass.
        "date_posted":            raw.get('date_posted') or raw.get('date_posted_raw') or '',
        "seniority_level":        normalized_seniority.seniority_level,
        "work_mode":              raw.get('work_mode') or '',
        "min_years_experience":   normalized_seniority.min_years_experience if normalized_seniority.min_years_experience is not None else '',
        "max_years_experience":   normalized_seniority.max_years_experience if normalized_seniority.max_years_experience is not None else '',
        "batch_date":       raw.get('batch_date') or _today(),
    }
    row["job_content_hash"] = row.get("job_content_hash") or job_content_hash(row)
    return {field: row.get(field, '') for field in CANONICAL_FIELDS}


def save_jobs(
    company_name: str,
    jobs: list[dict],
    write_csv: bool = True,
    output_base: str = OUTPUT_BASE,
    write_marker: bool = True,
    run_id: str = "",
) -> tuple[str, int]:
    """
    Write jobs to All_CSV_Outputs/{Company}/Outputs/YYYY_MM_DD/jobs.json (+ CSV).
    Deduplicates by job_id within the same date folder.
    write_marker=True (default): writes jobs.complete after both JSON and CSV succeed.
    write_marker=False: intermediate/page-level save — no marker (run still in progress).
    Returns (json_path, new_jobs_count).
    """
    folder = (
        Path(output_base)
        / company_slug(company_name)
        / "Outputs"
        / datetime.now().strftime("%Y_%m_%d")
    )
    folder.mkdir(parents=True, exist_ok=True)
    json_path      = folder / "jobs.json"
    tmp_path       = folder / "jobs.tmp.json"
    complete_marker = folder / COMPLETE_MARKER_NAME

    # Remove stale marker — this save is in progress
    if complete_marker.exists():
        complete_marker.unlink()

    existing: list[dict] = []
    if json_path.exists():
        try:
            existing = json.loads(json_path.read_text(encoding='utf-8'))
        except Exception:
            existing = []

    existing_ids = {j['job_id'] for j in existing if j.get('job_id')}
    new_jobs     = [j for j in jobs if j.get('job_id') not in existing_ids]
    all_jobs     = [stamp_job_content_hash(j) for j in (existing + new_jobs)]

    # Atomic JSON write: tmp → rename (POSIX atomic)
    tmp_path.write_text(json.dumps(all_jobs, indent=2, ensure_ascii=False), encoding='utf-8')
    tmp_path.rename(json_path)

    if write_csv and all_jobs:
        csv_path = folder / "jobs.csv"
        with csv_path.open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=SCHEMA, extrasaction='ignore')
            w.writeheader()
            for job in all_jobs:
                row = dict(job)
                row['skills'] = _skills_to_csv(job.get('skills'))
                row['main_skills'] = ', '.join(job.get('main_skills') or [])
                row['side_skills'] = ''
                row['locations'] = ' | '.join(job.get('locations') or [])
                w.writerow(row)

    # Marker written only after BOTH JSON and CSV succeed (skipped for page-level saves)
    if write_marker:
        write_complete_marker(folder, len(all_jobs), len(new_jobs), run_id=run_id)

    return str(json_path), len(new_jobs)
