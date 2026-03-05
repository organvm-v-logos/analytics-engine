"""Tests for the new referrer tracking functionality."""

import json
from datetime import date
from unittest.mock import MagicMock, patch

from src.aggregator import build_engagement_metrics, check_thresholds
from src.config import GoatCounterConfig, ThresholdRule, ThresholdsConfig
from src.goatcounter import collect_metrics, fetch_referrers


def _mock_resp(data: dict):
    mock = MagicMock()
    mock.read.return_value = json.dumps(data).encode()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class TestReferrers:
    @patch("src.goatcounter.urllib.request.urlopen")
    def test_fetch_referrers(self, mock_urlopen):
        data = {
            "referrers": [{"name": "google.com", "count": 50}, {"name": "twitter.com", "count": 30}]
        }
        mock_urlopen.return_value = _mock_resp(data)
        config = GoatCounterConfig(site="test", token="tok_test")

        referrers = fetch_referrers(config, date(2026, 3, 1), date(2026, 3, 5))
        assert len(referrers) == 2
        assert referrers[0]["name"] == "google.com"
        assert referrers[0]["count"] == 50

    @patch("src.goatcounter.fetch_referrers")
    @patch("src.goatcounter.fetch_total_stats")
    @patch("src.goatcounter.fetch_page_hits")
    def test_collect_metrics_includes_referrers(self, mock_hits, mock_totals, mock_ref):
        mock_hits.return_value = []
        mock_totals.return_value = {"total_count": 100, "total_unique": 80}
        mock_ref.return_value = [{"name": "test.com", "count": 10}]

        config = GoatCounterConfig(site="test", token="tok_test")
        result = collect_metrics(config, days=7)

        assert "referrers" in result
        assert result["referrers"][0]["name"] == "test.com"

    def test_build_engagement_metrics_computes_max_referrer_share(self):
        gc_data = {
            "period": {"start": "2026-03-01", "end": "2026-03-05"},
            "site_totals": {"page_views": 100, "unique_visitors": 80},
            "pages": [],
            "referrers": [
                {"name": "bot-site.com", "count": 85},
                {"name": "google.com", "count": 5},
            ],
        }
        result = build_engagement_metrics(gc_data, None)

        assert result["site_totals"]["referrer_count"] == 2
        assert result["referrers"][0]["name"] == "bot-site.com"
        assert result["trends"]["max_referrer_share_pct"] == 85.0

    def test_check_thresholds_triggers_referrer_anomaly(self):
        thresholds = ThresholdsConfig(
            rules=[
                ThresholdRule(
                    name="referrer_anomaly",
                    description="Bot alert",
                    metric="referrer_share_pct",
                    operator=">",
                    value=80,
                    severity="info",
                )
            ]
        )

        gc = {"pages": [], "available": True}
        gh = {"totals": {"commits": 10}}
        trends = {"max_referrer_share_pct": 85.0}

        alerts = check_thresholds(thresholds, gc, gh, trends)
        assert len(alerts) == 1
        assert alerts[0]["rule"] == "referrer_anomaly"
        assert alerts[0]["current_value"] == 85.0
