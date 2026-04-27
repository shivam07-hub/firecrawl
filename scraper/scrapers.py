"""
Direct-API scrapers for each ATS type.
Each function returns a list of partial job dicts with fields that can be
directly mapped from the ATS response (no LLM needed).
LLM enrichment happens later in enricher.py.

Returned dict shape (subset of canonical schema):
  job_id, title, job_url, source_api_url, business_unit,
  raw_jd_text, location_city, date_posted, source_platform
"""
import re
import requests
import firecrawl_client as fc
from utils import strip_html, is_india, job_hash
from config import REQUEST_TIMEOUT, WORKDAY_PAGE_SIZE, WORKDAY_MAX_JOBS, WORKDAY_JD_FETCH_LIMIT
from company_registry import WORKDAY_REGISTRY

_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type":    "application/json",
}


# ── WORKDAY ───────────────────────────────────────────────────────────────────

_WORKDAY_BLOCKED = object()   # sentinel: API returned redirect/error, try Firecrawl


def scrape_workday(portal: dict, max_jobs: int | None = None) -> list[dict] | None:
    """Returns list of jobs, empty list if no India jobs, or None if blocked (→ Firecrawl fallback)."""
    endpoint = portal['endpoint']

    company = portal.get('company', '')
    reg = WORKDAY_REGISTRY.get(company)
    use_search_text = reg and reg.get('search_text')
    if use_search_text:
        # searchText mode: no facet filter — tenant has no India UUID
        search_text_val = reg['search_text']
        print(f"    [REGISTRY] Using searchText='{search_text_val}' for {company}")
    elif reg:
        facet_param  = reg['india_facet_param']
        india_uuids  = reg.get('india_uuids') or [reg['india_uuid']]
        print(f"    [REGISTRY] Using hardcoded facet IDs for {company}")
    else:
        uuid_result = _workday_india_uuid(endpoint)
        if uuid_result is _WORKDAY_BLOCKED:
            return None   # signals scrape_portal to fall back to Firecrawl
        if uuid_result is None:
            print(f"    [WARN] no India UUID found for {company}")
            return []
        facet_param, india_uuid = uuid_result
        india_uuids = [india_uuid]

    parts = endpoint.split('/')
    referer = '/'.join(parts[:3]) + '/' + parts[-2] if len(parts) >= 8 else endpoint
    headers = {**_HEADERS, "Referer": referer}

    jobs, offset = [], 0
    seen_ids: set[str] = set()
    while True:
        if use_search_text:
            facets = {}
        else:
            facets = {facet_param: india_uuids}
            if reg and reg.get('it_uuids'):
                facets[reg['it_facet_param']] = reg['it_uuids']
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
            print(f"    [ERROR] Workday {portal['company']} offset={offset}: {e}")
            break

        postings = data.get('jobPostings', [])
        new_on_page = 0
        for p in postings:
            jid = p.get('jobReqId') or ''
            if jid and jid in seen_ids:
                continue                    # deduplicate overlapping pagination
            if jid:
                seen_ids.add(jid)
            new_on_page += 1

            ext = p.get('externalPath', '')
            tenant   = portal['tenant']
            instance = portal['instance']
            # externalPath is the browser-friendly path (e.g. /job/India--Hyderabad/Title_JR123)
            url = f"https://{tenant}.{instance}.myworkdayjobs.com{ext}" if ext else ''
            loc = p.get('locationsText') or p.get('primaryLocation', '')
            # searchText may return global results (e.g. "Indiana") — filter to India only
            if use_search_text and not is_india(loc):
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
                '_ext':            ext,       # kept for JD fetch; stripped by to_canonical
            })

        # Stop if pagination is stalling (all duplicates) or cap reached
        if new_on_page == 0 or len(postings) < WORKDAY_PAGE_SIZE:
            break
        if max_jobs and len(jobs) >= max_jobs:
            print(f"    [WORKDAY] Validate cap reached ({max_jobs} jobs) — stopping pagination")
            break
        if len(jobs) >= WORKDAY_MAX_JOBS:
            print(f"    [WORKDAY] Cap reached ({WORKDAY_MAX_JOBS} jobs) — stopping pagination")
            break
        offset += WORKDAY_PAGE_SIZE

    # Truncate to max_jobs before JD fetches to avoid wasted requests in validate mode
    if max_jobs:
        jobs = jobs[:max_jobs]

    # Fetch full JD text for each job via the Workday CXS individual-job API
    _fetch_workday_jds(jobs, portal)
    return jobs


def _workday_india_uuid(endpoint: str):
    """POST with empty facets, recursively search response for 'India' UUID.
    Returns: (facet_param, uuid) tuple | None (no India facet) | _WORKDAY_BLOCKED (redirect/error → try Firecrawl)
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
            print(f"    [ERROR] Workday UUID discovery: redirect {r.status_code} — API blocked (Cloudflare)")
            return _WORKDAY_BLOCKED
        r.raise_for_status()
        body = r.text.strip()
        if not body:
            print(f"    [ERROR] Workday UUID discovery: empty response body")
            return _WORKDAY_BLOCKED
        return _find_india_id(r.json())
    except Exception as e:
        print(f"    [ERROR] Workday UUID discovery: {e}")
        return _WORKDAY_BLOCKED


def _find_india_id(obj, _parent_facet_param: str = 'locationCountry') -> tuple[str, str] | None:
    """Recursively walk Workday facet JSON to find (facet_parameter, India UUID)."""
    if isinstance(obj, list):
        for item in obj:
            result = _find_india_id(item, _parent_facet_param)
            if result:
                return result
    elif isinstance(obj, dict):
        # Track the facet parameter of the current facet group
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


# ── SMARTRECRUITERS ───────────────────────────────────────────────────────────

def scrape_smartrecruiters(portal: dict, max_jobs: int | None = None) -> list[dict]:
    """
    SmartRecruiters list endpoint never includes jobAd body.
    We fetch the individual posting (ref URL) for each job to get the JD.
    """
    list_url = portal['endpoint']
    try:
        r = requests.get(list_url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"    [ERROR] SmartRecruiters {portal['company']}: {e}")
        return []

    listings = data.get('content', [])
    if max_jobs:
        listings = listings[:max_jobs]
    print(f"    {len(listings)} postings listed — fetching JDs...")

    jobs = []
    india_only = portal.get('india_only', False)
    for p in listings:
        loc  = p.get('location') or {}
        city = loc.get('city') or loc.get('country', '')
        if india_only and not is_india(f"{city} {loc.get('country', '')}"):
            continue
        dept = (p.get('department') or {}).get('label')
        ref  = p.get('ref', '')          # API URL for this individual posting

        # Fetch full posting to get jobAd sections
        raw_jd = ''
        public_url = ref
        if ref:
            try:
                jr = requests.get(ref, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
                jr.raise_for_status()
                jdata    = jr.json()
                sections = (jdata.get('jobAd') or {}).get('sections') or {}
                raw_jd   = strip_html(
                    sections.get('jobDescription', {}).get('text', '') or
                    sections.get('qualifications', {}).get('text', '')
                )
                # Public-facing URL is better than the API ref for job_url
                public_url = jdata.get('postingUrl') or jdata.get('applyUrl') or ref
            except Exception:
                pass    # keep raw_jd='' and fall through to LLM enrichment

        jobs.append({
            'job_id':          str(p.get('id') or job_hash(p.get('name', ''), ref)),
            'title':           p.get('name', ''),
            'job_url':         public_url,
            'source_api_url':  list_url,
            'business_unit':   dept,
            'raw_jd_text':     raw_jd,
            'location_city':   city,
            'date_posted':     p.get('releasedDate'),
            'source_platform': 'SmartRecruiters',
            'industry':        portal.get('industry', ''),
        })
    return jobs


# ── GREENHOUSE ────────────────────────────────────────────────────────────────

def scrape_greenhouse(portal: dict) -> list[dict]:
    url = portal['endpoint']
    try:
        r = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"    [ERROR] Greenhouse {portal['company']}: {e}")
        return []

    india_only = portal.get('india_only', True)
    jobs = []
    for p in data.get('jobs', []):
        loc = (p.get('location') or {}).get('name', '')
        if india_only and not is_india(loc):
            continue
        depts  = p.get('departments') or []
        raw_jd = strip_html(p.get('content', ''))
        jobs.append({
            'job_id':          str(p.get('id', job_hash(p.get('title', ''), p.get('absolute_url', '')))),
            'title':           p.get('title', ''),
            'job_url':         p.get('absolute_url', ''),
            'source_api_url':  url,
            'business_unit':   depts[0]['name'] if depts else None,
            'raw_jd_text':     raw_jd,
            'location_city':   loc,
            'date_posted':     p.get('updated_at'),
            'source_platform': 'Greenhouse',
            'industry':        portal.get('industry', ''),
        })
    return jobs


# ── CUSTOM / SAP / ORACLE (GET-based JSON or HTML) ───────────────────────────

def scrape_get(portal: dict) -> list[dict]:
    """
    Best-effort scraper for GET-based APIs (Amazon, Microsoft, Apple, SAP HTML, etc.).
    Returns partial jobs if the response is JSON with a recognisable structure,
    or a sentinel dict for HTML responses that need Firecrawl post-processing.
    """
    url = portal['endpoint']
    if not url.startswith('http'):
        print(f"    [SKIP] {portal['company']}: endpoint not a URL")
        return []

    try:
        r = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        print(f"    [ERROR] GET {portal['company']}: {e}")
        return []

    # Try JSON
    ct = r.headers.get('Content-Type', '')
    if 'json' in ct or r.text.lstrip().startswith(('{', '[')):
        try:
            return _parse_json_response(r.json(), portal, url)
        except Exception:
            pass

    # HTML / XML response → hand to Firecrawl path via sentinel
    return [{'_needs_firecrawl': True, '_url': url, '_company': portal['company'],
             '_platform': portal.get('ats', 'Custom')}]


def _fetch_workday_jds(jobs: list[dict], portal: dict) -> None:
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

    # ── Strategy 1: direct CXS GET ───────────────────────────────────────────
    # Correct format: /wday/cxs/{tenant}/{career_site}{ext}  (career_site was missing before)
    career_site = portal.get('career_site', '')
    cxs_base = f"https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{career_site}"
    print(f"    Fetching JDs for {len(to_fetch)}/{len(jobs)} jobs via Workday CXS API...")
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

    print(f"    JDs fetched (CXS): {ok} ok  {fail} missing/error")

    # ── Strategy 2: Firecrawl Docker fallback ────────────────────────────────
    # If direct API got nothing, use Firecrawl to render each job's human-facing page.
    # Only runs against Docker (localhost:3002) — never burns cloud credits for JDs.
    # job_url was already built with full en-US/{career_site}/job/... format in scrape_workday.
    still_missing = [j for j in to_fetch if not j.get('raw_jd_text') and j.get('job_url')]
    if still_missing and ok == 0:
        urls = [j['job_url'] for j in still_missing]
        print(f"    [FC FALLBACK] Scraping {len(urls)} Workday JD pages via Docker...")
        BATCH = 20
        fc_ok = 0
        for i in range(0, len(urls), BATCH):
            batch_urls = urls[i:i + BATCH]
            results = fc.batch_scrape(batch_urls)
            for job in still_missing[i:i + BATCH]:
                md = results.get(job['job_url'], '')
                if md and len(md) > 500:   # ignore stub/error pages
                    job['raw_jd_text'] = md
                    fc_ok += 1
        print(f"    [FC FALLBACK] JDs via Firecrawl: {fc_ok} ok  {len(still_missing) - fc_ok} missing")


def _parse_json_response(data, portal: dict, source_url: str) -> list[dict]:
    """Walk common JSON structures to extract job listings."""
    company  = portal['company']
    platform = portal.get('ats', 'Custom').title()

    # Try common root keys to find the array of jobs
    items = (
        data.get('jobPostings') or
        data.get('jobs') or
        data.get('results') or
        data.get('data') or
        (data if isinstance(data, list) else [])
    )
    if not isinstance(items, list):
        return []

    jobs = []
    for p in items:
        if not isinstance(p, dict):
            continue

        title = p.get('title') or p.get('name') or p.get('jobTitle') or ''
        if not title:
            continue

        # Location — may be string or dict
        raw_loc = (
            p.get('normalized_location') or p.get('location') or
            p.get('city') or p.get('country') or ''
        )
        loc = raw_loc if isinstance(raw_loc, str) else (
            raw_loc.get('city') or raw_loc.get('name') or ''
        )

        if not is_india(loc):
            continue

        raw_jd = strip_html(
            p.get('description') or p.get('jobDescription') or
            p.get('content') or p.get('summary') or ''
        )
        # Amazon uses job_path (/en/jobs/...) — build full URL; others use url/job_url/absolute_url/ref
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
    return jobs


# ── FIRECRAWL EXTRACT (structured extraction via Firecrawl cloud LLM) ─────────

# Schema fed to Firecrawl's /v1/extract endpoint — mirrors our canonical schema.
_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "jobs": {
            "type": "array",
            "description": "All India-based job listings found on the page",
            "items": {
                "type": "object",
                "properties": {
                    "title":         {"type": "string",  "description": "Exact job title"},
                    "job_url":       {"type": "string",  "description": "Full absolute URL to the job posting"},
                    "location_city": {"type": "string",  "description": "City or location string (e.g. Bengaluru, Hyderabad, India)"},
                    "business_unit": {"type": "string",  "description": "Department or team"},
                    "raw_jd_text":   {"type": "string",  "description": "Full job description text if visible on the page"},
                    "date_posted":   {"type": "string",  "description": "Date posted in YYYY-MM-DD format if available"},
                },
                "required": ["title"],
            },
        }
    },
    "required": ["jobs"],
}

_EXTRACT_PROMPT = (
    "Extract all job listings located in India from this careers page. "
    "India locations include cities such as Bengaluru, Hyderabad, Mumbai, Pune, "
    "Delhi, Chennai, Gurugram, Noida, Kolkata, Ahmedabad, or anything labelled India. "
    "For each job capture the full job description text if it is visible on the page. "
    "Only include roles where the location is confirmed to be in India. "
    "If there are multiple pages of results, include jobs from all visible pages."
)


def scrape_validate(portal: dict, max_jobs: int = 5) -> list[dict]:
    """
    Validate-mode scraper for JS-heavy portals: fc.scrape() only (Playwright, no LLM).
    Parses markdown for job title candidates — sufficient to verify column coverage.
    """
    import re
    url = portal['endpoint']
    print(f"    Firecrawl scrape (validate): {url}")
    md = fc.scrape(url)
    if not md:
        return []

    jobs = []
    # Extract link text that look like job titles: [Title](url) patterns
    links = re.findall(r'\[([^\]]{10,120})\]\((https?://[^\)]+)\)', md)
    for title, job_url in links[:max_jobs * 3]:
        # Skip navigation/footer noise
        if any(w in title.lower() for w in ('cookie', 'privacy', 'sign in', 'log in', 'menu', 'search', 'home', 'about', 'contact', 'careers')):
            continue
        jobs.append({
            'job_id':          job_hash(title, job_url),
            'title':           title.strip(),
            'job_url':         job_url,
            'source_api_url':  url,
            'business_unit':   None,
            'raw_jd_text':     '',
            'location_city':   '',
            'date_posted':     None,
            'source_platform': 'Firecrawl',
            'industry':        portal.get('industry', ''),
        })
        if len(jobs) >= max_jobs:
            break

    # Fallback: if no links found, create 1 stub entry so the portal shows up in output
    if not jobs:
        # grab first meaningful heading as title
        heading = next((l.lstrip('# ').strip() for l in md.splitlines() if l.startswith('#') and len(l) > 5), '')
        title = heading or f"{portal['company']} careers page"
        jobs.append({
            'job_id':          job_hash(title, url),
            'title':           title,
            'job_url':         url,
            'source_api_url':  url,
            'business_unit':   None,
            'raw_jd_text':     md[:1000],
            'location_city':   '',
            'date_posted':     None,
            'source_platform': 'Firecrawl',
            'industry':        portal.get('industry', ''),
        })

    print(f"    {len(jobs)} entries from scrape")
    return jobs


def scrape_extract(portal: dict, max_jobs: int | None = None) -> list[dict]:
    """
    Scrape JS-heavy career pages via Firecrawl Docker.
    Two-pass: scrape listing page → parse individual job URLs → batch_scrape each.
    Falls back to single-entry staging if no job links are parseable.
    """
    url     = portal.get('endpoint') or portal.get('careers_url', '')
    company = portal.get('company', '')

    print(f"    Firecrawl scrape (Docker): {url}")
    markdown = fc.scrape(url)
    if not markdown or len(markdown) < 200:
        return []

    _LINK_PATTERNS = [
        re.compile(r'\[([^\]]+)\]\((https?://[^\)]+/details/\d+[^\)]*)\)'),
        re.compile(r'\[([^\]]+)\]\((https?://[^\)]+/job[s]?/[^\)]{5,})\)'),
        re.compile(r'\[([^\]]+)\]\((https?://[^\)]+/careers?/[^\)]{10,})\)'),
        re.compile(r'\[([^\]]+)\]\((https?://[^\)]+/opening[s]?/[^\)]{5,})\)'),
        re.compile(r'(https?://[^\s\)\]\"]+/details/\d+[^\s\)\]\"]+)'),
        re.compile(r'(https?://[^\s\)\]\"]{20,}/job[s]?/[^\s\)\]\"]{8,})'),
    ]
    _NOISE_EXT   = ('.svg', '.png', '.jpg', '.css', '.js', '.ico', '.woff', '.gif', '.webp')
    _NOISE_WORDS = ('menu', 'search', 'home', 'cookie', 'nav', 'sign in', 'log in', 'privacy', 'about us')

    seen, job_links = set(), []
    for pat in _LINK_PATTERNS:
        for m in pat.finditer(markdown):
            if pat.groups >= 2:
                title, link = m.group(1), m.group(2)
            else:
                title, link = '', m.group(1)
            clean = link.split('?')[0].rstrip('/')
            if any(clean.endswith(e) for e in _NOISE_EXT):
                continue
            if clean in seen:
                continue
            seen.add(clean)
            job_links.append((title.strip(), link))

    print(f"    Found {len(job_links)} candidate job URLs in listing markdown")

    if not job_links:
        print(f"    No job links found — using single staging entry (small/boutique company)")
        return [{
            'job_id':           job_hash(company, url),
            'title':            f'{company} — scraped via Firecrawl',
            'job_url':          url,
            'source_api_url':   url,
            'business_unit':    None,
            'raw_jd_text':      markdown,
            'location_city':    'India',
            'date_posted':      None,
            'source_platform':  'Firecrawl',
            'industry':         portal.get('industry', ''),
            '_fc_raw_markdown': True,
        }]

    cap = max_jobs or 200
    job_links = job_links[:cap]

    BATCH = 20
    india_only = portal.get('india_only', True)
    jobs = []
    for i in range(0, len(job_links), BATCH):
        chunk = job_links[i:i + BATCH]
        results = fc.batch_scrape([link for _, link in chunk])
        for link_title, job_url in chunk:
            jd_md = results.get(job_url, '')
            if not jd_md or len(jd_md) < 100:
                continue
            if india_only and not is_india(link_title + ' ' + jd_md[:1500]):
                continue
            title = link_title if (
                len(link_title) > 5 and
                not any(w in link_title.lower() for w in _NOISE_WORDS)
            ) else company
            jobs.append({
                'job_id':          job_hash(title, job_url),
                'title':           title,
                'job_url':         job_url,
                'source_api_url':  url,
                'business_unit':   None,
                'raw_jd_text':     jd_md,
                'location_city':   'India',
                'date_posted':     None,
                'source_platform': 'Firecrawl',
                'industry':        portal.get('industry', ''),
            })

    print(f"    {len(jobs)} India jobs extracted from individual pages")
    return jobs



# ── PHENOM REST API (paginated JSON) ──────────────────────────────────────────

def scrape_phenom_api(portal: dict) -> list[dict]:
    """
    Scrape Phenom/iCIMS REST APIs that return paginated JSON with full JDs.
    Currently handles: Schneider Electric (careers.se.com/api/jobs).

    The endpoint URL from KNOWN_PORTALS.md already contains base params
    (location, categories, pageSize). We append &page=N for pagination.
    """
    base_url   = portal['endpoint']
    company    = portal['company']
    india_only = portal.get('india_only', True)
    jobs       = []
    page       = 1
    _GLOBAL_CAP = 500   # cap when india_only=False to avoid unbounded fetches

    while True:
        url = f"{base_url}&page={page}"
        try:
            r = requests.get(url, headers={**_HEADERS, "Accept": "application/json"}, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"    [ERROR] Phenom API {company} page={page}: {e}")
            break

        raw_jobs = data.get('jobs', [])
        if not raw_jobs:
            break

        for item in raw_jobs:
            job_data = item.get('data') or item   # API wraps each job in {"data": {...}}
            title    = job_data.get('title', '').strip()
            if not title:
                continue

            # Combine all available JD fields into raw_jd_text
            jd_parts = [
                job_data.get('description', '') or '',
                job_data.get('responsibilities', '') or '',
                job_data.get('qualifications', '') or '',
            ]
            raw_jd = strip_html('\n\n'.join(p for p in jd_parts if p).strip())

            loc_raw = job_data.get('location_name') or job_data.get('full_location') or job_data.get('location') or {}
            if isinstance(loc_raw, dict):
                city = loc_raw.get('city') or loc_raw.get('name') or ''
            else:
                city = str(loc_raw)

            job_url = (job_data.get('apply_url') or job_data.get('jobUrl') or
                       job_data.get('applyUrl') or '')
            jid     = str(job_data.get('req_id') or job_data.get('jobId') or
                          job_data.get('id') or job_hash(title, job_url))

            jobs.append({
                'job_id':          jid,
                'title':           title,
                'job_url':         job_url,
                'source_api_url':  base_url,
                'business_unit':   job_data.get('department') or job_data.get('category'),
                'raw_jd_text':     raw_jd,
                'location_city':   city,
                'date_posted':     job_data.get('publishedDate') or job_data.get('datePosted'),
                'source_platform': 'Phenom',
                'industry':        portal.get('industry', ''),
            })

        total = data.get('total', 0)
        page_size = len(raw_jobs)
        if not total or page * page_size >= total:
            break
        if not india_only and len(jobs) >= _GLOBAL_CAP:
            break
        page += 1

    print(f"    {len(jobs)} India jobs fetched via Phenom API")
    return jobs


# ── LEVER ─────────────────────────────────────────────────────────────────────

_INDIA_KEYWORDS = {'india', 'bangalore', 'bengaluru', 'hyderabad', 'mumbai',
                   'pune', 'chennai', 'noida', 'gurgaon', 'gurugram', 'delhi'}

def scrape_lever(portal: dict) -> list[dict]:
    """
    Lever ATS: GET https://api.lever.co/v0/postings/{slug}?mode=json
    Returns all active postings. Filters to India jobs unless portal marks
    india_only=False (for India-founded companies, all jobs are India).
    """
    slug       = portal['lever_slug']
    company    = portal['company']
    india_only = portal.get('india_only', True)
    url        = f"https://api.lever.co/v0/postings/{slug}?mode=json"

    try:
        r = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        postings = r.json()
    except Exception as e:
        print(f"    [ERROR] Lever {company}: {e}")
        return []

    if not isinstance(postings, list):
        print(f"    [WARN] Lever {company}: unexpected response type")
        return []

    jobs = []
    for p in postings:
        location = (p.get('categories') or {}).get('location') or ''
        if india_only and not any(kw in location.lower() for kw in _INDIA_KEYWORDS):
            continue

        jd_plain = p.get('descriptionPlain') or strip_html(p.get('description') or '')
        # lists: lists is HTML with structured sections; merge into JD if available
        for lst in (p.get('lists') or []):
            content = strip_html(lst.get('content', ''))
            if content:
                jd_plain = f"{jd_plain}\n\n{lst.get('text', '')}\n{content}"

        jid = p.get('id') or job_hash(p.get('text', ''), p.get('hostedUrl', ''))
        jobs.append({
            'job_id':          jid,
            'title':           p.get('text', '').strip(),
            'job_url':         p.get('hostedUrl') or p.get('applyUrl') or '',
            'source_api_url':  url,
            'business_unit':   (p.get('categories') or {}).get('team'),
            'raw_jd_text':     jd_plain.strip(),
            'location_city':   location,
            'date_posted':     None,
            'source_platform': 'Lever',
            'industry':        portal.get('industry', ''),
        })

    print(f"    {len(jobs)} jobs fetched via Lever ({slug})")
    return jobs
