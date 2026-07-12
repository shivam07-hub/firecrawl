from __future__ import annotations

import daily_cycle


def test_build_commands_runs_poll_before_worker() -> None:
    poll, worker = daily_cycle.build_commands(
        python="python-test",
        scope="india",
        company_cap=250,
        company="Deepgram",
        max_messages=900,
    )

    assert poll[:2] == ["python-test", str(daily_cycle.ROOT / "daily_poll.py")]
    assert poll[-2:] == ["--company", "Deepgram"]
    assert worker[:2] == ["python-test", str(daily_cycle.ROOT / "enrichment_worker.py")]
    assert worker[-1] == "900"


def test_remote_open_weight_skips_lm_studio(monkeypatch) -> None:
    monkeypatch.setattr(daily_cycle, "INFERENCE_PROVIDER", "cloudflare_workers_ai")
    monkeypatch.setattr(daily_cycle, "INFERENCE_MODEL", "@cf/open-model")
    monkeypatch.setattr(
        daily_cycle,
        "_lms_binary",
        lambda: (_ for _ in ()).throw(AssertionError("must not inspect local LM Studio")),
    )

    result = daily_cycle.ensure_inference_ready(
        env={}, model_ttl_seconds=3600, timeout_seconds=1
    )

    assert result == {
        "provider": "cloudflare_workers_ai",
        "model": "@cf/open-model",
        "lm_studio_started": False,
    }


def test_loaded_local_model_needs_no_restart_or_reload(monkeypatch) -> None:
    monkeypatch.setattr(daily_cycle, "INFERENCE_PROVIDER", "local")
    monkeypatch.setattr(daily_cycle, "INFERENCE_MODEL", "google/gemma-3-4b")
    monkeypatch.setattr(daily_cycle, "_lms_binary", lambda: "/tmp/lms")
    monkeypatch.setattr(daily_cycle, "_model_ids", lambda: {"google/gemma-3-4b"})
    monkeypatch.setattr(
        daily_cycle.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no command expected")),
    )

    result = daily_cycle.ensure_inference_ready(
        env={}, model_ttl_seconds=3600, timeout_seconds=1
    )

    assert result["model_loaded"] is False
    assert result["loaded_models"] == ["google/gemma-3-4b"]
