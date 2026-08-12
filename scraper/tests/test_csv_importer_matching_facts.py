from __future__ import annotations

import json

import pytest

from csv_importer import (
    _source_matching_facts_are_publishable,
    _validate_source_matching_facts,
)
from enrichment_state import source_content_hash


def _write_jobs(path, jobs) -> None:
    path.write_text(json.dumps(jobs), encoding="utf-8")


def test_matching_fact_preflight_accepts_valid_band_and_unknown_seniority(tmp_path) -> None:
    jobs_path = tmp_path / "jobs.json"
    job = {
        "job_id": "engineer-1",
        "job_title": "Software Engineer",
        "job_description": "Build reliable data services.",
        "career_band": "engineering_data",
        "career_band_source": "deterministic_title_or_role_domain",
        "seniority_level": "",
    }
    job["career_band_source_hash"] = source_content_hash(job)
    _write_jobs(jobs_path, [job])

    assert _validate_source_matching_facts([jobs_path]) == (1, 1, 0)


def test_matching_fact_preflight_rejects_unresolved_band_before_upload(tmp_path) -> None:
    jobs_path = tmp_path / "jobs.json"
    _write_jobs(jobs_path, [{
        "job_id": "associate-1",
        "job_title": "Associate",
        "career_band": "",
        "seniority_level": "entry",
    }])

    with pytest.raises(ValueError, match="1 invalid/unresolved career bands"):
        _validate_source_matching_facts([jobs_path])


def test_matching_fact_preflight_rejects_invalid_seniority(tmp_path) -> None:
    jobs_path = tmp_path / "jobs.json"
    job = {
        "job_id": "engineer-1",
        "job_title": "Software Engineer",
        "job_description": "Build reliable data services.",
        "career_band": "engineering_data",
        "career_band_source": "deterministic_title_or_role_domain",
        "seniority_level": "experienced",
    }
    job["career_band_source_hash"] = source_content_hash(job)
    _write_jobs(jobs_path, [job])

    with pytest.raises(ValueError, match="1 invalid seniority levels"):
        _validate_source_matching_facts([jobs_path])


def test_matching_fact_preflight_rejects_unprovenanced_fallback(tmp_path) -> None:
    jobs_path = tmp_path / "jobs.json"
    _write_jobs(jobs_path, [{
        "job_id": "associate-1",
        "job_title": "Associate",
        "job_description": "Support business operations.",
        "career_band": "business_product_operations",
        "seniority_level": "entry",
    }])

    with pytest.raises(
        ValueError,
        match="1 invalid/stale career-band provenance",
    ):
        _validate_source_matching_facts([jobs_path])


def test_matching_fact_preflight_requires_model_audit_fields(tmp_path) -> None:
    jobs_path = tmp_path / "jobs.json"
    job = {
        "job_id": "associate-1",
        "job_title": "Associate",
        "job_description": "Prepare financial reports.",
        "career_band": "business_product_operations",
        "career_band_source": "model_grounded",
        "seniority_level": "entry",
    }
    job["career_band_source_hash"] = source_content_hash(job)
    _write_jobs(jobs_path, [job])

    with pytest.raises(
        ValueError,
        match="1 invalid/stale career-band provenance",
    ):
        _validate_source_matching_facts([jobs_path])


def test_resolved_only_preflight_counts_withheld_rows(tmp_path) -> None:
    jobs_path = tmp_path / "jobs.json"
    proven = {
        "job_id": "engineer-1",
        "job_title": "Software Engineer",
        "job_description": "Build reliable data services.",
        "career_band": "engineering_data",
        "career_band_source": "deterministic_title_or_role_domain",
        "seniority_level": "",
    }
    proven["career_band_source_hash"] = source_content_hash(proven)
    unresolved = {
        "job_id": "associate-1",
        "job_title": "Associate",
        "job_description": "Support the team.",
        "career_band": "",
        "seniority_level": "entry",
    }
    _write_jobs(jobs_path, [proven, unresolved])

    assert _validate_source_matching_facts(
        [jobs_path],
        allow_withheld=True,
    ) == (2, 1, 0)
    assert _source_matching_facts_are_publishable(proven)
    assert not _source_matching_facts_are_publishable(unresolved)


def test_resolved_only_preflight_withholds_missing_job_id(tmp_path) -> None:
    jobs_path = tmp_path / "jobs.json"
    job = {
        "job_title": "Software Engineer",
        "job_description": "Build reliable data services.",
        "career_band": "engineering_data",
        "career_band_source": "deterministic_title_or_role_domain",
        "seniority_level": "",
    }
    job["career_band_source_hash"] = source_content_hash(job)
    _write_jobs(jobs_path, [job])

    assert _validate_source_matching_facts(
        [jobs_path],
        allow_withheld=True,
    ) == (1, 0, 0)


def test_resolved_only_preflight_counts_duplicate_source_rows(tmp_path) -> None:
    jobs_path = tmp_path / "jobs.json"
    job = {
        "job_id": "engineer-1",
        "company_name": "Example Co",
        "job_title": "Software Engineer",
        "job_description": "Build reliable data services.",
        "career_band": "engineering_data",
        "career_band_source": "deterministic_title_or_role_domain",
        "seniority_level": "",
    }
    job["career_band_source_hash"] = source_content_hash(job)
    _write_jobs(jobs_path, [job, dict(job)])

    assert _validate_source_matching_facts(
        [jobs_path],
        allow_withheld=True,
    ) == (2, 1, 1)
