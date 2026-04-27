from __future__ import annotations

from providers.base import FALLBACK_FIRECRAWL_EXTRACT, ProviderResult
from scrapers import scrape_workday


class WorkdayProvider:
    key = "workday"

    def scrape(
        self,
        portal: dict,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        jobs = scrape_workday(portal, max_jobs=max_jobs)
        if jobs is None:
            fallback_portal = dict(portal)
            if portal.get("careers_url"):
                fallback_portal["endpoint"] = portal["careers_url"]
            return ProviderResult.fallback(
                policy=FALLBACK_FIRECRAWL_EXTRACT,
                reason="workday_api_blocked",
                portal=fallback_portal,
            )
        return ProviderResult.success(jobs)
