from __future__ import annotations

from schema import Portal

import json
import logging
import requests
from pathlib import Path

from config import REQUEST_TIMEOUT
from providers.base import FALLBACK_FIRECRAWL_EXTRACT, ProviderResult, ScrapeReason
from utils import is_india, job_hash, strip_html

_log = logging.getLogger("mirror")
_GENERIC_REGISTRY_PATH = Path(__file__).parent.parent / "generic_registry.json"
_generic_registry: dict | None = None


def _load_generic_registry() -> dict:
    global _generic_registry
    if _generic_registry is None:
        if _GENERIC_REGISTRY_PATH.exists():
            try:
                _generic_registry = json.loads(_GENERIC_REGISTRY_PATH.read_text(encoding="utf-8"))
            except Exception:
                _generic_registry = {}
        else:
            _generic_registry = {}
    return _generic_registry


def _persist_field_map(company: str, field_map: dict) -> None:
    """Persist which JSON keys worked for this company — next run uses registry directly."""
    reg = _load_generic_registry()
    if company in reg:
        return  # already known
    reg[company] = field_map
    try:
        _GENERIC_REGISTRY_PATH.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
        _log.info(f"    [REGISTRY] Persisted field map for {company}: {field_map}")
    except Exception as e:
        _log.warning(f"    [REGISTRY] Failed to persist field map for {company}: {e}")

_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type":    "application/json",
}


class GenericJSONProvider:
    key = "generic_json"

    def scrape(
        self,
        portal: Portal,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        raw = scrape_get(portal, max_jobs=max_jobs)

        # Oracle HCM REST is auth-gated — 400 or empty both mean fall to careers_url
        if (raw is None or not raw) and portal.get("ats") == "oracle" and portal.get("careers_url"):
            fc_portal = {**portal, "endpoint": portal["careers_url"]}
            return ProviderResult.fallback(
                policy=FALLBACK_FIRECRAWL_EXTRACT,
                reason="oracle_api_empty_fallback_careers_url",
                portal=fc_portal,
            )

        if raw is None:
            return ProviderResult.error(ScrapeReason.API_BLOCKED)

        if raw and raw[0].get("_needs_firecrawl"):
            return ProviderResult.fallback(
                policy=FALLBACK_FIRECRAWL_EXTRACT,
                reason="generic_get_requires_firecrawl",
                portal=portal,
            )

        return ProviderResult.success(raw)


def scrape_get(portal: Portal, max_jobs: int | None = None) -> list[dict] | None:
    """Best-effort GET-based scraper for Amazon, Microsoft, Apple, SAP, etc.
    Returns None on hard request error (caller maps to ScrapeReason.API_BLOCKED).
    Returns [] with _needs_firecrawl sentinel when HTML detected.
    """
    url = portal['endpoint']
    if not url.startswith('http'):
        _log.warning(f"    [SKIP] {portal['company']}: endpoint not a URL")
        return None

    try:
        r = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        _log.error(f"    [ERROR] GET {portal['company']}: {e}")
        return None

    ct = r.headers.get('Content-Type', '')
    if 'json' in ct or r.text.lstrip().startswith(('{', '[')):
        try:
            return _parse_json_response(r.json(), portal, url, max_jobs=max_jobs)
        except Exception:
            pass

    return [{'_needs_firecrawl': True, '_url': url, '_company': portal['company'],
             '_platform': portal.get('ats', 'Custom')}]


_ITEMS_KEYS = ['jobPostings', 'jobs', 'results', 'data']


def _parse_json_response(data, portal: Portal, source_url: str, max_jobs: int | None = None) -> list[dict]:
    """Walk common JSON structures to extract job listings.
    Checks generic_registry.json first — skips discovery for known companies.
    Persists successful key-path after first discovery so next run is instant.
    """
    platform = portal.get('ats', 'Custom').title()
    company = portal.get('company', '')

    # Registry fast-path: use known key if available
    reg = _load_generic_registry().get(company, {})
    items_key = reg.get('items_key')
    if items_key:
        items = data.get(items_key) if items_key != '__list__' else (data if isinstance(data, list) else [])
    else:
        # Discovery: try each key in order
        items = None
        discovered_key = None
        for k in _ITEMS_KEYS:
            v = data.get(k)
            if isinstance(v, list) and v:
                items = v
                discovered_key = k
                break
        if items is None:
            if isinstance(data, list) and data:
                items = data
                discovered_key = '__list__'
            else:
                items = []
        if discovered_key and company:
            _persist_field_map(company, {'items_key': discovered_key})

    if not isinstance(items, list):
        return []

    jobs = []
    for p in items:
        if not isinstance(p, dict):
            continue

        title = p.get('title') or p.get('name') or p.get('jobTitle') or ''
        if not title:
            continue

        raw_loc = (
            p.get('normalized_location') or p.get('location') or
            p.get('city') or p.get('country') or ''
        )
        loc = raw_loc if isinstance(raw_loc, str) else (
            raw_loc.get('city') or raw_loc.get('name') or ''
        )

        india_only = portal.get('india_only', True)
        if india_only and not is_india(loc):
            continue

        raw_jd = strip_html(
            p.get('description') or p.get('jobDescription') or
            p.get('content') or p.get('summary') or ''
        )
        job_path = p.get('job_path', '')
        job_url = (
            p.get('url') or p.get('job_url') or p.get('absolute_url') or
            p.get('ref') or
            (f"https://www.amazon.jobs{job_path}" if job_path else '') or ''
        )
        jid = str(
            p.get('id_icims') or p.get('id') or p.get('jobId') or
            job_hash(title, job_url)
        )
        bu = (
            p.get('business_category') or p.get('department') or
            p.get('team') or p.get('category')
        )
        if isinstance(bu, dict):
            bu = bu.get('label') or bu.get('name')

        jobs.append({
            'job_id':          jid,
            'title':           title,
            'job_url':         job_url,
            'source_api_url':  source_url,
            'business_unit':   bu,
            'raw_jd_text':     raw_jd,
            'location_city':   loc,
            'date_posted':     (
                p.get('posted_date') or p.get('date_posted') or
                p.get('updated_at') or p.get('releasedDate')
            ),
            'source_platform': platform,
            'industry':        portal.get('industry', ''),
        })
        if max_jobs and len(jobs) >= max_jobs:
            break
    return jobs
