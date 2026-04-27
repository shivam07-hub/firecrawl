from __future__ import annotations

from providers.base import ProviderResult
from scrapers import scrape_lever


class LeverProvider:
    key = "lever"

    def scrape(
        self,
        portal: dict,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        return ProviderResult.success(scrape_lever(portal, max_jobs=max_jobs))
