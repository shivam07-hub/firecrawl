from __future__ import annotations

from providers.base import ProviderResult
from scrapers import scrape_smartrecruiters


class SmartRecruitersProvider:
    key = "smartrecruiters"

    def scrape(
        self,
        portal: dict,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        return ProviderResult.success(scrape_smartrecruiters(portal, max_jobs=max_jobs))
