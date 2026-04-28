from __future__ import annotations

from schema import Portal

import logging

from providers.base import FALLBACK_FIRECRAWL_EXTRACT, Provider, ProviderResult, ScrapeReason
from providers.firecrawl_js import FirecrawlJSProvider
from providers.generic_json import GenericJSONProvider
from providers.greenhouse import GreenhouseProvider
from providers.lever import LeverProvider
from providers.phenom import PhenomProvider
from providers.smartrecruiters import SmartRecruitersProvider
from providers.workday import WorkdayProvider

_FIRECRAWL_PROVIDER = FirecrawlJSProvider()
_GENERIC_PROVIDER = GenericJSONProvider()

_ATS_PROVIDERS: dict[str, Provider] = {
    "workday": WorkdayProvider(),
    "smartrecruiters": SmartRecruitersProvider(),
    "greenhouse": GreenhouseProvider(),
    "lever": LeverProvider(),
    "phenom_api": PhenomProvider(),
}


def _provider_for_portal(portal: Portal) -> Provider:
    if portal.get("js_required"):
        return _FIRECRAWL_PROVIDER
    return _ATS_PROVIDERS.get(portal.get("ats", ""), _GENERIC_PROVIDER)


def _run_firecrawl_extract(
    portal: Portal,
    log: logging.Logger,
    *,
    max_jobs: int | None,
    validate_mode: bool,
) -> list[dict]:
    company = portal["company"]
    result = _FIRECRAWL_PROVIDER.scrape(
        portal,
        max_jobs=max_jobs,
        validate_mode=validate_mode,
    )
    jobs = result.jobs
    if jobs:
        log.info(f"    Firecrawl {'scrape' if validate_mode else 'extract'}: {len(jobs)} entries")
    else:
        log.warning(f"    Firecrawl returned 0 for {company}")
    return jobs


def _apply_fallback(
    result: ProviderResult,
    portal: Portal,
    log: logging.Logger,
    *,
    max_jobs: int | None,
    validate_mode: bool,
) -> list[dict]:
    if result.fallback_policy != FALLBACK_FIRECRAWL_EXTRACT:
        return result.jobs

    fallback_portal = result.fallback_portal or portal
    reason = result.fallback_reason or "fallback_requested"

    if reason == "workday_api_blocked":
        log.info("    Workday direct API blocked -> falling back to Firecrawl")
    elif reason == "oracle_api_empty_fallback_careers_url":
        log.info("    Oracle REST returned 0 -> falling back to Firecrawl on careers_url")
    else:
        log.info(f"    Provider fallback -> Firecrawl ({reason})")

    return _run_firecrawl_extract(
        fallback_portal,
        log,
        max_jobs=max_jobs,
        validate_mode=validate_mode,
    )


def dispatch_scrape(
    portal: Portal,
    log: logging.Logger,
    *,
    max_jobs: int | None = None,
    validate_mode: bool = False,
) -> list[dict]:
    provider = _provider_for_portal(portal)

    # JS-required portals and explicit Firecrawl usage go through Firecrawl provider directly.
    if provider is _FIRECRAWL_PROVIDER:
        return _run_firecrawl_extract(
            portal,
            log,
            max_jobs=max_jobs,
            validate_mode=validate_mode,
        )

    result = provider.scrape(portal, max_jobs=max_jobs, validate_mode=validate_mode)

    # Log typed reason for non-success outcomes (aids debugging without log-string parsing)
    if result.reason not in (ScrapeReason.SUCCESS, ScrapeReason.NO_JOBS, ScrapeReason.FALLBACK):
        log.warning(f"    [{portal['company']}] scrape reason: {result.reason.value}")

    return _apply_fallback(
        result,
        portal,
        log,
        max_jobs=max_jobs,
        validate_mode=validate_mode,
    )
