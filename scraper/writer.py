"""
Normalize raw scraper dicts to the 10-field canonical schema and
persist to All_CSV_Outputs/{Company}/Outputs/YYYY_MM_DD/jobs.json (+ CSV).

Schema (v2, Dump 4+):
  job_id, job_title, job_description,
  industry, role_domain,          ← static from portal / LLM-derived
  company_name, apply_url,
  main_skills, side_skills,       ← LLM-derived
  batch_date                      ← auto-stamped integer YYYYMMDD
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

def _today() -> int:
    return int(datetime.now().strftime("%Y%m%d"))


def to_canonical(raw: dict, company_name: str) -> dict:
    """Map raw scraper dict to canonical schema using RAW_FIELD_MAP for renames."""
    def _get(raw_key: str, canonical_key: str, default=''):
        # Try canonical key first (already-mapped field), then raw key alias
        return raw.get(canonical_key) or raw.get(raw_key) or default

    return {
        "job_id":          raw.get('job_id') or '',
        "job_title":       _get('title', 'job_title'),
        "job_description": _get('raw_jd_text', 'job_description'),
        "industry":        raw.get('industry') or '',
        "company_name":    company_name,
        "location":        _get('location_city', 'location') or raw.get('Location') or 'India',
        "apply_url":       _get('job_url', 'apply_url'),
        "main_skills":     raw.get('main_skills') or [],
        "side_skills":     raw.get('side_skills') or [],
        "batch_date":      _today(),
    }


def save_jobs(company_name: str, jobs: list[dict], write_csv: bool = True, output_base: str = OUTPUT_BASE) -> tuple[str, int]:
    """
    Write jobs to All_CSV_Outputs/{Company}/Outputs/YYYY_MM_DD/jobs.json.
    Deduplicates by job_id within the same date folder.
    Returns (json_path, new_jobs_count).
    """
    folder = (
        Path(output_base)
        / company_slug(company_name)
        / "Outputs"
        / datetime.now().strftime("%Y_%m_%d")
    )
    folder.mkdir(parents=True, exist_ok=True)
    json_path = folder / "jobs.json"

    existing: list[dict] = []
    if json_path.exists():
        try:
            existing = json.loads(json_path.read_text(encoding='utf-8'))
        except Exception:
            existing = []

    existing_ids = {j['job_id'] for j in existing if j.get('job_id')}
    new_jobs     = [j for j in jobs if j.get('job_id') not in existing_ids]
    all_jobs     = existing + new_jobs

    json_path.write_text(
        json.dumps(all_jobs, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

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

    return str(json_path), len(new_jobs)
