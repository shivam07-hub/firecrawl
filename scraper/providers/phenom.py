from __future__ import annotations

from providers.base import ProviderResult
from scrapers import scrape_phenom_api


class PhenomProvider:
    key = "phenom_api"

    def scrape(
        self,
        portal: dict,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        return ProviderResult.success(scrape_phenom_api(portal, max_jobs=max_jobs))
