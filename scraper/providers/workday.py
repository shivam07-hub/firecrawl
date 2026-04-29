from __future__ import annotations

from schema import Portal

import json
import logging
import threading
import requests
from pathlib import Path

import firecrawl_client as fc
from config import REQUEST_TIMEOUT, WORKDAY_PAGE_SIZE, WORKDAY_MAX_JOBS, WORKDAY_JD_FETCH_LIMIT
from providers.base import FALLBACK_FIRECRAWL_EXTRACT, ProviderResult, ScrapeReason
from utils import is_india, job_hash, strip_html

_REGISTRY_PATH = Path(__file__).parent.parent / "workday_registry.json"
_registry_lock = threading.Lock()

_log = logging.getLogger("mirror")

_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type":    "application/json",
}

_WORKDAY_BLOCKED = object()  # sentinel: API redirected/errored → try Firecrawl


class WorkdayProvider:
    key = "workday"

    def scrape(
        self,
        portal: Portal,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        # Skip API entirely for Cloudflare-blocked tenants — go straight to Firecrawl
        if portal.get('workday_blocked'):
            _log.info(f"    [BLOCKED] {portal.get('company','')} — Cloudflare-blocked Workday, skip to Firecrawl")
            fallback_portal = dict(portal)
            if portal.get("careers_url"):
                fallback_portal["endpoint"] = portal["careers_url"]
            return ProviderResult.fallback(
                policy=FALLBACK_FIRECRAWL_EXTRACT,
                reason="workday_cloudflare_blocked",
                portal=fallback_portal,
            )

        jobs, reason = scrape_workday(portal, max_jobs=max_jobs)

        # Global mode returned 0 or blocked → retry with India UUID before giving up
        if not portal.get('india_only', True):
            should_retry = (
                (jobs is None and reason == ScrapeReason.API_BLOCKED) or
                (isinstance(jobs, list) and len(jobs) == 0 and reason == ScrapeReason.NO_JOBS)
            )
            if should_retry:
                _log.info(f"    [RETRY] Global 0/422 — retrying {portal.get('company','')} with India UUID")
                india_portal = {**portal, 'india_only': True}
                jobs2, reason2 = scrape_workday(india_portal, max_jobs=max_jobs)
                if jobs2 is not None and (len(jobs2) > 0 or jobs is None):
                    return ProviderResult(jobs=jobs2, reason=reason2)
                # India UUID also failed → fall through to Firecrawl
                if jobs is None or reason == ScrapeReason.API_BLOCKED:
                    fallback_portal = dict(portal)
                    if portal.get("careers_url"):
                        fallback_portal["endpoint"] = portal["careers_url"]
                    return ProviderResult.fallback(
                        policy=FALLBACK_FIRECRAWL_EXTRACT,
                        reason="workday_api_blocked",
                        portal=fallback_portal,
                    )

        if jobs is None:
            if reason == ScrapeReason.API_BLOCKED:
                fallback_portal = dict(portal)
                if portal.get("careers_url"):
                    fallback_portal["endpoint"] = portal["careers_url"]
                return ProviderResult.fallback(
                    policy=FALLBACK_FIRECRAWL_EXTRACT,
                    reason="workday_api_blocked",
                    portal=fallback_portal,
                )
            # CONFIG_ERROR: no India UUID found — skip, no Firecrawl fallback
            return ProviderResult.error(reason)
        return ProviderResult(jobs=jobs, reason=reason)


def scrape_workday(
    portal: Portal, max_jobs: int | None = None
) -> tuple[list[dict] | None, ScrapeReason]:
    """
    Returns (jobs, reason):
      ([...], SUCCESS/NO_JOBS)  — normal result
      (None,  API_BLOCKED)      — Cloudflare / HTTP redirect → try Firecrawl
      (None,  CONFIG_ERROR)     — no India UUID found for tenant → skip, no fallback
    """
    endpoint = portal['endpoint']
    india_only = portal.get('india_only', True)

    company = portal.get('company', '')
    if india_only:
        use_search_text = bool(portal.get('workday_search_text'))
        if use_search_text:
            search_text_val = portal['workday_search_text']
            _log.info(f"    [REGISTRY] Using searchText='{search_text_val}' for {company}")
        elif portal.get('workday_facet_param'):
            facet_param = portal['workday_facet_param']
            india_uuids = portal.get('workday_india_uuids') or []
            _log.info(f"    [REGISTRY] Using hardcoded facet IDs for {company}")
        else:
            uuid_result = _workday_india_uuid(endpoint)
            if uuid_result is _WORKDAY_BLOCKED:
                return None, ScrapeReason.API_BLOCKED
            if uuid_result is None:
                _log.warning(f"    [WARN] no India UUID found for {company}")
                return None, ScrapeReason.CONFIG_ERROR
            facet_param, india_uuid = uuid_result
            india_uuids = [india_uuid]
            # Persist discovered UUID → next run skips discovery entirely
            _persist_uuid(company, facet_param, india_uuid)
    else:
        use_search_text = False
        search_text_val = ""
        facet_param = ""
        india_uuids = []
        _log.info(f"    [SCOPE] Global mode for {company} (no India facet filter)")

    parts = endpoint.split('/')
    referer = '/'.join(parts[:3]) + '/' + parts[-2] if len(parts) >= 8 else endpoint
    headers = {**_HEADERS, "Referer": referer}

    jobs, offset = [], 0
    seen_ids: set[str] = set()
    while True:
        if not india_only:
            facets = {}
        elif use_search_text:
            facets = {}
        else:
            facets = {facet_param: india_uuids}
            if portal.get('workday_it_uuids'):
                facets[portal['workday_it_facet_param']] = portal['workday_it_uuids']
        payload = {
            "appliedFacets": facets,
            "limit":  WORKDAY_PAGE_SIZE,
            "offset": offset,
            "searchText": search_text_val if use_search_text else "",
        }
        try:
            r = requests.post(endpoint, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            _log.error(f"    [ERROR] Workday {portal['company']} offset={offset}: {e}")
            if offset == 0:
                return None, ScrapeReason.API_BLOCKED
            break

        postings = data.get('jobPostings', [])
        new_on_page = 0
        for p in postings:
            jid = p.get('jobReqId') or ''
            if jid and jid in seen_ids:
                continue
            if jid:
                seen_ids.add(jid)
            new_on_page += 1

            ext = p.get('externalPath', '')
            tenant   = portal['tenant']
            instance = portal['instance']
            url = f"https://{tenant}.{instance}.myworkdayjobs.com{ext}" if ext else ''
            loc = p.get('locationsText') or p.get('primaryLocation', '')
            if india_only and use_search_text and not is_india(loc):
                continue
            bf  = p.get('bulletFields') or []
            bu  = bf[1] if len(bf) > 1 else None
            jobs.append({
                'job_id':          jid or job_hash(p.get('title', ''), url),
                'title':           p.get('title', ''),
                'job_url':         url,
                'source_api_url':  endpoint,
                'business_unit':   bu,
                'raw_jd_text':     strip_html(p.get('jobDescription', '')),
                'location_city':   loc,
                'date_posted':     p.get('postedOn'),
                'source_platform': 'Workday',
                'industry':        portal.get('industry', ''),
                '_ext':            ext,
            })

        if new_on_page == 0 or len(postings) < WORKDAY_PAGE_SIZE:
            break
        if max_jobs and len(jobs) >= max_jobs:
            _log.info(f"    [WORKDAY] Validate cap reached ({max_jobs} jobs) — stopping pagination")
            break
        if len(jobs) >= WORKDAY_MAX_JOBS:
            _log.info(f"    [WORKDAY] Cap reached ({WORKDAY_MAX_JOBS} jobs) — stopping pagination")
            break
        offset += WORKDAY_PAGE_SIZE

    if max_jobs:
        jobs = jobs[:max_jobs]

    _fetch_workday_jds(jobs, portal)
    reason = ScrapeReason.SUCCESS if jobs else ScrapeReason.NO_JOBS
    return jobs, reason


def _persist_uuid(company: str, facet_param: str, india_uuid: str) -> None:
    """Write discovered India UUID back to workday_registry.json (thread-safe).
    Only writes if company has no existing registry entry — never overwrites manual entries.
    """
    with _registry_lock:
        try:
            registry = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8")) if _REGISTRY_PATH.exists() else {}
            if company in registry:
                return  # manual entry takes precedence
            registry[company] = {"india_facet_param": facet_param, "india_uuid": india_uuid}
            _REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
            _log.info(f"    [REGISTRY] Persisted India UUID for {company} ({facet_param}={india_uuid[:8]}…)")
        except Exception as e:
            _log.warning(f"    [REGISTRY] Failed to persist UUID for {company}: {e}")


def _workday_india_uuid(endpoint: str):
    """POST with empty facets, recursively search response for 'India' UUID.
    Returns: (facet_param, uuid) | None (no India facet) | _WORKDAY_BLOCKED (redirect/error)
    """
    parts = endpoint.split('/')
    referer = '/'.join(parts[:3]) + '/' + parts[-2] if len(parts) >= 8 else endpoint
    headers = {**_HEADERS, "Referer": referer}
    try:
        r = requests.post(
            endpoint,
            json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        if r.status_code in (301, 302, 303, 307, 308):
            _log.error(f"    [ERROR] Workday UUID discovery: redirect {r.status_code} — API blocked (Cloudflare)")
            return _WORKDAY_BLOCKED
        r.raise_for_status()
        body = r.text.strip()
        if not body:
            _log.error(f"    [ERROR] Workday UUID discovery: empty response body")
            return _WORKDAY_BLOCKED
        return _find_india_id(r.json())
    except Exception as e:
        _log.error(f"    [ERROR] Workday UUID discovery: {e}")
        return _WORKDAY_BLOCKED


def _find_india_id(obj, _parent_facet_param: str = 'locationCountry') -> tuple[str, str] | None:
    """Recursively walk Workday facet JSON to find (facet_parameter, India UUID)."""
    if isinstance(obj, list):
        for item in obj:
            result = _find_india_id(item, _parent_facet_param)
            if result:
                return result
    elif isinstance(obj, dict):
        facet_param = obj.get('facetParameter', _parent_facet_param)
        descriptor = (obj.get('descriptor') or obj.get('name') or '').lower()
        if descriptor == 'india':
            uid = obj.get('id') or obj.get('value')
            return (facet_param, uid) if uid else None
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                result = _find_india_id(v, facet_param)
                if result:
                    return result
    return None


def _fetch_workday_jds(jobs: list[dict], portal: Portal) -> None:
    """
    Fill raw_jd_text for Workday jobs.
    Strategy 1 — Workday CXS individual-job JSON API (fast, no credits).
    Strategy 2 — Firecrawl Docker batch_scrape on human-facing job_url (fallback when CXS is
                  Cloudflare-blocked; uses Docker so no credit cost).
    Mutates jobs in-place. Capped at WORKDAY_JD_FETCH_LIMIT.
    """
    tenant   = portal.get('tenant', '')
    instance = portal.get('instance', '')
    if not tenant or not instance:
        return

    to_fetch = [j for j in jobs if not j.get('raw_jd_text') and j.get('_ext')]
    to_fetch = to_fetch[:WORKDAY_JD_FETCH_LIMIT]
    if not to_fetch:
        return

    career_site = portal.get('career_site', '')
    cxs_base = f"https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{career_site}"
    _log.info(f"    Fetching JDs for {len(to_fetch)}/{len(jobs)} jobs via Workday CXS API...")
    ok = fail = 0
    for job in to_fetch:
        detail_url = cxs_base + job['_ext']
        try:
            r = requests.get(detail_url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            info = r.json().get('jobPostingInfo', {})
            jd   = info.get('jobDescription', '') or info.get('jobSummary', '')
            if jd:
                job['raw_jd_text'] = strip_html(jd)
                ok += 1
            else:
                fail += 1
        except Exception:
            fail += 1

    _log.info(f"    JDs fetched (CXS): {ok} ok  {fail} missing/error")

    still_missing = [j for j in to_fetch if not j.get('raw_jd_text') and j.get('job_url')]
    if still_missing and ok == 0:
        urls = [j['job_url'] for j in still_missing]
        _log.info(f"    [FC FALLBACK] Scraping {len(urls)} Workday JD pages via Docker...")
        BATCH = 20
        fc_ok = 0
        for i in range(0, len(urls), BATCH):
            batch_urls = urls[i:i + BATCH]
            results = fc.batch_scrape(batch_urls)
            for job in still_missing[i:i + BATCH]:
                md = results.get(job['job_url'], '')
                if md and len(md) > 500:
                    job['raw_jd_text'] = md
                    fc_ok += 1
        _log.info(f"    [FC FALLBACK] JDs via Firecrawl: {fc_ok} ok  {len(still_missing) - fc_ok} missing")
