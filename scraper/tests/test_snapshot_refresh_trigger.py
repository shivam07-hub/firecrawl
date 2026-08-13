from __future__ import annotations

from unittest.mock import MagicMock

import csv_importer


def test_scraper_requests_async_forced_refresh_and_accepts_202(monkeypatch) -> None:
    monkeypatch.setenv("MYRO_BACKEND_URL", "https://api.example.test")
    monkeypatch.setenv("MYRO_ANALYTICS_REFRESH_SECRET", "refresh-secret")
    response = MagicMock(status_code=202)
    post = MagicMock(return_value=response)
    monkeypatch.setattr(csv_importer.requests, "post", post)

    csv_importer._refresh_analytics_snapshot()

    post.assert_called_once_with(
        "https://api.example.test/jobs/analytics/refresh-snapshot?force=true",
        headers={"X-Myro-Refresh-Secret": "refresh-secret"},
        timeout=5,
    )
