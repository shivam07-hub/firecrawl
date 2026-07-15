from __future__ import annotations

from job_career_band import normalize_job_career_band
from writer import to_canonical


def test_product_designer_uses_design_band_over_product_domain() -> None:
    assert normalize_job_career_band({
        "job_title": "Product Designer",
        "role_domain": "Product Management",
    }) == "design_creative"


def test_role_domain_maps_mba_families_to_business_band() -> None:
    assert normalize_job_career_band({
        "job_title": "Strategy Associate",
        "role_domain": "Strategy & Consulting",
    }) == "business_product_operations"


def test_unknown_titles_do_not_invent_a_band() -> None:
    assert normalize_job_career_band({"job_title": "Associate"}) == ""


def test_canonical_writer_publishes_career_band() -> None:
    row = to_canonical({
        "job_id": "policy-1",
        "title": "Graduate Policy Research Associate",
        "raw_jd_text": "Support policy research and stakeholder briefs for public programs.",
        "role_domain": "Research & Science",
    }, "Example Org")

    assert row["career_band"] == "research_people_public_impact"
