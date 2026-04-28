"""
Parse KNOWN_PORTALS.md into a list of portal config dicts.

Each dict has at minimum:
  company       str
  ats           str   workday | smartrecruiters | greenhouse | eightfold |
                      custom | sap | oracle | avature | other
  endpoint      str   URL to hit (API or careers page)
  js_required   bool  True → route through Firecrawl browser rendering
  status        str   raw status emoji string from the file
  industry      str   company sector (from lookup below)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from config import PORTALS_PATH
from schema import Portal

# ── Industry lookup — loaded lazily from company_industries.json ──────────────
# Edit company_industries.json to add/update mappings — no Python change needed.
_INDUSTRIES_PATH = Path(__file__).parent / "company_industries.json"
_COMPANY_INDUSTRY: dict[str, str] | None = None


def _load_industries() -> dict[str, str]:
    global _COMPANY_INDUSTRY
    if _COMPANY_INDUSTRY is None:
        if _INDUSTRIES_PATH.exists():
            _COMPANY_INDUSTRY = json.loads(_INDUSTRIES_PATH.read_text(encoding="utf-8"))
        else:
            print(f"  [WARN] company_industries.json not found at {_INDUSTRIES_PATH}; all portals will have empty industry")
            _COMPANY_INDUSTRY = {}
    return _COMPANY_INDUSTRY



def _industry(company: str) -> str:
    """Look up industry from company_industries.json. Warns once if file missing.
    Logs a warning (not silent empty string) if the company has no entry.
    """
    ind = _load_industries().get(company, '')
    if not ind:
        print(f'  [WARN] No industry mapping for {company!r} — add to company_industries.json')
    return ind


# ── Workday tenant overrides ──────────────────────────────────────────────────
# Tenants that use non-standard facet names, have no dynamic-discoverable India
# UUID, or are Cloudflare-blocked at the discovery endpoint.
# Inlined from former company_registry.py — full migration to KNOWN_PORTALS.md
# columns is tracked as Arch-Phase D1.
_WORKDAY_REGISTRY: dict[str, dict] = {
    # searchText mode — no India UUID in tenant facets
    "Intel":  {"search_text": "india"},
    "Target": {"search_text": "india"},
    # Standard India UUID (shared across many Workday tenants)
    "3M":               {"india_facet_param": "Location_Country",    "india_uuid": "c4f78be1a8f14da0ab49ce1162348a5e"},
    "NXP Semiconductors":{"india_facet_param": "Location_Country",   "india_uuid": "c4f78be1a8f14da0ab49ce1162348a5e"},
    "Autodesk":         {"india_facet_param": "locationCountry",     "india_uuid": "c4f78be1a8f14da0ab49ce1162348a5e"},
    "DXC Technology":   {"india_facet_param": "locationCountry",     "india_uuid": "c4f78be1a8f14da0ab49ce1162348a5e"},
    "Airbus":           {"india_facet_param": "locationCountry",     "india_uuid": "c4f78be1a8f14da0ab49ce1162348a5e",
                         "it_facet_param": "jobFamilyGroup", "it_uuids": ["f5811cef9cb5015323ad7f3f550a1df2"]},
    "Shell":            {"india_facet_param": "locationCountry",     "india_uuid": "c4f78be1a8f14da0ab49ce1162348a5e",
                         "it_facet_param": "jobFamilyGroup", "it_uuids": ["a87fe1bd64b8016d9c737d3fa72c300c"]},
    # Non-standard facets
    "Roche":   {"india_facet_param": "locations", "india_uuid": "54c59631019f01c479dfb787a377c235"},
    "Philips": {"india_facet_param": "locationHierarchy1", "india_uuid": "6e1b2a934716103c2adde1d57e7700ea",
                "it_facet_param": "jobFamilyGroup", "it_uuids": [
                    "94eec23a3cab01216af07777df6a8d29", "169c3da8f7270169c0ee692fbd324709",
                    "40b79030b3e0100163f33cd03cff0000", "58aeacb31cc0011e54561931bd325829",
                    "358cbd5a2fcc01e0783eb441a1012864", "a05309e84f810165f53b47218532188d",
                ]},
    # Multi-office UUID lists (no single country facet available)
    "Barclays": {"india_facet_param": "locations", "india_uuids": [
        "1110a9ca6540100196e1f0c315e90000", "112c0542820110016378a0a3e68d0000",
        "112c05428201100163788a5627320000", "253dfca5ccfc10016b1361f46cfe0000",
        "c58206e6ec7510011bb86a010cff0000", "1ab48a98eb7c1001634cf23b210c0000",
        "b8f75d1cb9781000cd91027a85e30000", "1ab48a98eb7c100163423aff71b80000",
        "112c0542820110016377af553b050000", "112c0542820110016377c02c6ef00000",
        "1ab48a98eb7c100163465bf6c3310000", "112c05428201100163763bd6ad400000",
    ]},
    "Maersk": {"india_facet_param": "locations", "india_uuids": [
        "4e4d26638c45010787a24d3a78f50000", "8df45049b43810013bfc511ded230000",
        "4e4d26638c45010787a25209b00e0000", "26c4d72049dc10009e0daf1507aa0000",
        "853120f5cc8a10009e388f5d2aec0000", "15350d48499210009e07c02b134d0000",
        "ddba4775944910009e1b192970560000", "d8801e5af43d10009dfa3a8079340000",
        "5fb6db3471ab10009df11e5466840000", "d8801e5af43d10009e0f6cca3a670000",
        "ddba4775944910009e424afe3f850000", "7a38998ecd771001354b00da72100000",
        "e27b2cd8aca310009e0d527ac7650000", "d8801e5af43d10009e04f442bf430000",
        "f37d2115b2fa1001e2ef05dbcdc00000", "614482d9d2ed1000c19c822fe2b50000",
        "e78dddcb583810009e1299afb33f0000", "5fb6db3471ab10009e1c4676598a0000",
        "d8801e5af43d10009e1bfb079d6e0000", "4140682c689310014db3b323f82e0000",
        "4e4d26638c450107879f5562654c0000", "4e4d26638c45010787a37d5e5ad00000",
        "0829310dd78f100197add0dc5cc90000", "4e4d26638c45010787a25b0edea60000",
        "4e4d26638c45010787a25f43fa5f0000", "4e4d26638c45010787a265e08d260000",
    ]},
}


# Statuses we will actually scrape
_ACTIVE = {'✅', '🟡'}


def _clean_ep(raw: str) -> str | None:
    """
    Normalise a raw endpoint cell from the markdown table:
      • Strip surrounding backticks and whitespace
      • Strip HTTP method prefix (GET, POST …)
      • Strip trailing notes after ' — ' or ' — '
      • Return None if the result is not a real URL (placeholder, '...', etc.)
    """
    s = raw.strip().strip('`').strip()
    # Remove HTTP verb prefix
    s = re.sub(r'^(GET|POST|PUT|DELETE)\s+', '', s, flags=re.IGNORECASE)
    # Remove trailing editorial notes  e.g. " — see existing scraper"
    s = re.sub(r'\s*[—–\-]{1,2}\s+.*$', '', s).strip()
    # Placeholder / incomplete URL
    if '...' in s or not s.startswith('http'):
        return None
    return s


def _is_active(status: str) -> bool:
    return any(s in status for s in _ACTIVE)


def _parse_table(lines: list[str]) -> list[dict]:
    """Convert markdown table lines → list of row dicts keyed by header."""
    header = []
    rows = []
    for line in lines:
        if not line.startswith('|'):
            if header:          # table ended
                break
            continue
        if '---' in line:       # separator row
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if not header:
            header = cells
        else:
            row = dict(zip(header, cells))
            # Some tables have an extra data column not in the header
            # (e.g. SAP section has an "India Filter" column between
            #  Scraping Endpoint and India Jobs). When the row is wider,
            # the real Status cell is the last one — fix the mapping.
            if len(cells) > len(header):
                row['Status'] = cells[-1]
            rows.append(row)
    return rows


def _section_portals(header: str, lines: list[str]) -> list[dict]:
    h = header.upper()
    rows = _parse_table(lines)

    if 'WORKDAY' in h:
        return _workday(rows)
    if 'SMARTRECRUITERS' in h:
        return _smartrecruiters(rows)
    if 'GREENHOUSE' in h:
        return _greenhouse(rows)
    if 'EIGHTFOLD' in h:
        return _eightfold(rows)
    if 'CUSTOM' in h or 'PROPRIETARY' in h:
        return _custom(rows)
    if 'SAP' in h or 'SUCCESSFACTORS' in h:
        return _sap(rows, india_only=True)
    if 'ORACLE' in h:
        return _oracle(rows)
    if 'AVATURE' in h:
        return _avature(rows)
    if 'LEVER' in h:
        return _lever(rows)
    if 'PHENOM' in h:
        return _phenom_api(rows, india_only=False)
    # Industry-organised sections (CONSULTING, BFSI, CONGLOMERATES, CONSUMER, IT, RETAIL, etc.)
    # and the catch-all OTHER section — all use the same _other() parser (Careers URL + Status).
    # These sections don't have reliable India-only filters, so india_only=False: we capture
    # all global jobs and rely on the Location field for post-scrape filtering.
    _INDUSTRY_SECTIONS = {
        'OTHER', 'CONSULTING', 'BFSI', 'CONGLOMERATE', 'CONSUMER',
        'INFORMATION TECHNOLOGY', 'RETAIL', 'PHARMA', 'REAL ESTATE',
        'ENGINEERING', 'AGRI',
    }
    if any(kw in h for kw in _INDUSTRY_SECTIONS):
        return _other(rows, india_only=False)
    return []


# ── Per-ATS parsers ───────────────────────────────────────────────────────────

def _workday(rows) -> list[Portal]:
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        tenant      = r.get('Tenant', '').strip()
        instance    = r.get('Instance', '').strip()
        career_site = r.get('Career Site', '').strip()
        # Skip rows where career_site slug is still unknown
        if not tenant or not instance or '⚠️' in career_site or not career_site:
            continue
        base = (
            f"https://{tenant}.{instance}.myworkdayjobs.com"
            f"/wday/cxs/{tenant}/{career_site}/jobs"
        )
        company = r.get('Company', '').strip()
        portal: dict = {
            'company':      company,
            'ats':          'workday',
            'endpoint':     base,
            'careers_url':  r.get('Careers URL', '').strip(),
            'tenant':       tenant,
            'instance':     instance,
            'career_site':  career_site,
            'js_required':  False,
            'status':       status,
            'industry':     _industry(company),
        }
        # Embed Workday tenant overrides so workday.py reads from portal dict,
        # not a separate global registry (Arch-Phase D1 interim step).
        reg = _WORKDAY_REGISTRY.get(company)
        if reg:
            portal['workday_search_text']  = reg.get('search_text', '')
            portal['workday_facet_param']  = reg.get('india_facet_param', '')
            portal['workday_india_uuids']  = reg.get('india_uuids') or (
                [reg['india_uuid']] if reg.get('india_uuid') else []
            )
            portal['workday_it_facet_param'] = reg.get('it_facet_param', '')
            portal['workday_it_uuids']       = reg.get('it_uuids', [])
        out.append(portal)
    return out


def _smartrecruiters(rows) -> list[Portal]:
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        sr_id   = r.get('SmartRecruiters ID', '').strip()
        company = r.get('Company', '').strip()
        # no_country_filter: country=in returns 0 for this tenant; fetch all + Python-side filter
        no_country = 'no_country_filter' in status
        endpoint = (
            f"https://api.smartrecruiters.com/v1/companies/{sr_id}/postings"
            f"?limit=100&offset=0"
            if no_country else
            f"https://api.smartrecruiters.com/v1/companies/{sr_id}/postings"
            f"?country=in&limit=100&offset=0"
        )
        out.append({
            'company':          company,
            'ats':              'smartrecruiters',
            'endpoint':         endpoint,
            'sr_id':            sr_id,
            'india_only':       no_country,
            'js_required':      False,
            'status':           status,
            'industry':         _industry(company),
        })
    return out


def _greenhouse(rows) -> list[Portal]:
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        token   = r.get('Board Token', '').strip()
        company = r.get('Company', '').strip()
        out.append({
            'company':      company,
            'ats':          'greenhouse',
            'endpoint':     f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
            'board_token':  token,
            'js_required':  False,
            'status':       status,
            'industry':     _industry(company),
        })
    return out


def _eightfold(rows) -> list[Portal]:
    """Eightfold API is broken → always use Firecrawl."""
    out = []
    for r in rows:
        status  = r.get('Status', '')
        domain  = r.get('Eightfold Domain', '').strip()
        company = r.get('Company', '').strip()
        careers_url = r.get('Careers URL', '').strip()
        out.append({
            'company':     company,
            'ats':         'eightfold',
            'endpoint':    careers_url or f"https://{domain}/careers",
            'js_required': True,
            'status':      status,
            'industry':    _industry(company),
        })
    return out


def _custom(rows) -> list[Portal]:
    out = []
    for r in rows:
        status  = r.get('Status', '')
        if not _is_active(status):
            continue
        ep      = _clean_ep(r.get('Scraping Endpoint', ''))
        careers = r.get('Careers URL', '').strip()
        endpoint = ep or careers
        js_req  = '🟡' in status or ep is None
        company = r.get('Company', '').strip()
        out.append({
            'company':      company,
            'ats':          'custom',
            'endpoint':     endpoint,
            'india_filter': r.get('India Filter', '').strip(),
            'js_required':  js_req,
            'status':       status,
            'industry':     _industry(company),
        })
    return out


def _sap(rows, india_only: bool = True) -> list[Portal]:
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        ep      = _clean_ep(r.get('Scraping Endpoint', ''))
        careers = r.get('Careers URL', '').strip()
        endpoint = ep or careers
        company  = r.get('Company', '').strip()
        out.append({
            'company':     company,
            'ats':         'sap',
            'endpoint':    endpoint,
            'js_required': ep is None,
            'status':      status,
            'industry':    _industry(company),
            'india_only':  india_only,
        })
    return out


def _oracle(rows) -> list[Portal]:
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        host    = r.get('Oracle Host', '').strip().strip('`')
        company = r.get('Company', '').strip()
        if not host or 'existing scraper' in host.lower() or not re.match(r'^[\w\.\-]+$', host):
            continue
        out.append({
            'company':     company,
            'ats':         'oracle',
            'endpoint':    (
                f"https://{host}/hcmRestApi/resources/latest"
                "/recruitingCEJobRequisitions"
                "?limit=25&offset=0&onlyData=true"
                '&q=PrimaryLocation.CountryName%3D%22India%22'
            ),
            'careers_url': r.get('Careers URL', '').strip() or None,
            'js_required': False,
            'status':      status,
            'industry':    _industry(company),
        })
    return out


def _avature(rows) -> list[Portal]:
    out = []
    for r in rows:
        status  = r.get('Status', '')
        if not _is_active(status):
            continue
        company = r.get('Company', '').strip()
        out.append({
            'company':     company,
            'ats':         'avature',
            'endpoint':    r.get('Careers URL', '').strip(),
            'js_required': True,
            'status':      status,
            'industry':    _industry(company),
        })
    return out


def _other(rows, india_only: bool = True) -> list[Portal]:
    out = []
    for r in rows:
        status  = r.get('Status', '')
        if not _is_active(status):
            continue
        js_req  = '🟡' in status or '🔍' in status
        company = r.get('Company', '').strip()
        out.append({
            'company':     company,
            'ats':         'other',
            'endpoint':    r.get('Careers URL', '').strip(),
            'js_required': js_req,
            'status':      status,
            'industry':    _industry(company),
            'india_only':  india_only,
        })
    return out


def _lever(rows) -> list[Portal]:
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        slug    = r.get('Lever Slug', '').strip()
        company = r.get('Company', '').strip()
        if not slug or '?' in slug or 'TBD' in slug.upper():
            continue
        # India-founded companies: all jobs are India, no location filter needed
        india_only = '(suspected)' not in status and 'global' not in status.lower()
        out.append({
            'company':     company,
            'ats':         'lever',
            'endpoint':    f"https://api.lever.co/v0/postings/{slug}?mode=json",
            'lever_slug':  slug,
            'js_required': False,
            'india_only':  india_only,
            'status':      status,
            'industry':    _industry(company),
        })
    return out


def _phenom_api(rows, india_only: bool = True) -> list[Portal]:
    """Phenom REST API companies — paginated JSON with full JDs."""
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        ep = _clean_ep(r.get('API Endpoint', ''))
        if not ep:
            continue
        company = r.get('Company', '').strip()
        out.append({
            'company':     company,
            'ats':         'phenom_api',
            'endpoint':    ep,
            'js_required': False,
            'status':      status,
            'industry':    _industry(company),
            'india_only':  india_only,
        })
    return out


# ── Public entry point ────────────────────────────────────────────────────────

def parse_portals(path: str = PORTALS_PATH) -> list[Portal]:
    """Return all active portals from KNOWN_PORTALS.md."""
    text = Path(path).read_text(encoding='utf-8')

    # Split on level-2 headers (## SECTION NAME)
    raw_sections = re.split(r'\n## ', '\n' + text)

    portals = []
    for section in raw_sections:
        lines = section.splitlines()
        if not lines:
            continue
        header = lines[0].lstrip('#').strip()
        # Skip meta sections (HOW TO READ, NO INDIA JOBS, SCRAPE_QUEUE, FIELD MAP)
        skip_words = {'HOW TO', 'NO INDIA', 'SCRAPE_QUEUE', 'FIELD MAP', 'KNOWN_PORTALS'}
        if any(w in header.upper() for w in skip_words):
            continue
        portals.extend(_section_portals(header, lines[1:]))

    # Remove any entries with empty company or endpoint
    portals = [p for p in portals if p.get('company') and p.get('endpoint')]
    return portals


if __name__ == '__main__':
    for p in parse_portals():
        flag = '🌐' if p['js_required'] else '⚡'
        print(f"{flag}  {p['company']:<30} [{p['ats']}]  {p['endpoint'][:70]}")
