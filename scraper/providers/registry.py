from __future__ import annotations

from schema import Portal

import logging

from providers.base import FALLBACK_FIRECRAWL_EXTRACT, Provider, ProviderResult, ScrapeReason
from providers.eightfold import EightfoldProvider
from providers.firecrawl_js import FirecrawlJSProvider
from providers.darwinbox import DarwinboxProvider
from providers.mynexthire import MyNextHireProvider
from providers.icims_custom import IcimsCustomProvider
from providers.mckinsey import McKinseyProvider
from providers.aditya_birla import AdityaBirlaProvider
from providers.apple_jobs import AppleJobsProvider
from providers.cognizant_xml import CognizantXMLProvider
from providers.deshaw_india import DEShawIndiaProvider
from providers.pcsx import PCSXProvider
from providers.taleo import TaleoProvider
from providers.talentbrew import TalentBrewProvider
from providers.phenom_ssr import PhenomSSRProvider
from providers.siemens_externaljobs import SiemensExternalJobsProvider
from providers.deloitte_usi import DeloitteUSIProvider
from providers.yello import YelloProvider
from providers.sap_jobs2web_html import SAPJobs2WebHTMLProvider
from providers.tata_elxsi import TataElxsiProvider
from providers.vector_consulting import VectorConsultingProvider
from providers.pepsico_jobs_api import PepsiCoJobsAPIProvider
from providers.skima_careers import SkimaCareersProvider
from providers.hm_wp_jobs import HMWordPressJobsProvider
from providers.michelin_astro import MichelinAstroProvider
from providers.pinpoint import PinpointProvider
from providers.spire2grow import Spire2GrowProvider
from providers.zwayam import ZwayamProvider
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
    "eightfold": EightfoldProvider(),
    "icims_custom": IcimsCustomProvider(),
    "darwinbox": DarwinboxProvider(),
    "mynexthire": MyNextHireProvider(),
    "mckinsey": McKinseyProvider(),
    "aditya_birla": AdityaBirlaProvider(),
    "apple_jobs": AppleJobsProvider(),
    "cognizant_xml": CognizantXMLProvider(),
    "deshaw_india": DEShawIndiaProvider(),
    "pinpoint": PinpointProvider(),
    "pcsx": PCSXProvider(),
    "taleo": TaleoProvider(),
    "talentbrew": TalentBrewProvider(),
    "phenom_ssr": PhenomSSRProvider(),
    "siemens_externaljobs": SiemensExternalJobsProvider(),
    "deloitte_usi": DeloitteUSIProvider(),
    "yello": YelloProvider(),
    "sap_jobs2web_html": SAPJobs2WebHTMLProvider(),
    "tata_elxsi": TataElxsiProvider(),
    "vector_consulting": VectorConsultingProvider(),
    "pepsico_jobs_api": PepsiCoJobsAPIProvider(),
    "skima_careers": SkimaCareersProvider(),
    "hm_wp_jobs": HMWordPressJobsProvider(),
    "michelin_astro": MichelinAstroProvider(),
    "spire2grow": Spire2GrowProvider(),
    "zwayam": ZwayamProvider(),
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

    if reason in ("workday_api_blocked", "workday_cloudflare_blocked"):
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
    on_page_complete=None,  # Callable[[list[dict], int], None] | None — Workday/Taleo only
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

    # Only Workday and Taleo support page-level callbacks — others ignore the param safely
    supports_callback = isinstance(provider, (WorkdayProvider, TaleoProvider))
    scrape_kwargs: dict = {"max_jobs": max_jobs, "validate_mode": validate_mode}
    if on_page_complete and supports_callback:
        scrape_kwargs["on_page_complete"] = on_page_complete

    result = provider.scrape(portal, **scrape_kwargs)

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


def probe_scrape(
    portal: Portal,
    log: logging.Logger,
    *,
    max_jobs: int | None = None,
    validate_mode: bool = False,
    allow_firecrawl: bool = False,
) -> ProviderResult:
    """Probe one portal without implicit Firecrawl fallback unless allowed.

    Inventory runs need to distinguish "direct route returned zero" from
    "direct route would need Firecrawl". The production dispatch path should keep
    falling back automatically; this probe path is deliberately conservative.
    """
    provider = _provider_for_portal(portal)

    if provider is _FIRECRAWL_PROVIDER and not allow_firecrawl:
        return ProviderResult.fallback(
            policy=FALLBACK_FIRECRAWL_EXTRACT,
            reason="firecrawl_probe_skipped",
            portal=portal,
        )

    result = provider.scrape(
        portal,
        max_jobs=max_jobs,
        validate_mode=validate_mode,
    )

    if result.fallback_policy == FALLBACK_FIRECRAWL_EXTRACT and allow_firecrawl:
        jobs = _apply_fallback(
            result,
            portal,
            log,
            max_jobs=max_jobs,
            validate_mode=validate_mode,
        )
        return ProviderResult.success(jobs)

    return result
