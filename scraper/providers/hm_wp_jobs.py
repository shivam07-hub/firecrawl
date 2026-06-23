from __future__ import annotations

"""H&M careers provider via WordPress JSON API.

Validated API pattern:
  POST https://career.hm.com/in-en/wp-json/hm/v1/sr/jobs/search?_locale=user
  payload (India): {"locations": ["cou:in"], "page": N}

Response contains:
  - jobs[] with sr_id, title, city/country, job_description_text, apply_on_web_url
  - total (match count)
"""

import logging
from urllib.parse import urlsplit, urlunsplit

import requests

from config import REQUEST_TIMEOUT
from providers._paginate import Page, paginate
from providers.base import FALLBACK_FIRECRAWL_EXTRACT, ProviderResult
from schema import Portal
from utils import is_india, job_hash, strip_html

_log = logging.getLogger("mirror")

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
}

_INDIA_LOCATION_FILTER = "cou:in"
_MAX_PAGES = 1000


class HMWordPressJobsProvider:
    key = "hm_wp_jobs"

    def scrape(
        self,
        portal: Portal,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        jobs = _scrape_hm_jobs(portal, max_jobs=max_jobs)
        if jobs is None:
            fallback_portal = {
                **portal,
                "endpoint": portal.get("careers_url") or portal.get("endpoint", ""),
            }
            return ProviderResult.fallback(
                policy=FALLBACK_FIRECRAWL_EXTRACT,
                reason="hm_wp_jobs_api_blocked_or_unreachable",
                portal=fallback_portal,
            )
        return ProviderResult.success(jobs)


def _derive_api_url(careers_or_api_url: str) -> str:
    """Build the jobs API URL from either careers page URL or API URL."""
    if "/wp-json/hm/v1/sr/jobs/search" in careers_or_api_url:
        return careers_or_api_url

    parts = urlsplit(careers_or_api_url)
    segments = [s for s in parts.path.split("/") if s]
    locale_segment = segments[0] if segments else "in-en"
    path = f"/{locale_segment}/wp-json/hm/v1/sr/jobs/search"
    return urlunsplit((parts.scheme, parts.netloc, path, "_locale=user", ""))


def _compose_location(job: dict) -> str:
    city = (job.get("city") or "").strip()
    country = (job.get("country") or "").strip()
    address = (job.get("address") or "").strip()
    if city and country:
        return f"{city}, {country}"
    if city:
        return city
    if country:
        return country
    return address


def _compose_job_description(job: dict) -> str:
    """Merge available description sections into a single plain-text field."""
    sections: list[str] = []
    for key in ("job_description_text", "company_description_text"):
        text = strip_html(job.get(key) or "")
        if text and text.lower() != "job description":
            sections.append(text)

    qual = strip_html(job.get("qualifications_text") or "")
    if qual:
        sections.append(f"Qualifications: {qual}")

    additional = strip_html(job.get("additional_information_text") or "")
    if additional and additional.lower() != "job description":
        sections.append(f"Additional Information: {additional}")

    deduped: list[str] = []
    seen: set[str] = set()
    for sec in sections:
        if sec in seen:
            continue
        seen.add(sec)
        deduped.append(sec)
    return "\n\n".join(deduped)


def _scrape_hm_jobs(portal: Portal, max_jobs: int | None = None) -> list[dict] | None:
    endpoint = (portal.get("endpoint") or "").strip()
    if not endpoint.startswith("http"):
        _log.error(f"    [ERROR] H&M provider: invalid endpoint for {portal.get('company','')}: {endpoint}")
        return None

    company = portal.get("company", "")
    industry = portal.get("industry", "")
    india_only = portal.get("india_only", True)
    cap = max_jobs or 2000

    api_url = _derive_api_url(endpoint)
    session = requests.Session()
    session.headers.update(_HEADERS)
    session.headers["Referer"] = endpoint

    jobs: list[dict] = []
    seen_ids: set[str] = set()
    state = {"error_first": False}

    # Page-number API with no total; the shared paginator advances pages and stops
    # on an empty page or a page whose raw ids are all repeats. We keep an India-
    # aware `new_on_page == 0` break too (server-side filter can yield a non-India
    # page). No guessed page size — that was the Zwayam truncation bug.
    def fetch_page(page: int) -> Page | None:
        payload: dict = {"page": page}
        if india_only:
            payload["locations"] = [_INDIA_LOCATION_FILTER]
        try:
            r = session.post(api_url, json=payload, timeout=REQUEST_TIMEOUT)
        except Exception as e:
            _log.warning(f"    [WARN] H&M API request failed page={page} ({company}): {e}")
            state["error_first"] = page == 1
            return None
        if r.status_code != 200:
            _log.warning(f"    [WARN] H&M API status={r.status_code} page={page} ({company})")
            state["error_first"] = page == 1
            return None
        if "json" not in (r.headers.get("Content-Type") or "").lower():
            _log.warning(f"    [WARN] H&M API non-JSON response page={page} ({company})")
            state["error_first"] = page == 1
            return None
        try:
            data = r.json()
        except Exception:
            _log.warning(f"    [WARN] H&M API invalid JSON page={page} ({company})")
            state["error_first"] = page == 1
            return None
        batch = data.get("jobs") or []
        return Page(items=batch if isinstance(batch, list) else [])

    def _raw_id(raw: dict) -> str:
        return str(raw.get("sr_id") or raw.get("id") or id(raw)) if isinstance(raw, dict) else str(id(raw))

    for batch in paginate(fetch_page, start=1, step=1, max_pages=_MAX_PAGES, id_of=_raw_id):
        if len(jobs) >= cap:
            break
        page_marker = api_url
        new_on_page = 0
        for raw in batch:
            if not isinstance(raw, dict):
                continue

            title = (raw.get("title") or "").strip()
            if not title:
                continue

            location = _compose_location(raw)
            country = (raw.get("country") or "").strip()
            country_code = (raw.get("country_code") or "").strip().lower()
            if india_only and not (country_code == "in" or is_india(f"{location} {country}")):
                continue

            apply_url = (
                (raw.get("apply_on_web_url") or "").strip()
                or (raw.get("permalink") or "").strip()
            )

            job_id = str(raw.get("sr_id") or raw.get("id") or "").strip()
            if not job_id:
                job_id = job_hash(title, apply_url or f"{page_marker}#{title}")
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            raw_jd = _compose_job_description(raw)
            jobs.append(
                {
                    "job_id": job_id,
                    "title": title,
                    "job_url": apply_url,
                    "source_api_url": api_url,
                    "business_unit": raw.get("department_label") or raw.get("job_family_label") or "",
                    "raw_jd_text": raw_jd,
                    "location_city": location,
                    "date_posted": raw.get("updated_on") or raw.get("created_on") or raw.get("created_at") or "",
                    "source_platform": "HMCareersWP",
                    "industry": industry,
                }
            )
            new_on_page += 1
            if len(jobs) >= cap:
                break

        # India-aware end signal: server-side filter can return a page with no
        # India rows even though raw ids are new. (Empty pages and repeated-id
        # pages are stopped by the paginator itself.)
        if new_on_page == 0:
            break

    if not jobs and state["error_first"]:
        return None  # first page unreachable -> treat as provider failure
    scope_label = "India" if india_only else "global"
    _log.info(f"    {len(jobs)} {scope_label} jobs via H&M WP API ({company})")
    return jobs
