"""Tests for the GoatCounter API client."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config import GoatCounterConfig
from src.goatcounter import (
    collect_metrics,
    fetch_page_hits,
    fetch_referrers,
    fetch_total_stats,
    main,
    unconfigured_result,
)


class TestFetchReferrers:
    @patch("src.goatcounter.urllib.request.urlopen")
    def test_parses_referrers(self, mock_urlopen):
        data = {"referrers": [{"name": "google.com", "count": 10}]}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(data).encode()
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        config = GoatCounterConfig(site="test", token="tok_test")  # allow-secret
        from datetime import date

        refs = fetch_referrers(config, date(2026, 2, 17), date(2026, 2, 24))
        assert len(refs) == 1
        assert refs[0]["name"] == "google.com"


class TestGoatCounterMain:
    @patch("src.goatcounter.collect_metrics")
    @patch("src.goatcounter.GoatCounterConfig.from_env")
    @patch("sys.exit")
    def test_main_runs(self, mock_exit, mock_config, mock_collect, tmp_path):
        mock_config.return_value = MagicMock(configured=True)
        mock_collect.return_value = {"site_totals": {"page_views": 100}}

        output_dir = tmp_path / "raw"
        with patch("sys.argv", ["prog", "--output", str(output_dir)]):
            main()

        assert len(list(output_dir.glob("goatcounter-*.json"))) == 1
        mock_exit.assert_called_with(0)


FIXTURES = Path(__file__).parent / "fixtures"


def _mock_urlopen(fixture_path: Path):
    """Create a mock urllib.request.urlopen context manager."""
    data = fixture_path.read_bytes()
    mock_resp = MagicMock()
    mock_resp.read.return_value = data
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestUnconfiguredResult:
    def test_has_correct_structure(self):
        result = unconfigured_result(7)
        assert result["source"] == "goatcounter"
        assert result["available"] is False
        assert "reason" in result
        assert result["site_totals"]["page_views"] == 0
        assert result["pages"] == []

    def test_respects_days_parameter(self):
        result = unconfigured_result(14)
        assert result["period"]["days"] == 14


class TestFetchPageHits:
    @patch("src.goatcounter.urllib.request.urlopen")
    def test_parses_pages_fixture(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(FIXTURES / "goatcounter_pages.json")
        config = GoatCounterConfig(site="test", token="tok_test")  # allow-secret

        from datetime import date

        pages = fetch_page_hits(config, date(2026, 2, 17), date(2026, 2, 24))

        assert len(pages) == 5
        assert pages[0]["path"] == "/essays/meta-system/01-orchestrate/"
        assert pages[0]["count"] == 312
        assert pages[0]["count_unique"] == 218

    @patch("src.goatcounter.urllib.request.urlopen")
    def test_empty_response(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(FIXTURES / "goatcounter_empty.json")
        config = GoatCounterConfig(site="test", token="tok_test")  # allow-secret

        from datetime import date

        pages = fetch_page_hits(config, date(2026, 2, 17), date(2026, 2, 24))
        assert pages == []


class TestFetchTotalStats:
    @patch("src.goatcounter.urllib.request.urlopen")
    def test_parses_totals(self, mock_urlopen):
        data = {"total": {"count": 1077, "count_unique": 782}}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        config = GoatCounterConfig(site="test", token="tok_test")  # allow-secret

        from datetime import date

        totals = fetch_total_stats(config, date(2026, 2, 17), date(2026, 2, 24))
        assert totals["total_count"] == 1077
        assert totals["total_unique"] == 782


class TestCollectMetrics:
    @patch("src.goatcounter.fetch_systems")
    @patch("src.goatcounter.fetch_browsers")
    @patch("src.goatcounter.fetch_referrers")
    @patch("src.goatcounter.fetch_total_stats")
    @patch("src.goatcounter.fetch_page_hits")
    def test_builds_complete_result(
        self, mock_hits, mock_totals, mock_ref, mock_browsers, mock_systems
    ):
        mock_hits.return_value = [
            {"path": "/test/", "title": "Test", "count": 100, "count_unique": 80}
        ]
        mock_totals.return_value = {"total_count": 100, "total_unique": 80}
        mock_ref.return_value = [{"name": "ref.com", "count": 10}]
        mock_browsers.return_value = [{"name": "Chrome", "count": 50}]
        mock_systems.return_value = [{"name": "macOS", "count": 30}]

        config = GoatCounterConfig(site="test", token="tok_test")  # allow-secret
        result = collect_metrics(config, days=7)

        assert result["source"] == "goatcounter"
        assert result["available"] is True
        assert result["site_totals"]["page_views"] == 100
        assert len(result["pages"]) == 1
        assert len(result["referrers"]) == 1
        assert len(result["browsers"]) == 1
        assert len(result["systems"]) == 1
