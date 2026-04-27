from __future__ import annotations

from providers.base import ProviderResult
from scrapers import scrape_extract, scrape_validate


class FirecrawlJSProvider:
    key = "firecrawl_js"

    def scrape(
        self,
        portal: dict,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        if validate_mode:
            jobs = scrape_validate(portal, max_jobs=max_jobs or 5)
        else:
            jobs = scrape_extract(portal, max_jobs=max_jobs)
        return ProviderResult.success(jobs)
