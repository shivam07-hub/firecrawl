from __future__ import annotations

"""Oracle Taleo Business Edition (TBE) provider.

Pattern: POST https://{careers_domain}/services/jobs/search/
Body: {"keywords":"","locationsearch":"india","recordsperpage":N,"startrow":0,"filterquery":{}}
Response: {"jobList": [{id, title, city, country, urltitle, referencedate, ...}]}
JD: fetched from individual HTML page https://{domain}/job/{urltitle}/{id}/

No auth required. JSESSIONID set automatically on first request.
"""

import logging
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT
from providers.base import ProviderResult, ScrapeReason
from schema import Portal
from utils import is_india, strip_html

_log = logging.getLogger("mirror")
_PAGE_SIZE = 100

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}


class TaleoProvider:
    key = "taleo"

    def scrape(
        self,
        portal: Portal,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        # Detect v1 REST API (StanChart pattern) vs classic Taleo TBE
        if portal.get("taleo_v1") or "/recruiting/v1/" in portal.get("endpoint", ""):
            jobs = _scrape_taleo_v1(portal, max_jobs=max_jobs)
        else:
            jobs = _scrape_taleo(portal, max_jobs=max_jobs)
        if jobs is None:
            return ProviderResult.error(ScrapeReason.API_BLOCKED)
        return ProviderResult.success(jobs)


def _scrape_taleo(portal: Portal, max_jobs: int | None = None) -> list[dict] | None:
    careers_url = portal.get("careers_url", portal.get("endpoint", ""))
    parsed = urlparse(careers_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    search_url = f"{base}/services/jobs/search/"
    india_only = portal.get("india_only", True)

    session = requests.Session()
    session.headers.update(_HEADERS)

    body = {
        "keywords": "",
        "locationsearch": "india" if india_only else "",
        "recordsperpage": _PAGE_SIZE,
        "startrow": 0,
        "filterquery": {},
        "sortby": "referencedate",
        "sortdir": "desc",
    }
    try:
        r = session.post(search_url, json=body, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        _log.error(f"    [ERROR] Taleo {portal['company']}: {e}")
        return None

    listings = data.get("jobList", [])
    jobs: list[dict] = []

    for item in listings:
        title = (item.get("title") or "").strip()
        if not title:
            continue

        city = item.get("city") or ""
        country = item.get("country") or ""
        loc = f"{city}, {country}".strip(", ")

        if india_only and not is_india(loc):
            continue

        jid = str(item.get("id") or "")
        urltitle = item.get("urltitle") or jid
        apply_url = f"{base}/job/{urltitle}/{jid}/"

        raw_jd = _fetch_jd(session, apply_url)

        jobs.append({
            "job_id":          jid,
            "title":           title,
            "job_url":         apply_url,
            "source_api_url":  search_url,
            "business_unit":   item.get("department") or item.get("facility"),
            "raw_jd_text":     raw_jd,
            "location_city":   loc,
            "date_posted":     item.get("referencedate"),
            "source_platform": "Taleo",
            "industry":        portal.get("industry", ""),
        })

        if max_jobs and len(jobs) >= max_jobs:
            break

    _log.info(f"    {len(jobs)} India jobs via Taleo ({portal['company']})")
    return jobs


def _scrape_taleo_v1(portal: Portal, max_jobs: int | None = None) -> list[dict] | None:
    """Taleo Enterprise v1 REST API — used by Standard Chartered and similar.
    POST /services/recruiting/v1/jobs → jobSearchResult[].response
    Pagination via pageNumber (0-indexed, 10 results/page default).
    """
    endpoint = portal.get("endpoint", "")
    parsed = urlparse(endpoint)
    base = f"{parsed.scheme}://{parsed.netloc}"
    india_only = portal.get("india_only", True)

    session = requests.Session()
    session.headers.update(_HEADERS)

    jobs: list[dict] = []
    page = 0

    while True:
        body = {
            "locale": "en_GB",
            "pageNumber": page,
            "sortBy": "",
            "keywords": "india" if india_only else "",
            "location": "",
            "facetFilters": {},
            "brand": "",
            "skills": [],
            "categoryId": 0,
            "alertId": "",
            "rcmCandidateId": "",
        }
        try:
            r = session.post(endpoint, json=body, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            _log.error(f"    [ERROR] Taleo v1 {portal['company']}: {e}")
            return None

        results = data.get("jobSearchResult", [])
        if not results:
            break

        for item in results:
            resp = item.get("response", item)
            title = (resp.get("unifiedStandardTitle") or "").strip()
            if not title:
                continue

            locs = resp.get("jobLocationShort") or []
            countries = resp.get("jobLocationCountry") or []
            loc = (locs[0] if locs else "") or (countries[0] if countries else "")

            if india_only and not is_india(loc):
                continue

            jid = str(resp.get("id") or "")
            urltitle = resp.get("unifiedUrlTitle") or jid
            apply_url = f"{base}/job/{urltitle}/{jid}/" if jid else ""

            raw_jd = _fetch_jd(session, apply_url) if apply_url else ""

            jobs.append({
                "job_id":          jid,
                "title":           title,
                "job_url":         apply_url,
                "source_api_url":  endpoint,
                "business_unit":   (resp.get("mfield1") or [None])[0],
                "raw_jd_text":     raw_jd,
                "location_city":   loc,
                "date_posted":     resp.get("unifiedStandardStart"),
                "source_platform": "TaleoV1",
                "industry":        portal.get("industry", ""),
            })

            if max_jobs and len(jobs) >= max_jobs:
                _log.info(f"    {len(jobs)} India jobs via Taleo v1 ({portal['company']})")
                return jobs

        total = data.get("totalJobs", 0)
        if len(jobs) >= total or len(results) < 10:
            break
        page += 1

    _log.info(f"    {len(jobs)} India jobs via Taleo v1 ({portal['company']})")
    return jobs


def _fetch_jd(session: requests.Session, job_url: str) -> str:
    try:
        r = session.get(job_url, headers={"Accept": "text/html"}, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except Exception:
        return ""

    soup = BeautifulSoup(r.text, "html.parser")
    # Remove scripts/styles
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    # Look for largest meaningful text block
    candidates = []
    for tag in soup.find_all(["div", "section", "article"]):
        text = tag.get_text(separator=" ", strip=True)
        if len(text) > 200:
            candidates.append(text)

    if not candidates:
        return strip_html(r.text)

    # Return the longest candidate (most likely the JD)
    return max(candidates, key=len)[:8000]
