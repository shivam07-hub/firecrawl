from datetime import datetime, timezone

from trusted_job_lifecycle import assess_source_run, missing_transition


def test_complete_run_requires_safe_coverage() -> None:
    healthy = assess_source_run(current_count=80, prior_good_count=100)
    collapsed = assess_source_run(current_count=20, prior_good_count=100)

    assert healthy.status == "complete"
    assert healthy.coverage_ratio == 0.8
    assert collapsed.status == "partial"
    assert "coverage" in (collapsed.failure_reason or "")


def test_zero_first_run_is_failed_not_complete() -> None:
    result = assess_source_run(current_count=0, prior_good_count=None)

    assert result.status == "failed"


def test_growth_is_complete_and_coverage_is_capped_for_storage() -> None:
    result = assess_source_run(current_count=37, prior_good_count=36)

    assert result.status == "complete"
    assert result.coverage_ratio == 1.0


def test_three_complete_misses_close_then_quarantine_listing() -> None:
    now = datetime(2026, 7, 11, 12, tzinfo=timezone.utc)

    first = missing_transition(0, now=now)
    second = missing_transition(1, now=now)
    third = missing_transition(2, now=now)

    assert first.listing_confidence == "uncertain"
    assert first.is_active is True
    assert second.listing_confidence == "likely_closed"
    assert second.is_active is True
    assert third.listing_confidence == "closed"
    assert third.is_active is False
    assert third.quarantine_until is not None
    assert (third.quarantine_until - now).days == 30


def test_additional_misses_do_not_extend_quarantine() -> None:
    now = datetime(2026, 7, 11, 12, tzinfo=timezone.utc)

    transition = missing_transition(3, now=now)

    assert transition.listing_confidence == "closed"
    assert transition.quarantine_until is None
