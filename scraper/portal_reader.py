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
import re
from pathlib import Path
from config import PORTALS_PATH

# ── Static industry lookup ─────────────────────────────────────────────────────
# Maps company name (as it appears in KNOWN_PORTALS.md) → industry sector string.
# Used to stamp the 'industry' field on every job produced by that portal.
# Update this dict when adding new companies.

COMPANY_INDUSTRY = {
    # ── Existing portals ──────────────────────────────────────────────────────
    "Accenture":                    "IT Services",
    "Airbus":                       "Aerospace & Defense",
    "Chanel":                       "Consumer Goods",
    "Eli Lilly":                    "Pharmaceutical",
    "Engie":                        "Energy",
    "Fidelity Investments":         "BFSI",
    "Mastercard":                   "BFSI",
    "Novartis":                     "Pharmaceutical",
    "Salesforce":                   "Technology",
    "Sanofi":                       "Pharmaceutical",
    "Shell":                        "Energy",
    "Synopsys":                     "Technology",
    "Wells Fargo":                  "BFSI",
    "Philips":                      "Healthcare Technology",
    "Continental":                  "Automotive",
    "LDC (Louis Dreyfus)":          "Commodities & Trading",
    "ServiceNow":                   "Technology",
    "Atlassian":                    "Technology",
    "Stripe":                       "Fintech",
    "American Express":             "BFSI",
    "Morgan Stanley":               "BFSI",
    "STMicroelectronics":           "Semiconductors",
    "Amazon":                       "E-commerce & Technology",
    "Apple":                        "Technology",
    "Cognizant":                    "IT Services",
    "Google":                       "Technology",
    "Infosys":                      "IT Services",
    "L'Oréal":                      "Consumer Goods",
    "Microsoft":                    "Technology",
    "Stellantis":                   "Automotive",
    "Wipro":                        "IT Services",
    "TCS":                          "IT Services",
    "Alstom":                       "Engineering & Infrastructure",
    "CMA CGM":                      "Shipping & Logistics",
    "CNHI":                         "Industrial",
    "Volvo Group":                  "Automotive",
    "Schneider Electric":           "Energy & Industrial",
    "TotalEnergies":                "Energy",
    "AstraZeneca":                  "Pharmaceutical",
    "Baker Hughes":                 "Energy",
    "Cisco":                        "Technology",
    "Dell":                         "Technology",
    "Michelin":                     "Automotive",
    "SAP":                          "Technology",
    "Tech Mahindra":                "IT Services",
    "Air France":                   "Aviation",
    "Technip Energies":             "Energy",
    "Goldman Sachs":                "BFSI",
    "IBM":                          "Technology",
    # ── Hyderabad GCC additions (2026-04-19) ──────────────────────────────────
    "JP Morgan Chase":              "BFSI",
    "Dr. Reddy's":                  "Pharmaceutical",
    "Micron Technology":            "Semiconductors",
    "AMD":                          "Semiconductors",
    "Qualcomm":                     "Semiconductors",
    "Boeing":                       "Aerospace & Defense",
    "ZF Lifetec":                   "Automotive",
    "Bosch":                        "Automotive",
    "HMIE":                         "Automotive",
    "Deloitte India":               "Consulting",
    "Intel":                        "Semiconductors",
    "State Street":                 "BFSI",
    "Uber":                         "Mobility",
    "EA":                           "Gaming & Technology",
    "EA (Electronic Arts)":         "Gaming & Technology",
    "DBS Bank":                     "BFSI",
    "Medtronic":                    "Healthcare",
    "GE Aerospace":                 "Engineering",
    "Siemens":                      "Engineering",
    "Honeywell":                    "Engineering",
    "BlackBerry":                   "Technology",
    "CyberArk":                     "Cybersecurity",
    "Storable":                     "Technology",
    "Align Technology":             "Medical Devices",
    "Mondee Holdings":              "Travel Technology",
    "Lloyds Banking Group":         "BFSI",
    "Inspire Brands":               "Hospitality",
    "Syneriq Global":               "Technology",
    "Bank of America":              "BFSI",
    "Oracle":                       "Technology",
    # ── Agri Inputs ───────────────────────────────────────────────────────────
    "Coromandel International":     "Agri Inputs",
    # ── BFSI – Investment Banking & Asset Management ──────────────────────────
    "ARGA Investment Management":   "BFSI",
    "Arpwood Capital":              "BFSI",
    "Avendus Capital":              "BFSI",
    "Claypond Capital":             "BFSI",
    "Deutsche Bank":                "BFSI",
    "Elevation Capital":            "BFSI",
    "Everstone Capital":            "BFSI",
    "General Atlantic":             "BFSI",
    "HSBC":                         "BFSI",
    "O3 Capital":                   "BFSI",
    "Premji Invest":                "BFSI",
    "Standard Chartered Bank":      "BFSI",
    "UBS":                          "BFSI",
    "SBI Mutual Fund":              "BFSI",
    "Integrow Asset Management":    "BFSI",
    # ── BFSI – Banking & Finance ──────────────────────────────────────────────
    "Bank of India":                "BFSI",
    "Credila":                      "BFSI",
    "CRISIL":                       "BFSI",
    "IIFL Finance":                 "BFSI",
    "IndusInd Bank":                "BFSI",
    "L&T Finance":                  "BFSI",
    "Navi Technologies":            "Fintech",
    "S&P Global":                   "BFSI",
    "FinIQ":                        "Fintech",
    # ── Conglomerates ─────────────────────────────────────────────────────────
    "Adani Group":                  "Conglomerates",
    "Aditya Birla Group":           "Conglomerates",
    "CK Birla Group":               "Conglomerates",
    "GMR Group":                    "Conglomerates",
    "Lodha Ventures":               "Conglomerates",
    "Tata Administrative Services": "Conglomerates",
    # ── Consulting ────────────────────────────────────────────────────────────
    "Accenture Strategy":           "Consulting",
    "Bain & Company":               "Consulting",
    "Black Brix":                   "Consulting",
    "BCG":                          "Consulting",
    "EY Parthenon":                 "Consulting",
    "FinIQ Consulting":             "Consulting",
    "Kearney":                      "Consulting",
    "L.E.K. Consulting":            "Consulting",
    "McKinsey & Company":           "Consulting",
    "Monitor Deloitte":             "Consulting",
    "Oliver Wyman":                 "Consulting",
    "Practus":                      "Consulting",
    "Praxis Global Alliance":       "Consulting",
    "PwC":                          "Consulting",
    "Simon-Kucher & Partners":      "Consulting",
    "Showtime Consulting":          "Consulting",
    "Strategy&":                    "Consulting",
    "Takshashila Consulting":       "Consulting",
    "TransformationX":              "Consulting",
    "Vector Consulting Group":      "Consulting",
    # ── Consumer Goods (FMCG) ─────────────────────────────────────────────────
    "Dabur":                        "Consumer Goods",
    "Haleon":                       "Consumer Goods",
    "Philip Morris International":  "Consumer Goods",
    "United Breweries":             "Consumer Goods",
    "Wipro Consumer Care":          "Consumer Goods",
    # ── Consumer Services ─────────────────────────────────────────────────────
    "OYO":                          "Consumer Services",
    "Zomato":                       "Consumer Services",
    # ── E-commerce ────────────────────────────────────────────────────────────
    "Myntra":                       "E-commerce",
    "Nykaa":                        "E-commerce",
    "Purplle":                      "E-commerce",
    # ── Engineering / Technology ──────────────────────────────────────────────
    "HCL Software":                 "Technology",
    "Vehere Interactive":           "Technology",
    # ── Information Technology ────────────────────────────────────────────────
    "BrowserStack":                 "Technology",
    "Coforge":                      "IT Services",
    "EXL Digital":                  "IT Services",
    "HiLabs":                       "Healthcare Technology",
    "Sanas":                        "Technology",
    "Yubi":                         "Fintech",
    # ── Retail ────────────────────────────────────────────────────────────────
    "Bluestone Jewellery":          "Retail",
    "Welspun":                      "Retail",
    # ── Pharmaceutical / Healthcare ───────────────────────────────────────────
    "Mankind Pharma":               "Pharmaceutical",
    # ── Real Estate ───────────────────────────────────────────────────────────
    "Arvind SmartSpaces":           "Real Estate",
    "Lodha Group":                  "Real Estate",
    # ── Bengaluru MNCs & Startups (2026-04-19) ────────────────────────────────
    "3M":                           "Industrial & Technology",
    "Juniper Networks":             "Technology",
    "Texas Instruments":            "Semiconductors",
    "ARM Holdings":                 "Semiconductors",
    "NXP Semiconductors":           "Semiconductors",
    "Autodesk":                     "Technology",
    "Keysight Technologies":        "Technology",
    "Rakuten India":                "Technology",
    "Nokia":                        "Technology",
    "Telefonica":                   "Telecommunications",
    "Roche":                        "Pharmaceutical",
    "ABB":                          "Engineering & Industrial",
    "BNY Mellon":                   "BFSI",
    "ANZ Bank":                     "BFSI",
    "Societe Generale":             "BFSI",
    "ING Bank":                     "BFSI",
    "Barclays":                     "BFSI",
    "Credit Suisse":                "BFSI",
    "Maersk":                       "Shipping & Logistics",
    "Ola Electric":                 "EV & Mobility",
    "Swiggy":                       "Consumer Services",
    "Flipkart":                     "E-commerce",
    "Meesho":                       "E-commerce",
    "CRED":                         "Fintech",
    "Razorpay":                     "Fintech",
    "Freshworks":                   "Technology",
    "Zoho":                         "Technology",
    "Tata Elxsi":                   "Engineering & Technology",
    "L&T Infotech":                 "IT Services",
    "Mindtree":                     "IT Services",
    "LTIMindtree":                  "IT Services",
    "Publicis Sapient":             "IT Services",
    "ZS Associates":                "Consulting",
    "Thoughtworks":                 "IT Services",
    "Virtusa":                      "IT Services",
    "Mu Sigma":                     "Analytics",
    "InMobi":                       "Technology",
    "PhonePe":                      "Fintech",
    "Paytm":                        "Fintech",
    "DXC Technology":               "IT Services",
    "Spotify":                      "Media & Entertainment",
}


def _industry(company: str) -> str:
    """Look up the industry for a company name. Returns '' if unknown."""
    return COMPANY_INDUSTRY.get(company, '')


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
        return _sap(rows, india_only=False)
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

def _workday(rows):
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
        out.append({
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
        })
    return out


def _smartrecruiters(rows):
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


def _greenhouse(rows):
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


def _eightfold(rows):
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


def _custom(rows):
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


def _sap(rows, india_only: bool = True):
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


def _oracle(rows):
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


def _avature(rows):
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


def _other(rows, india_only: bool = True):
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


def _lever(rows):
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


def _phenom_api(rows, india_only: bool = True):
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

def parse_portals(path: str = PORTALS_PATH) -> list[dict]:
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
