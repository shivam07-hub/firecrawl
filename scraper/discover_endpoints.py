"""
discover_endpoints.py — Use Firecrawl to find the real job-listing URLs
for companies currently using generic homepage endpoints in KNOWN_PORTALS.md.

For each js-required 'other' company, scrapes the careers homepage and looks for:
  - ATS platform links (workday, greenhouse, smartrecruiters, lever, ashby, etc.)
  - India-filtered job search URLs
  - /jobs/, /careers/jobs, /openings, /positions patterns

Usage:
    python discover_endpoints.py                    # all js-required 'other' companies
    python discover_endpoints.py --company "HSBC"   # single company
    python discover_endpoints.py --confirm          # write findings back to KNOWN_PORTALS.md
"""
import argparse
import re
import sys
from pathlib import Path

import firecrawl_client as fc
from portal_reader import parse_portals

# ── ATS platform patterns to detect in links ─────────────────────────────────
ATS_PATTERNS = [
    (r'[\w\-]+\.wd\d+\.myworkdayjobs\.com',           'workday'),
    (r'boards\.greenhouse\.io|jobs\.lever\.co',        'greenhouse/lever'),
    (r'api\.smartrecruiters\.com|careers\.smartrecruiters\.com', 'smartrecruiters'),
    (r'[\w\-]+\.eightfold\.ai',                        'eightfold'),
    (r'jobs\.ashbyhq\.com',                            'ashby'),
    (r'apply\.workable\.com',                          'workable'),
    (r'icims\.com|phenom\.com',                        'icims/phenom'),
    (r'taleo\.net|oraclecloud\.com',                   'oracle/taleo'),
    (r'successfactors\.com|jobs2web\.com',             'sap'),
    (r'myrecruitment\+\.com|jobvite\.com',             'jobvite'),
]

# ── URL patterns that indicate a job listing page ────────────────────────────
JOB_URL_PATTERNS = [
    r'/jobs[/\?]',
    r'/careers/jobs',
    r'/careers/search',
    r'/open-positions',
    r'/openings',
    r'/search-jobs',
    r'/job-search',
    r'SearchJobs',
    r'search-results',
    r'locationsearch=India',
    r'location=India',
    r'country=India',
    r'qcountry=India',
    r'country=IN\b',
    r'/india[/\?]',
    r'\?.*india',
]

# Skip these generic/noisy patterns
SKIP_PATTERNS = [
    r'\.(png|jpg|jpeg|gif|svg|webp|ico|pdf|css|js)(\?|$)',
    r'#',
    r'mailto:',
    r'linkedin\.com',
    r'twitter\.com|x\.com',
    r'facebook\.com',
    r'instagram\.com',
    r'youtube\.com',
]


def _extract_links(markdown: str, base_url: str) -> list[str]:
    """Extract all URLs from markdown link syntax [text](url)."""
    links = re.findall(r'\]\((https?://[^\s\)]+)\)', markdown)
    # Also grab bare URLs
    links += re.findall(r'(?<!\()(https?://[^\s\)\]"\'<>]+)', markdown)
    # Deduplicate, skip noise
    seen = set()
    out = []
    for url in links:
        url = url.rstrip('.,;)')
        if url in seen:
            continue
        seen.add(url)
        if any(re.search(p, url, re.I) for p in SKIP_PATTERNS):
            continue
        out.append(url)
    return out


def _classify_link(url: str) -> tuple[str | None, str | None]:
    """
    Returns (ats_type, reason) if the URL is useful, else (None, None).
    ats_type: 'workday' | 'greenhouse' | ... | 'job_page' | None
    reason: short description of why this URL is interesting
    """
    url_lower = url.lower()

    # ATS platform detection
    for pattern, ats in ATS_PATTERNS:
        if re.search(pattern, url, re.I):
            return ats, f"ATS platform: {ats}"

    # Job listing page patterns
    for pattern in JOB_URL_PATTERNS:
        if re.search(pattern, url, re.I):
            return 'job_page', f"job listing URL pattern: {pattern}"

    return None, None


def discover(company_name: str, current_url: str) -> dict:
    """
    Scrape `current_url` and return a findings dict:
      {
        'company': str,
        'current_url': str,
        'ats_links': [(url, ats_type, reason), ...],
        'job_links': [(url, reason), ...],
        'markdown_len': int,
        'error': str | None,
      }
    """
    print(f"  Scraping {current_url} ...", flush=True)
    md = fc.scrape(current_url)

    if not md:
        return {
            'company': company_name, 'current_url': current_url,
            'ats_links': [], 'job_links': [], 'markdown_len': 0,
            'error': 'Firecrawl returned empty markdown',
        }

    links = _extract_links(md, current_url)
    ats_links = []
    job_links = []

    for url in links:
        ats_type, reason = _classify_link(url)
        if ats_type == 'job_page':
            job_links.append((url, reason))
        elif ats_type:
            ats_links.append((url, ats_type, reason))

    return {
        'company': company_name,
        'current_url': current_url,
        'ats_links': ats_links,
        'job_links': job_links,
        'markdown_len': len(md),
        'error': None,
    }


def _best_url(findings: dict) -> tuple[str | None, str | None]:
    """
    Pick the single best candidate URL from findings.
    Priority: ATS platform link > India job_link > generic job_link
    Returns (url, reason).
    """
    # Prefer ATS platform links
    if findings['ats_links']:
        url, ats_type, reason = findings['ats_links'][0]
        return url, f"{ats_type} ATS detected"

    # Prefer India-specific job links
    india_links = [
        (u, r) for u, r in findings['job_links']
        if re.search(r'india', u, re.I)
    ]
    if india_links:
        return india_links[0][0], "India-specific job listing page"

    # Generic job links
    if findings['job_links']:
        return findings['job_links'][0][0], findings['job_links'][0][1]

    return None, None


def print_findings(findings: dict) -> None:
    c = findings['company']
    if findings['error']:
        print(f"  [{c}] ERROR: {findings['error']}")
        return

    best_url, best_reason = _best_url(findings)

    print(f"  [{c}]  markdown: {findings['markdown_len']} chars")

    if findings['ats_links']:
        print(f"    ATS links found:")
        for url, ats, _ in findings['ats_links'][:3]:
            print(f"      {ats:<20} {url[:80]}")

    if findings['job_links']:
        print(f"    Job listing links found:")
        for url, _ in findings['job_links'][:3]:
            print(f"      {url[:80]}")

    if best_url:
        print(f"    ✅ BEST CANDIDATE: {best_url}")
        print(f"       Reason: {best_reason}")
    else:
        print(f"    ❌ No useful links found — page may be fully JS-rendered or block Firecrawl")

    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--company', help='Filter by company name (substring)')
    parser.add_argument('--confirm', action='store_true',
                        help='Print KNOWN_PORTALS.md update suggestions')
    args = parser.parse_args()

    # Only test js-required 'other' companies (ones with generic homepage URLs)
    portals = parse_portals()
    targets = [
        p for p in portals
        if p['ats'] == 'other' and p['js_required']
    ]
    if args.company:
        targets = [p for p in targets if args.company.lower() in p['company'].lower()]

    print(f"Discovering endpoints for {len(targets)} js-required 'other' companies\n")

    all_findings = []
    for p in targets:
        findings = discover(p['company'], p['endpoint'])
        print_findings(findings)
        all_findings.append(findings)

    # Summary
    found = [(f['company'], *(_best_url(f))) for f in all_findings if _best_url(f)[0]]
    not_found = [f['company'] for f in all_findings if not _best_url(f)[0]]

    print("=" * 70)
    print(f"SUMMARY: {len(found)} companies with better URLs, {len(not_found)} still blocked\n")

    if found:
        print("✅ Found better endpoints:")
        for company, url, reason in found:
            print(f"  {company:<35} {reason}")
            print(f"    → {url}")
        print()

    if not_found:
        print("❌ No useful links found (fully JS-rendered or blocked):")
        for c in not_found:
            print(f"  {c}")


if __name__ == '__main__':
    main()
