"""Deterministic source-owned Career Band normalization for scraped jobs."""
from __future__ import annotations

import re
from typing import Any


_ROLE_DOMAIN_BANDS = {
    "software engineering": "engineering_data",
    "data & analytics": "engineering_data",
    "it & infrastructure": "engineering_data",
    "manufacturing": "engineering_data",
    "finance": "business_product_operations",
    "strategy & consulting": "business_product_operations",
    "sales & marketing": "business_product_operations",
    "operations": "business_product_operations",
    "product management": "business_product_operations",
    "risk & compliance": "business_product_operations",
    "general management": "business_product_operations",
    "supply chain": "business_product_operations",
    "research & science": "research_people_public_impact",
    "hr & people": "research_people_public_impact",
    "legal & compliance": "research_people_public_impact",
}

_DESIGN_TITLE = re.compile(
    r"\b(?:ux|ui|product|graphic|visual|brand|motion|content|creative)\s+"
    r"(?:designer|design|writer|artist|illustrator)\b|\b(?:ux|ui)\b",
    re.IGNORECASE,
)
_TECHNICAL_TITLE = re.compile(
    r"\b(?:software|data|machine learning|ai|devops|sre|cloud|cyber|security|"
    r"qa|quality assurance|platform|backend|front[ -]?end|full[ -]?stack|"
    r"engineer|developer|programmer|architect|infrastructure|manufacturing|"
    r"embedded|systems?)\b",
    re.IGNORECASE,
)
_BUSINESS_TITLE = re.compile(
    r"\b(?:product manager|marketing|sales|finance|consultant|consulting|strategy|"
    r"operations|business analyst|supply chain|procurement|revenue|account executive|"
    r"partnerships?|growth)\b",
    re.IGNORECASE,
)
_PUBLIC_IMPACT_TITLE = re.compile(
    r"\b(?:research|policy|public affairs|government relations|social impact|"
    r"human resources|\bhr\b|people|talent|legal|counsel|compliance|community|"
    r"education|programme? officer)\b",
    re.IGNORECASE,
)


def normalize_job_career_band(job: dict[str, Any]) -> str:
    """Map source metadata/title to one of Myro's four role families.

    Explicit title signals take precedence over a broader role domain so that a
    Product Designer stays in Design & Creative rather than Product Management.
    Unknown evidence stays blank; this function never invents a career path.
    """
    title = str(job.get("job_title") or job.get("title") or "")
    for pattern, band in (
        (_DESIGN_TITLE, "design_creative"),
        (_TECHNICAL_TITLE, "engineering_data"),
        (_BUSINESS_TITLE, "business_product_operations"),
        (_PUBLIC_IMPACT_TITLE, "research_people_public_impact"),
    ):
        if pattern.search(title):
            return band
    return _ROLE_DOMAIN_BANDS.get(str(job.get("role_domain") or "").strip().casefold(), "")
