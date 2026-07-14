from __future__ import annotations

from datetime import date

from daily_poll import build_commands, run_dates_spanned


def test_daily_poll_publishes_source_without_linear_enrichment() -> None:
    commands = build_commands(
        python="python",
        run_date="2026_07_12",
        scope="india",
        company_cap=2000,
    )

    assert [name for name, _ in commands] == ["scrape", "publish"]
    assert "--skip-enrich" in commands[0][1]
    assert "--source-only" in commands[1][1]
    assert "--enrich-only" not in " ".join(part for _, command in commands for part in command)


def test_company_canary_scopes_both_steps() -> None:
    commands = build_commands(
        python="python",
        run_date="2026_07_12",
        scope="india",
        company_cap=50,
        company="Stripe",
    )

    assert commands[0][1][-2:] == ["--company", "Stripe"]
    assert commands[1][1][-2:] == ["--company", "Stripe"]


def test_run_dates_spanned_includes_midnight_boundary() -> None:
    assert run_dates_spanned(
        date(2026, 7, 12), date(2026, 7, 13)
    ) == ["2026_07_12", "2026_07_13"]
