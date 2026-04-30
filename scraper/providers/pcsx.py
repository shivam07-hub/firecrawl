from __future__ import annotations

"""Phenom CX (pcsx) ATS provider.

Two-step fetch:
  1. GET {base}/api/pcsx/search?domain={domain}&query=&location=india&start={N}
     Returns {data: {positions: [...], count: N}} — 10 jobs/page
  2. GET {base}/careers/job/{id} → parse JSON-LD <script type="application/ld+json">
     Extracts full JD (~6000 chars) server-side rendered, no JS needed

Portal config keys:
  endpoint     str   base URL e.g. https://careers.haleon.com
  pcsx_domain  str   domain param e.g. haleon.com
"""

import json
import logging
import re

import requests

from config import REQUEST_TIMEOUT
from providers.base import ProviderResult, ScrapeReason
from schema import Portal
from utils import job_hash, strip_html

_log = logging.getLogger("mirror")
_PAGE_SIZE = 10

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


class PCSXProvider:
    """Phenom CX (pcsx) — paginated list API + per-job HTML JSON-LD for full JD."""
    key = "pcsx"

    def scrape(
        self,
        portal: Portal,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        jobs = _scrape_pcsx(portal, max_jobs=max_jobs)
        if jobs is None:
            return ProviderResult.error(ScrapeReason.API_BLOCKED)
        return ProviderResult.success(jobs)


def _fetch_jd(base: str, job_id: str) -> str:
    """Fetch job HTML page and extract JD from JSON-LD JobPosting schema."""
    url = f"{base}/careers/job/{job_id}"
    try:
        r = requests.get(url, headers={**_HEADERS, "Accept": "text/html"}, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return ""
        m = re.search(
            r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
            r.text, re.DOTALL
        )
        if not m:
            return ""
        ld = json.loads(m.group(1))
        return strip_html(ld.get("description", ""))
    except Exception:
        return ""


def _scrape_pcsx(portal: Portal, max_jobs: int | None = None) -> list[dict] | None:
    base = portal.get("endpoint", "").rstrip("/")
    domain = portal.get("pcsx_domain", "")
    company = portal["company"]
    cap = max_jobs or 2000

    jobs: list[dict] = []
    start = 0

    while True:
        params = {
            "domain": domain,
            "query": "",
            "location": "india",
            "start": start,
        }
        try:
            r = requests.get(
                f"{base}/api/pcsx/search",
                params=params,
                headers=_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            _log.error(f"    [ERROR] PCSX {company} start={start}: {e}")
            return jobs or None

        positions = data.get("data", {}).get("positions", [])
        total = data.get("data", {}).get("count", 0)

        if not positions:
            break

        for p in positions:
            job_id = str(p.get("id") or "")
            if not job_id:
                continue
            title = (p.get("name") or "").strip()
            if not title:
                continue

            locs = p.get("locations") or p.get("standardizedLocations") or []
            loc = locs[0] if locs else ""
            if isinstance(loc, str):
                # strip ATS prefix e.g. "Field Worker- IND Cx_MumbaiRSO, Mumbai, ..."
                loc = loc.split(",")[-3].strip() if loc.count(",") >= 2 else loc

            jd = _fetch_jd(base, job_id)
            apply_url = f"{base}{p.get('positionUrl', f'/careers/job/{job_id}')}"

            jobs.append({
                "job_id":          job_id,
                "title":           title,
                "job_url":         apply_url,
                "source_api_url":  f"{base}/api/pcsx/search",
                "business_unit":   p.get("department"),
                "raw_jd_text":     jd,
                "location_city":   loc,
                "date_posted":     str(p.get("postedTs", "")),
                "source_platform": "PhenomCX",
                "industry":        portal.get("industry", ""),
            })

            if len(jobs) >= cap:
                break

        if len(jobs) >= cap or start + _PAGE_SIZE >= total:
            break
        start += _PAGE_SIZE

    _log.info(f"    {len(jobs)} India jobs fetched via PCSX ({company})")
    return jobs
