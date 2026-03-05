"""Tests for browser and OS metric collection."""
import json
from datetime import date
from unittest.mock import MagicMock, patch

from src.aggregator import build_engagement_metrics
from src.config import GoatCounterConfig
from src.goatcounter import fetch_browsers, fetch_systems


def _mock_resp(data: dict):
    mock = MagicMock()
    mock.read.return_value = json.dumps(data).encode()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock

class TestBrowserOS:
    @patch("src.goatcounter.urllib.request.urlopen")
    def test_fetch_browsers(self, mock_urlopen):
        mock_urlopen.return_value = _mock_resp({"browsers": [{"name": "Chrome", "count": 100}]})
        config = GoatCounterConfig(site="test", token="tok")
        res = fetch_browsers(config, date(2026,1,1), date(2026,1,2))
        assert len(res) == 1
        assert res[0]["name"] == "Chrome"

    @patch("src.goatcounter.urllib.request.urlopen")
    def test_fetch_systems(self, mock_urlopen):
        mock_urlopen.return_value = _mock_resp({"systems": [{"name": "macOS", "count": 50}]})
        config = GoatCounterConfig(site="test", token="tok")
        res = fetch_systems(config, date(2026,1,1), date(2026,1,2))
        assert len(res) == 1
        assert res[0]["name"] == "macOS"

    def test_build_engagement_metrics_includes_browsers_and_systems(self):
        gc_data = {
            "period": {"start": "2026-03-01", "end": "2026-03-05"},
            "site_totals": {"page_views": 100, "unique_visitors": 80},
            "pages": [],
            "referrers": [],
            "browsers": [{"name": "Chrome", "count": 60}],
            "systems": [{"name": "macOS", "count": 40}],
        }
        result = build_engagement_metrics(gc_data, None)
        assert len(result["browsers"]) == 1
        assert result["browsers"][0]["name"] == "Chrome"
        assert len(result["systems"]) == 1
        assert result["systems"][0]["name"] == "macOS"

