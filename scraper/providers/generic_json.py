from __future__ import annotations

from providers.base import FALLBACK_FIRECRAWL_EXTRACT, ProviderResult
from scrapers import scrape_get


class GenericJSONProvider:
    key = "generic_json"

    def scrape(
        self,
        portal: dict,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        raw = scrape_get(portal, max_jobs=max_jobs)

        # custom / sap / oracle / other: direct GET fallback when HTML response
        if raw and raw[0].get("_needs_firecrawl"):
            return ProviderResult.fallback(
                policy=FALLBACK_FIRECRAWL_EXTRACT,
                reason="generic_get_requires_firecrawl",
                portal=portal,
            )

        # Oracle HCM REST can be auth-gated; keep historical fallback behavior.
        if not raw and portal.get("ats") == "oracle" and portal.get("careers_url"):
            fc_portal = {**portal, "endpoint": portal["careers_url"]}
            return ProviderResult.fallback(
                policy=FALLBACK_FIRECRAWL_EXTRACT,
                reason="oracle_api_empty_fallback_careers_url",
                portal=fc_portal,
            )

        return ProviderResult.success(raw)
