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
# Arch-Phase D1: data lives in workday_registry.json — edit that file, not here.
_WORKDAY_REGISTRY_PATH = Path(__file__).parent / "workday_registry.json"
_WORKDAY_REGISTRY: dict[str, dict] | None = None


def _load_workday_registry() -> dict[str, dict]:
    global _WORKDAY_REGISTRY
    if _WORKDAY_REGISTRY is None:
        if _WORKDAY_REGISTRY_PATH.exists():
            raw = json.loads(_WORKDAY_REGISTRY_PATH.read_text(encoding="utf-8"))
            _WORKDAY_REGISTRY = {k: v for k, v in raw.items() if not k.startswith("_")}
        else:
            print(f"  [WARN] workday_registry.json not found at {_WORKDAY_REGISTRY_PATH}; Workday tenant overrides disabled")
            _WORKDAY_REGISTRY = {}
    return _WORKDAY_REGISTRY


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
    if 'ICIMS' in h:
        return _icims_custom(rows)
    if 'DARWINBOX' in h:
        return _darwinbox(rows)
    if 'MYNEXTHIRE' in h:
        return _mynexthire(rows)
    if 'SPIRE2GROW' in h:
        return _spire2grow(rows)
    if 'ZWAYAM' in h:
        return _zwayam(rows)
    if 'TALEO' in h:
        return _taleo(rows)
    if 'MCKINSEY' in h:
        return _mckinsey(rows)
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
    if 'PCSX' in h or 'PHENOM CX' in h:
        return _pcsx(rows)
    if 'PHENOM' in h:
        return _phenom_api(rows, india_only=False)
    if 'PINPOINT' in h:
        return _pinpoint(rows)
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
        # Embed Workday tenant overrides from workday_registry.json (Arch-Phase D1).
        reg = _load_workday_registry().get(company)
        if reg:
            portal['workday_search_text']  = reg.get('search_text', '')
            portal['workday_facet_param']  = reg.get('india_facet_param', '')
            portal['workday_india_uuids']  = reg.get('india_uuids') or (
                [reg['india_uuid']] if reg.get('india_uuid') else []
            )
            portal['workday_it_facet_param'] = reg.get('it_facet_param', '')
            portal['workday_it_uuids']       = reg.get('it_uuids', [])
            # blocked=true: Cloudflare blocks all POSTs — skip API, go straight to Firecrawl
            if reg.get('blocked'):
                portal['workday_blocked'] = True
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
    out = []
    for r in rows:
        status      = r.get('Status', '')
        ef_domain   = r.get('Eightfold Domain', '').strip()   # e.g. netflix.eightfold.ai
        api_domain  = r.get('API Domain', '').strip()         # e.g. netflix.com
        company     = r.get('Company', '').strip()
        careers_url = r.get('Careers URL', '').strip()
        if not _is_active(status):
            continue
        # Derive tenant from Eightfold Domain (strip .eightfold.ai suffix)
        tenant = ef_domain.replace('.eightfold.ai', '').strip()
        # Use direct API if we have tenant + api_domain; otherwise Firecrawl
        has_api = bool(tenant and api_domain)
        out.append({
            'company':           company,
            'ats':               'eightfold',
            'endpoint':          careers_url or f"https://{ef_domain}/careers",
            'js_required':       not has_api,
            'eightfold_tenant':  tenant,
            'eightfold_domain':  api_domain,
            'status':            status,
            'industry':          _industry(company),
        })
    return out


# Per-company overrides for iCIMS Custom portals that deviate from the default
# country=India filter (e.g. portals that use location=india instead).
_ICIMS_OVERRIDES: dict[str, dict] = {
    "Keysight Technologies": {"icims_location_param": "location"},
}


def _icims_custom(rows) -> list[Portal]:
    out = []
    for r in rows:
        status      = r.get('Status', '')
        if not _is_active(status):
            continue
        company     = r.get('Company', '').strip()
        careers_url = r.get('Careers URL', '').strip()
        portal: Portal = {
            'company':     company,
            'ats':         'icims_custom',
            'endpoint':    careers_url,
            'careers_url': careers_url,
            'js_required': False,
            'india_only':  True,
            'status':      status,
            'industry':    _industry(company),
        }
        portal.update(_ICIMS_OVERRIDES.get(company, {}))
        out.append(portal)
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


_ORACLE_EXPAND = (
    "requisitionList.workLocation,"
    "requisitionList.otherWorkLocations,"
    "requisitionList.secondaryLocations,"
    "flexFieldsFacet.values,"
    "requisitionList.requisitionFlexFields"
)
_ORACLE_FACETS = (
    "LOCATIONS%3BWORK_LOCATIONS%3BWORKPLACE_TYPES%3BTITLES%3B"
    "CATEGORIES%3BORGANIZATIONS%3BPOSTING_DATES%3BFLEX_FIELDS"
)


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

        site_num  = r.get('Site Number', '').strip()
        loc_id    = r.get('India Location ID', '').strip()
        base      = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"

        if site_num:
            # Cracked: use finder=findReqs; locationId optional (omit for India-only portals)
            loc_filter = f",locationId={loc_id}" if loc_id else ""
            endpoint = (
                f"{base}?onlyData=true&expand={_ORACLE_EXPAND}"
                f"&finder=findReqs;siteNumber={site_num},"
                f"facetsList={_ORACLE_FACETS},"
                f"limit=25{loc_filter},sortBy=POSTING_DATES_DESC"
            )
            oracle_nested = True
        else:
            endpoint = f"{base}?limit=25&offset=0&onlyData=true"
            oracle_nested = False

        out.append({
            'company':       company,
            'ats':           'oracle',
            'endpoint':      endpoint,
            'oracle_nested': oracle_nested,
            'india_only':    True,
            'careers_url':   r.get('Careers URL', '').strip() or None,
            'js_required':   False,
            'status':        status,
            'industry':      _industry(company),
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


_ATS_OVERRIDES: dict[str, str] = {
    'Aditya Birla Group':    'aditya_birla',
    'McKinsey & Company':    'mckinsey',
    'Standard Chartered Bank': 'taleo',
}

_TALEO_V1: set[str] = {'Standard Chartered Bank'}


def _other(rows, india_only: bool = True) -> list[Portal]:
    out = []
    for r in rows:
        status  = r.get('Status', '')
        if not _is_active(status):
            continue
        company = r.get('Company', '').strip()
        ats     = _ATS_OVERRIDES.get(company, 'other')
        js_req  = '🟡' in status or '🔍' in status
        portal: dict = {
            'company':     company,
            'ats':         ats,
            'endpoint':    r.get('Careers URL', '').strip(),
            'js_required': js_req,
            'status':      status,
            'industry':    _industry(company),
            'india_only':  india_only,
        }
        if company in _TALEO_V1:
            portal['taleo_v1'] = True
        out.append(portal)
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


def _pcsx(rows) -> list[Portal]:
    """Phenom CX (pcsx) — list API + per-job HTML JSON-LD for full JD."""
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        company = r.get('Company', '').strip()
        base_url = r.get('Base URL', '').strip().rstrip('/')
        pcsx_domain = r.get('Domain', '').strip()
        if not base_url or not pcsx_domain:
            continue
        out.append({
            'company':     company,
            'ats':         'pcsx',
            'endpoint':    base_url,
            'careers_url': r.get('Careers URL', '').strip(),
            'pcsx_domain': pcsx_domain,
            'js_required': False,
            'status':      status,
            'industry':    _industry(company),
        })
    return out


def _darwinbox(rows) -> list[Portal]:
    """Darwinbox ATS — CF-protected POST API; falls back to Firecrawl without cookies."""
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        company = r.get('Company', '').strip()
        careers_url = r.get('Careers URL', '').strip()
        if not careers_url:
            continue
        out.append({
            'company':    company,
            'ats':        'darwinbox',
            'endpoint':   careers_url,
            'careers_url': careers_url,
            'js_required': False,
            'status':     status,
            'industry':   _industry(company),
        })
    return out


def _mynexthire(rows) -> list[Portal]:
    """MyNextHire ATS — POST per-category API; workspaceid + tenant from portal config."""
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        company     = r.get('Company', '').strip()
        careers_url = r.get('Careers URL', '').strip()
        tenant      = r.get('Tenant Domain', '').strip()
        workspace   = r.get('Workspace ID', '').strip()
        if not careers_url:
            continue
        out.append({
            'company':                  company,
            'ats':                      'mynexthire',
            'endpoint':                 careers_url,
            'careers_url':              careers_url,
            'mynexthire_tenant':        tenant,
            'js_required':              False,
            'india_only':               True,
            'status':                   status,
            'industry':                 _industry(company),
        })
    return out


def _spire2grow(rows) -> list[Portal]:
    """Spire2Grow / IES ATS — GET with workspaceid header."""
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        company      = r.get('Company', '').strip()
        careers_url  = r.get('Careers URL', '').strip()
        workspace_id = r.get('Workspace ID', '').strip()
        workflow_id  = r.get('Workflow ID', '').strip()
        if not careers_url or not workspace_id:
            continue
        out.append({
            'company':                   company,
            'ats':                       'spire2grow',
            'endpoint':                  careers_url,
            'careers_url':               careers_url,
            'spire2grow_workspace_id':   workspace_id,
            'spire2grow_workflow_id':    workflow_id,
            'js_required':               False,
            'india_only':                True,
            'status':                    status,
            'industry':                  _industry(company),
        })
    return out


def _zwayam(rows) -> list[Portal]:
    """Zwayam ATS — multipart POST with companyId (base64) and domain."""
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        company    = r.get('Company', '').strip()
        careers_url = r.get('Careers URL', '').strip()
        domain     = r.get('Zwayam Domain', '').strip()
        company_id = r.get('Company ID (b64)', '').strip()
        if not careers_url or not company_id:
            continue
        out.append({
            'company':           company,
            'ats':               'zwayam',
            'endpoint':          careers_url,
            'careers_url':       careers_url,
            'zwayam_domain':     domain,
            'zwayam_company_id': company_id,
            'js_required':       False,
            'india_only':        True,
            'status':            status,
            'industry':          _industry(company),
        })
    return out


def _taleo(rows) -> list[Portal]:
    """Oracle Taleo TBE — POST /services/jobs/search/ with locationsearch=india."""
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        company     = r.get('Company', '').strip()
        careers_url = r.get('Careers URL', '').strip()
        if not careers_url:
            continue
        out.append({
            'company':     company,
            'ats':         'taleo',
            'endpoint':    careers_url,
            'careers_url': careers_url,
            'js_required': False,
            'india_only':  True,
            'status':      status,
            'industry':    _industry(company),
        })
    return out


def _mckinsey(rows) -> list[Portal]:
    """McKinsey gateway API — GET with countries=India param."""
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        company     = r.get('Company', '').strip()
        careers_url = r.get('Careers URL', '').strip()
        if not careers_url:
            continue
        out.append({
            'company':     company,
            'ats':         'mckinsey',
            'endpoint':    careers_url,
            'careers_url': careers_url,
            'js_required': False,
            'india_only':  True,
            'status':      status,
            'industry':    _industry(company),
        })
    return out


def _pinpoint(rows) -> list[Portal]:
    """Pinpoint ATS — /en/postings.json with location_id[] India filter."""
    out = []
    for r in rows:
        status = r.get('Status', '')
        if not _is_active(status):
            continue
        company = r.get('Company', '').strip()
        base_url = r.get('Base URL', '').strip().rstrip('/')
        india_ids_raw = r.get('India Location IDs', '').strip()
        if not base_url or not india_ids_raw:
            continue
        india_ids = [i.strip() for i in india_ids_raw.split(',') if i.strip()]
        out.append({
            'company':                     company,
            'ats':                         'pinpoint',
            'endpoint':                    base_url,
            'careers_url':                 r.get('Careers URL', '').strip(),
            'pinpoint_india_location_ids': india_ids,
            'js_required':                 False,
            'status':                      status,
            'industry':                    _industry(company),
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
