"""
Firecrawl cloud API client — uses the official firecrawl-py SDK.

ONE singleton _app instance. Two permitted calls:

  scrape(url)                        → markdown str  (1 credit per URL)
  extract(urls, schema, prompt)      → structured dict (js-required portals only)
  batch_scrape(urls)                 → {url: markdown} (Workday JD fetch)

crawl() is intentionally NOT exposed — banned, too expensive (N credits per company).

Usage in scrapers.py / main.py:
    import firecrawl_client as fc
    markdown = fc.scrape(career_url)
    data     = fc.extract([career_url], schema, prompt)
"""
from firecrawl import Firecrawl
from config import FIRECRAWL_API_KEY, FIRECRAWL_URL

# ── One instance, shared across all calls ─────────────────────────────────────
# FIRECRAWL_URL=http://localhost:3002  → Docker (self-hosted, any key works)
# FIRECRAWL_URL unset or cloud URL    → Firecrawl cloud (paid API key required)
_CLOUD_DOMAINS = ("api.firecrawl.dev",)

def _is_local(url: str) -> bool:
    return bool(url) and not any(d in url for d in _CLOUD_DOMAINS)

_kwargs: dict = {"api_key": FIRECRAWL_API_KEY or "local"}
if _is_local(FIRECRAWL_URL):
    _kwargs["api_url"] = FIRECRAWL_URL
    print(f"[FC] Using Docker at {FIRECRAWL_URL}")
else:
    print(f"[FC] Using cloud API")

_app = Firecrawl(**_kwargs)

# SDK v4.22+ routes extract() to /v2/extract by default, but Docker only has /v1/extract.
# Always use the v1 client for extract so it hits /v1/extract on both Docker and cloud.
_v1 = _app._v1_client if hasattr(_app, '_v1_client') else _app


# ── Public API ────────────────────────────────────────────────────────────────

def scrape(url: str) -> str:
    """Scrape a URL via Playwright and return markdown. Works on Docker + cloud."""
    try:
        doc = _app.scrape(url, formats=["markdown"], only_main_content=True)
        return doc.markdown or ""
    except Exception as e:
        print(f"    [FC SCRAPE ERROR] {url}: {e}")
        return ""


def extract(urls: list[str], schema: dict, prompt: str) -> dict:
    """
    LLM-powered structured extraction via /v1/extract (Docker-compatible).
    Use only for js-required portals where no direct ATS API is available.
    Returns {} on failure.
    """
    try:
        result = _v1.extract(urls, prompt=prompt, schema=schema)
        # extract() returns the extracted data directly (typed or dict)
        if hasattr(result, "model_dump"):
            return result.model_dump(exclude_none=True)
        if isinstance(result, dict):
            return result.get("data") or result
        return {}
    except Exception as e:
        print(f"    [FC EXTRACT ERROR] {urls}: {e}")
        return {}


def batch_scrape(urls: list[str]) -> dict[str, str]:
    """
    Scrape multiple URLs in one SDK call (e.g. Workday individual JD pages).
    Returns {url: markdown}. Each URL costs 1 credit — use sparingly.
    """
    if not urls:
        return {}
    try:
        results = _app.batch_scrape(urls, formats=["markdown"], only_main_content=True)
        out = {}
        # batch_scrape returns a BatchScrapeResponse; iterate its data list
        pages = getattr(results, "data", None) or []
        for doc in pages:
            url = getattr(getattr(doc, "metadata", None), "url", None) or ""
            md  = getattr(doc, "markdown", None) or ""
            if url and md:
                out[url] = md
        return out
    except Exception as e:
        print(f"    [FC BATCH ERROR] {len(urls)} URLs: {e}")
        return {}
