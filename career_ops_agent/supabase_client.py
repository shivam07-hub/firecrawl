"""
Supabase reader for Career Ops — talks to the live firecrawl_Supabase `jobs` table
via PostgREST (plain HTTPS, requests only). No supabase-py dependency.

Live schema (canonical, see firecrawl_Supabase/scraper/schema.py):
  jobs: job_id, job_title, job_description, industry, company_name, location,
        apply_url, role_domain, main_skills[], side_skills[], batch_date,
        is_active, location_city, location_country, ...
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

import config

_SELECT = (
    "job_id,job_title,job_description,company_name,industry,location,"
    "location_city,location_country,apply_url,role_domain,main_skills,"
    "side_skills,batch_date,is_active"
)


def _headers() -> dict[str, str]:
    return {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
        "Accept": "application/json",
    }


def fetch_jobs(
    *,
    batch_date: int | None = None,
    active_only: bool = True,
    limit: int = 5000,
) -> list[dict[str, Any]]:
    """Page through PostgREST and return job rows as dicts."""
    base = f"{config.SUPABASE_URL}/rest/v1/jobs"
    filters = [f"select={_SELECT}"]
    if active_only:
        filters.append("is_active=eq.true")
    if batch_date is not None:
        filters.append(f"batch_date=eq.{batch_date}")

    rows: list[dict[str, Any]] = []
    page = 1000
    offset = 0
    while offset < limit:
        url = base + "?" + "&".join(filters) + f"&limit={page}&offset={offset}"
        resp = requests.get(url, headers=_headers(), timeout=60)
        resp.raise_for_status()
        batch = resp.json()
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return rows[:limit]


def fetch_companies(jobs: list[dict[str, Any]]) -> dict[str, int]:
    """Job count per company, for quick situational awareness."""
    counts: dict[str, int] = {}
    for j in jobs:
        c = j.get("company_name") or "Unknown"
        counts[c] = counts.get(c, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
