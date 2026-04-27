"""
Provider contracts used by the modular scraper architecture.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

FALLBACK_FIRECRAWL_EXTRACT = "firecrawl_extract"


@dataclass
class ProviderResult:
    """
    Standard provider return shape.

    `fallback_policy` is set when runtime should route to a fallback provider.
    """
    jobs: list[dict]
    fallback_policy: str | None = None
    fallback_reason: str | None = None
    fallback_portal: dict | None = None

    @classmethod
    def success(cls, jobs: list[dict]) -> "ProviderResult":
        return cls(jobs=jobs)

    @classmethod
    def fallback(
        cls,
        *,
        policy: str,
        reason: str,
        portal: dict | None = None,
    ) -> "ProviderResult":
        return cls(
            jobs=[],
            fallback_policy=policy,
            fallback_reason=reason,
            fallback_portal=portal,
        )


class Provider(Protocol):
    """Provider protocol for ATS/backend-specific scraping logic."""

    key: str

    def scrape(
        self,
        portal: dict,
        *,
        max_jobs: int | None = None,
        validate_mode: bool = False,
    ) -> ProviderResult:
        ...
