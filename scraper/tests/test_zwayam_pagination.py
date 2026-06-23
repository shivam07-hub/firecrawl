"""Zwayam paginates by record offset in small variable pages and signals
continuation via hasMoreData. Regression guard for the Persistent 300->2 bug:
the provider must walk every page, not stop after the first sub-50 page."""

from __future__ import annotations

import json

import providers.zwayam as z


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _make_api(total, page_size):
    """Fake Zwayam: offset-based, `page_size` India jobs per page, hasMoreData until exhausted."""
    jobs = [{"_source": {"jobTitle": f"Engineer {i}", "location": "Pune, India", "id": 1000 + i}}
            for i in range(total)]

    def _post(url, headers=None, files=None, timeout=None):
        start = json.loads(files["filterCri"][1])["paginationStartNo"]
        window = jobs[start:start + page_size]
        return _Resp({"data": {
            "data": window,
            "totalCount": total,
            "hasMoreData": (start + page_size) < total,
        }})
    return _post


def test_walks_all_pages_when_page_is_small(monkeypatch):
    # 200 jobs at 9/page — the exact shape that broke Persistent.
    monkeypatch.setattr(z.requests, "post", _make_api(total=200, page_size=9))
    portal = {"company": "Persistent Systems", "careers_url": "https://careers.persistent.com",
              "zwayam_company_id": "X", "zwayam_api_url": "https://apipersistent.zwayam.com/jobs/search"}
    jobs = z._scrape_zwayam(portal)
    assert len(jobs) == 200  # not 9


def test_respects_max_jobs(monkeypatch):
    monkeypatch.setattr(z.requests, "post", _make_api(total=200, page_size=9))
    portal = {"company": "Persistent Systems", "careers_url": "https://careers.persistent.com",
              "zwayam_company_id": "X", "zwayam_api_url": "https://x/jobs/search"}
    jobs = z._scrape_zwayam(portal, max_jobs=25)
    assert len(jobs) == 25


def test_large_page_deployment_still_works(monkeypatch):
    # CRISIL-style deployment returning 50/page must also fully paginate.
    monkeypatch.setattr(z.requests, "post", _make_api(total=120, page_size=50))
    portal = {"company": "CRISIL", "careers_url": "https://career.crisil.com",
              "zwayam_company_id": "X", "zwayam_api_url": "https://public.zwayam.com/jobs/search"}
    jobs = z._scrape_zwayam(portal)
    assert len(jobs) == 120
