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
from datetime import datetime
from pathlib import Path
from utils import company_slug
from config import OUTPUT_BASE
from schema import CANONICAL_FIELDS, RAW_FIELD_MAP

# SCHEMA kept as alias for backward-compat imports (e.g. main.py: from writer import SCHEMA)
SCHEMA = CANONICAL_FIELDS

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


def to_canonical(raw: dict, company_name: str) -> dict:
    """Map raw scraper dict to canonical schema using RAW_FIELD_MAP for renames."""
    def _get(raw_key: str, canonical_key: str, default=''):
        # Try canonical key first (already-mapped field), then raw key alias
        return raw.get(canonical_key) or raw.get(raw_key) or default

    location = _get('location_city', 'location') or raw.get('Location') or raw.get('location_raw') or 'India'

    row = {
        "job_id":           raw.get('job_id') or '',
        "job_title":        _get('title', 'job_title'),
        "job_description":  _get('raw_jd_text', 'job_description'),
        "industry":         raw.get('industry') or '',
        "industry_group":   raw.get('industry_group') or '',
        "company_name":     company_name,
        "location":         location,
        "location_raw":     raw.get('location_raw') or location,
        "location_city":    raw.get('location_city') or location,
        "location_country": raw.get('location_country') or ('India' if location else ''),
        "location_mode":    raw.get('location_mode') or '',
        "location_quality": raw.get('location_quality') or '',
        "apply_url":        _get('job_url', 'apply_url'),
        "role_domain":      raw.get('role_domain') or raw.get('business_unit') or '',
        "main_skills":      raw.get('main_skills') or [],
        "side_skills":      raw.get('side_skills') or [],
        "batch_date":       raw.get('batch_date') or _today(),
    }
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
    all_jobs     = existing + new_jobs

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
                row['main_skills'] = ', '.join(job.get('main_skills') or [])
                row['side_skills'] = ', '.join(job.get('side_skills') or [])
                w.writerow(row)

    # Marker written only after BOTH JSON and CSV succeed (skipped for page-level saves)
    if write_marker:
        write_complete_marker(folder, len(all_jobs), len(new_jobs), run_id=run_id)

    return str(json_path), len(new_jobs)
