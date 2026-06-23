from __future__ import annotations

"""Zwayam ATS provider (used by Rakuten India via openings.co).

Pattern: POST https://apic2.zwayam.com/jobs/search (multipart/form-data)
Fields: filterCri (JSON), domain, companyId (base64)
Response: data.data[] ES hits with _source containing job fields
Fields: jobTitle, location (str), id, shortDescription, jobUrl (slug)
Apply URL: https://{domain}/job/{jobUrl}
"""

import json
import logging
from urllib.parse import urlparse

import requests

from config import REQUEST_TIMEOUT
from providers._paginate import Page, paginate
from providers.base import ProviderResult, ScrapeReason
from schema import Portal
from utils import is_india, strip_html

_log = logging.getLogger("mirror")
_DEFAULT_API_URL = "https://apic2.zwayam.com/jobs/search"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


class ZwayamProvider:
    key = "zwayam"

    def scrape(
        self,
        portal: Portal,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        jobs = _scrape_zwayam(portal, max_jobs=max_jobs)
        if jobs is None:
            return ProviderResult.error(ScrapeReason.API_BLOCKED)
        return ProviderResult.success(jobs)


def _scrape_zwayam(portal: Portal, max_jobs: int | None = None) -> list[dict] | None:
    careers_url = portal.get("careers_url", portal.get("endpoint", ""))
    parsed = urlparse(careers_url)
    domain = portal.get("zwayam_domain") or parsed.netloc
    company_id = portal.get("zwayam_company_id", "")
    india_only = portal.get("india_only", True)
    api_url = portal.get("zwayam_api_url") or _DEFAULT_API_URL

    if not company_id:
        _log.error(f"    [Zwayam] {portal['company']}: missing zwayam_company_id")
        return None

    headers = {
        **_HEADERS,
        "Origin": f"{parsed.scheme}://{domain}",
        "Referer": f"{parsed.scheme}://{domain}/",
    }

    jobs: list[dict] = []
    state = {"error_first": False}

    # paginationStartNo is a record OFFSET; Zwayam returns a small, variable page
    # and signals continuation via hasMoreData + totalCount. The shared paginator
    # owns the stop decision (advance by len, stop on total/has_more) — this is
    # what the old fixed `< 50` stop got wrong (Persistent 300->2 truncation).
    def fetch_page(offset: int) -> Page | None:
        filter_cri = {
            "paginationStartNo": offset,
            "selectedCall": "sort",
            "sortCriteria": {"name": "modifiedDate", "isAscending": False},
            "anyOfTheseWords": "",
        }
        files = {
            "filterCri": (None, json.dumps(filter_cri)),
            "domain":    (None, domain),
            "companyId": (None, company_id),
        }
        try:
            r = requests.post(api_url, headers=headers, files=files, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            inner = (r.json().get("data") or {})
        except Exception as e:
            _log.error(f"    [ERROR] Zwayam {portal['company']} start={offset}: {e}")
            if offset == 0:
                state["error_first"] = True
            return None
        return Page(items=inner.get("data") or [], total=inner.get("totalCount") or None,
                    has_more=inner.get("hasMoreData"))

    for hits in paginate(fetch_page, step=None):
        for hit in hits:
            src = hit.get("_source", hit)
            title = (src.get("jobTitle") or "").strip()
            if not title:
                continue

            loc = src.get("location") or src.get("city") or ""
            if india_only and not is_india(loc):
                continue

            jid = str(src.get("id") or "")
            slug = src.get("jobUrl") or jid
            apply_url = f"{parsed.scheme}://{domain}/job/{slug}" if slug else careers_url

            raw_jd = strip_html(
                src.get("shortDescription") or src.get("responsibility") or src.get("additionalDetails") or ""
            )

            jobs.append({
                "job_id":          jid,
                "title":           title,
                "job_url":         apply_url,
                "source_api_url":  api_url,
                "business_unit":   src.get("departmentName") or src.get("segment"),
                "raw_jd_text":     raw_jd,
                "location_city":   loc,
                "date_posted":     src.get("modifiedDate") or src.get("createdDate"),
                "source_platform": "Zwayam",
                "industry":        portal.get("industry", ""),
            })

            if max_jobs and len(jobs) >= max_jobs:
                return jobs

    if not jobs and state["error_first"]:
        return None  # couldn't reach the API at all -> API_BLOCKED
    _log.info(f"    {len(jobs)} jobs via Zwayam ({portal['company']})")
    return jobs
