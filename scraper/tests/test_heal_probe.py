"""Probe verdict logic — dispatch_scrape stubbed so it's network-free."""

from __future__ import annotations

import providers
from heal.probe import probe_company


def _stub(jobs):
    def _f(portal, log, max_jobs=None):
        return jobs[:max_jobs] if max_jobs else jobs
    return _f


def test_capped_probe_reads_as_recovered_not_partial(monkeypatch):
    # 30 jobs available, cap 25 -> count==cap -> healthy route, not PARTIAL.
    monkeypatch.setattr(providers, "dispatch_scrape", _stub([{"job_title": f"r{i}"} for i in range(30)]))
    r = probe_company({"company": "NVIDIA", "ats": "pcsx"}, baseline_count=201, max_jobs=25)
    assert r.verdict == "RECOVERED"
    assert r.this_count == 25


def test_genuine_dry_route_is_partial(monkeypatch):
    monkeypatch.setattr(providers, "dispatch_scrape", _stub([{"job_title": f"r{i}"} for i in range(3)]))
    r = probe_company({"company": "Qualcomm", "ats": "pcsx"}, baseline_count=709, max_jobs=25)
    assert r.verdict == "PARTIAL"
    assert r.this_count == 3


def test_zero_is_still_broken(monkeypatch):
    monkeypatch.setattr(providers, "dispatch_scrape", _stub([]))
    r = probe_company({"company": "HSBC", "ats": "other"}, baseline_count=250, max_jobs=25)
    assert r.verdict == "STILL_BROKEN"


def test_route_raises_is_error(monkeypatch):
    def _boom(portal, log, max_jobs=None):
        raise RuntimeError("405")
    monkeypatch.setattr(providers, "dispatch_scrape", _boom)
    r = probe_company({"company": "Persistent Systems", "ats": "custom"}, baseline_count=300, max_jobs=25)
    assert r.verdict == "ERROR"
    assert not r.reachable
