from __future__ import annotations

"""RippleHire ATS provider.

Pattern:
  1) GET https://{host}/candidate/?token={token}&source=CAREERSITE  → acquire JSESSIONID
  2) POST https://{host}/candidate/candidatejobsearch
     form-encoded: careerSiteUrlParams (JSON), lang=en
     careerSiteUrlParams fields: page, search, token, source, pagesize, location
  3) Filter India client-side via is_india()
"""

import json
import logging

import requests

from config import REQUEST_TIMEOUT
from providers.base import ProviderResult, ScrapeReason
from schema import Portal
from utils import is_india, strip_html

_log = logging.getLogger("mirror")
_PAGE_SIZE = 50


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}


class RippleHireProvider:
    key = "ripplehire"

    def scrape(
        self,
        portal: Portal,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        try:
            jobs = _scrape_ripplehire(portal, max_jobs=max_jobs)
        except requests.RequestException as e:
            _log.error(f"    [ERROR] RippleHire {portal.get('company')}: {e}")
            return ProviderResult.error(ScrapeReason.API_BLOCKED)
        if jobs is None:
            return ProviderResult.error(ScrapeReason.API_BLOCKED)
        return ProviderResult.success(jobs)


def _scrape_ripplehire(portal: Portal, max_jobs: int | None = None) -> list[dict] | None:
    host = portal.get("ripplehire_host", "").strip()
    token = portal.get("ripplehire_token", "").strip()
    company = portal.get("company", "")
    industry = portal.get("industry", "")
    india_only = portal.get("india_only", True)

    if not host or not token:
        _log.error(f"    [RippleHire] {company}: missing ripplehire_host or ripplehire_token")
        return None

    base = f"https://{host}"
    sess = requests.Session()
    sess.headers.update({**_HEADERS, "Origin": base, "Referer": f"{base}/"})

    # Acquire session cookie
    try:
        sess.get(
            f"{base}/candidate/",
            params={"token": token, "source": "CAREERSITE"},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
    except Exception as e:
        _log.warning(f"    [RippleHire] {company}: session acquire failed ({e}); proceeding anyway")

    search_url = f"{base}/candidate/candidatejobsearch"
    jobs: list[dict] = []
    page = 0

    while True:
        params_obj = {
            "page": page,
            "search": "*:*",
            "token": token,
            "source": "CAREERSITE",
            "pagesize": _PAGE_SIZE,
            "location": "",
        }
        try:
            r = sess.post(
                search_url,
                data={"careerSiteUrlParams": json.dumps(params_obj), "lang": "en"},
                headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
                timeout=REQUEST_TIMEOUT,
            )
            r.raise_for_status()
            payload = r.json()
        except Exception as e:
            _log.error(f"    [ERROR] RippleHire {company} page={page}: {e}")
            return jobs or None

        # Response: {"response": {"docs": [...], "numFound": N}} or {"docs": [...]}
        response_obj = payload.get("response") or payload
        docs = response_obj.get("docs") or response_obj.get("jobs") or []
        if not docs:
            break

        for doc in docs:
            title = (
                doc.get("jobTitle")
                or doc.get("title")
                or doc.get("job_title")
                or ""
            ).strip()
            if not title:
                continue

            loc = (
                doc.get("location")
                or doc.get("city")
                or doc.get("jobLocation")
                or doc.get("jobCity")
                or ""
            )
            if isinstance(loc, list):
                loc = ", ".join(str(x) for x in loc if x)
            loc = str(loc).strip()

            if india_only and not is_india(loc):
                continue

            jid = str(
                doc.get("jobid")
                or doc.get("id")
                or doc.get("jobId")
                or doc.get("job_id")
                or ""
            ).strip()
            slug = (
                doc.get("jobUrl")
                or doc.get("joburl")
                or doc.get("urlSlug")
                or jid
                or ""
            )
            apply_url = f"{base}/job/{slug}" if slug else base

            raw_jd = strip_html(
                doc.get("shortDescription")
                or doc.get("longDescription")
                or doc.get("jobDescription")
                or doc.get("responsibility")
                or ""
            )

            jobs.append({
                "job_id":          jid or f"{company}_{title[:40]}",
                "title":           title,
                "job_url":         apply_url,
                "source_api_url":  search_url,
                "business_unit":   doc.get("departmentName") or doc.get("department") or doc.get("division"),
                "raw_jd_text":     raw_jd,
                "location_city":   loc or "India",
                "date_posted":     doc.get("modifiedDate") or doc.get("postedDate") or doc.get("createdDate"),
                "source_platform": "RippleHire",
                "industry":        industry,
            })

            if max_jobs and len(jobs) >= max_jobs:
                _log.info(f"    {company}: {len(jobs)} India jobs via RippleHire [cap]")
                return jobs

        if len(docs) < _PAGE_SIZE:
            break
        page += 1

    _log.info(f"    {company}: {len(jobs)} India jobs via RippleHire")
    return jobs
