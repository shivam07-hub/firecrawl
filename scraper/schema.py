"""
Canonical schema definition for the Dump 4+ job pipeline.

Single source of truth for:
  - Portal          — TypedDict for portal config dicts (ATS routing + metadata)
  - CANONICAL_FIELDS — ordered field list (matches Supabase `jobs` table columns)
  - RAW_FIELD_MAP    — scraper raw name → canonical name (for writer.to_canonical)
  - SKILL_FIELDS     — fields filled by LLM enrichment (enricher.py)
  - LEGACY_FIELD_ALIASES — older field names from pre-Dump4 dumps

Do not add fields here without also updating the Supabase DDL and CLAUDE.md.
"""
from __future__ import annotations
from typing import TypedDict


class Portal(TypedDict, total=False):
    """
    Typed portal config dict produced by portal_reader.parse_portals().

    Required fields (total=False means all optional at type-check level,
    but company/ats/endpoint are always populated by portal_reader).
    ATS-specific fields (workday_*, sr_id, board_token, lever_slug) are only
    present for their respective ATS type.
    """
    # Universal
    company:      str   # display name — must match company_industries.json key
    ats:          str   # workday | smartrecruiters | greenhouse | lever | phenom_api
                        # | phenom_ssr | yello | sap_jobs2web_html | pepsico_jobs_api
                        # | skima_careers | hm_wp_jobs | deloitte_usi
                        # | sap | oracle | eightfold | avature | talentbrew | custom | other
    endpoint:     str   # URL to hit
    careers_url:  str   # human-facing careers page (fallback / reference)
    js_required:  bool  # True → route through FirecrawlJSProvider
    india_only:   bool  # True → apply is_india() filter post-scrape
    status:       str   # raw emoji status string from KNOWN_PORTALS.md
    industry:     str   # from company_industries.json

    # Workday-specific
    tenant:               str
    instance:             str        # wd1 | wd3 | wd5 …
    career_site:          str        # career site slug in Workday URL
    workday_search_text:  str        # use searchText= filter (no India UUID)
    workday_facet_param:  str        # locationCountry | locations | locationHierarchy1 …
    workday_india_uuids:  list[str]  # one UUID (standard) or many (office-level)
    workday_it_facet_param: str
    workday_it_uuids:     list[str]

    # SmartRecruiters-specific
    sr_id:        str

    # Greenhouse-specific
    board_token:  str

    # Lever-specific
    lever_slug:   str

    # Phenom-specific (no extra fields beyond endpoint)

# Ordered canonical field list — must match Supabase `jobs` table column order.
# Lifecycle columns (first_seen, last_seen, is_active, change_fingerprint) are
# Supabase-managed and not included here.
CANONICAL_FIELDS: list[str] = [
    "job_id",
    "job_title",
    "job_description",
    "industry",
    "industry_group",
    "company_name",
    "location",
    "location_city",
    "apply_url",
    "role_domain",
    "main_skills",
    "side_skills",
    "batch_date",
]

# Maps scraper raw dict keys → canonical keys (used by writer.to_canonical).
# Only covers the non-obvious renames; identity mappings (company_name) are omitted.
RAW_FIELD_MAP: dict[str, str] = {
    "title":         "job_title",
    "raw_jd_text":   "job_description",
    "location_city": "location",
    "job_url":       "apply_url",
}

# Fields populated by LLM enrichment (Phase 2 of the pipeline).
SKILL_FIELDS: tuple[str, ...] = ("main_skills", "side_skills")

# Aliases from pre-Dump4 schemas — used by csv_importer.normalize_job for
# backward-compatible reading of older dump files.
LEGACY_FIELD_ALIASES: dict[str, list[str]] = {
    "job_title":       ["title"],
    "job_description": ["raw_jd_text", "job_description"],
    "location":        ["Location", "location_city", "location", "location_country"],
    "apply_url":       ["job_url", "apply_url"],
    "main_skills":     ["main_skills", "skills_required"],
    "side_skills":     ["side_skills", "skills_preferred"],
}
