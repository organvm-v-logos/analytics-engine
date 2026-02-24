"""Tests for the metric aggregation engine."""

import json
from pathlib import Path

from src.aggregator import (
    aggregate,
    build_engagement_metrics,
    build_system_report,
    check_thresholds,
    compute_trend,
    load_latest_raw,
    load_previous_metrics,
    save_to_history,
)
from src.config import ThresholdRule, ThresholdsConfig

FIXTURES = Path(__file__).parent / "fixtures"


class TestComputeTrend:
    def test_positive_change(self):
        assert compute_trend(110, 100) == 10.0

    def test_negative_change(self):
        assert compute_trend(80, 100) == -20.0

    def test_no_change(self):
        assert compute_trend(100, 100) == 0.0

    def test_none_when_previous_is_none(self):
        assert compute_trend(100, None) is None

    def test_none_when_previous_is_zero(self):
        assert compute_trend(100, 0) is None


class TestLoadLatestRaw:
    def test_loads_matching_file(self, tmp_path):
        (tmp_path / "goatcounter-2026-02-24.json").write_text('{"test": true}')
        result = load_latest_raw(tmp_path, "goatcounter")
        assert result == {"test": True}

    def test_loads_most_recent(self, tmp_path):
        (tmp_path / "goatcounter-2026-02-17.json").write_text('{"week": 1}')
        (tmp_path / "goatcounter-2026-02-24.json").write_text('{"week": 2}')
        result = load_latest_raw(tmp_path, "goatcounter")
        assert result["week"] == 2

    def test_returns_none_when_no_files(self, tmp_path):
        assert load_latest_raw(tmp_path, "goatcounter") is None


class TestLoadPreviousMetrics:
    def test_loads_from_history(self, tmp_path):
        (tmp_path / "engagement-metrics-2026-02-17.json").write_text(
            json.dumps({"site_totals": {"page_views": 950}})
        )
        result = load_previous_metrics(tmp_path)
        assert result["site_totals"]["page_views"] == 950

    def test_returns_none_when_empty(self, tmp_path):
        assert load_previous_metrics(tmp_path) is None


class TestBuildEngagementMetrics:
    def test_basic_structure(self):
        gc_data = {
            "period": {"start": "2026-02-17", "end": "2026-02-24"},
            "site_totals": {"page_views": 1077, "unique_visitors": 782},
            "pages": [
                {"path": "/test/", "title": "Test", "count": 100, "count_unique": 80}
            ],
        }
        result = build_engagement_metrics(gc_data, None)
        assert result["site_totals"]["page_views"] == 1077
        assert result["site_totals"]["unique_visitors"] == 782
        assert len(result["pages"]) == 1
        assert result["trends"]["views_delta_pct"] is None

    def test_with_previous_data(self):
        gc_data = {
            "period": {"start": "2026-02-17", "end": "2026-02-24"},
            "site_totals": {"page_views": 1077, "unique_visitors": 782},
            "pages": [],
        }
        previous = {
            "site_totals": {"page_views": 950, "unique_visitors": 680},
        }
        result = build_engagement_metrics(gc_data, previous)
        assert result["trends"]["views_delta_pct"] == 13.4
        assert result["trends"]["visitors_delta_pct"] == 15.0

    def test_empty_goatcounter_data(self):
        gc_data = {
            "period": {},
            "site_totals": {"page_views": 0, "unique_visitors": 0},
            "pages": [],
        }
        result = build_engagement_metrics(gc_data, None)
        assert result["site_totals"]["page_views"] == 0
        assert result["pages"] == []


class TestBuildSystemReport:
    def test_basic_structure(self):
        gc_data = {
            "period": {"start": "2026-02-17", "end": "2026-02-24"},
            "site_totals": {"page_views": 1077, "unique_visitors": 782},
            "pages": [
                {"path": "/essays/meta-system/01-orchestrate/", "count": 312},
            ],
        }
        gh_data = json.loads((FIXTURES / "github_activity.json").read_text())
        report = build_system_report(gc_data, gh_data, [])

        assert report["web_engagement"]["total_views"] == 1077
        assert report["web_engagement"]["top_essay"] == "01-orchestrate"
        assert report["github_activity"]["total_commits"] == 47
        assert "I" in report["github_activity"]["organ_breakdown"]
        assert report["alerts"] == []

    def test_no_pages_gives_null_top_essay(self):
        gc_data = {
            "period": {"start": "2026-02-17", "end": "2026-02-24"},
            "site_totals": {"page_views": 0, "unique_visitors": 0},
            "pages": [],
        }
        gh_data = {"period": {}, "totals": {"commits": 0, "prs": 0, "releases": 0},
                   "organ_breakdown": {}}
        report = build_system_report(gc_data, gh_data, [])
        assert report["web_engagement"]["top_essay"] is None

    def test_alerts_included(self):
        gc_data = {
            "period": {},
            "site_totals": {"page_views": 0, "unique_visitors": 0},
            "pages": [],
        }
        gh_data = {"period": {}, "totals": {"commits": 0, "prs": 0, "releases": 0},
                   "organ_breakdown": {}}
        alerts = [{"rule": "test_alert", "severity": "warning"}]
        report = build_system_report(gc_data, gh_data, alerts)
        assert len(report["alerts"]) == 1


class TestCheckThresholds:
    def test_traffic_drop_alert(self):
        thresholds = ThresholdsConfig(rules=[
            ThresholdRule(
                name="traffic_drop", description="Traffic dropped",
                metric="views_delta_pct", operator="<", value=-50, severity="warning"
            ),
        ])
        gc = {"pages": [], "available": True}
        gh = {"totals": {"commits": 10}}
        trends = {"views_delta_pct": -60}

        alerts = check_thresholds(thresholds, gc, gh, trends)
        assert len(alerts) == 1
        assert alerts[0]["rule"] == "traffic_drop"

    def test_no_alert_when_above_threshold(self):
        thresholds = ThresholdsConfig(rules=[
            ThresholdRule(
                name="traffic_drop", description="Traffic dropped",
                metric="views_delta_pct", operator="<", value=-50, severity="warning"
            ),
        ])
        gc = {"pages": [], "available": True}
        gh = {"totals": {"commits": 10}}
        trends = {"views_delta_pct": -20}

        alerts = check_thresholds(thresholds, gc, gh, trends)
        assert len(alerts) == 0

    def test_github_stall_alert(self):
        thresholds = ThresholdsConfig(rules=[
            ThresholdRule(
                name="github_stall", description="Low commits",
                metric="total_commits", operator="<", value=5, severity="warning"
            ),
        ])
        gc = {"pages": [], "available": True}
        gh = {"totals": {"commits": 2}}
        trends = {}

        alerts = check_thresholds(thresholds, gc, gh, trends)
        assert len(alerts) == 1
        assert alerts[0]["rule"] == "github_stall"


class TestSaveToHistory:
    def test_copies_files_to_history(self, tmp_path):
        out = tmp_path / "output"
        hist = tmp_path / "history"
        out.mkdir()
        (out / "engagement-metrics.json").write_text('{"test": true}')
        (out / "system-engagement-report.json").write_text('{"report": true}')

        save_to_history(out, hist)

        history_files = list(hist.glob("*.json"))
        assert len(history_files) == 2


class TestAggregate:
    def test_full_pipeline_with_fixtures(self, tmp_path):
        raw = tmp_path / "raw"
        out = tmp_path / "output"
        hist = tmp_path / "history"
        raw.mkdir()

        # Set up raw data
        gc_raw = {
            "source": "goatcounter", "available": True,
            "period": {"start": "2026-02-17", "end": "2026-02-24"},
            "site_totals": {"page_views": 1077, "unique_visitors": 782},
            "pages": [{"path": "/test/", "title": "Test", "count": 100, "count_unique": 80}],
        }
        (raw / "goatcounter-2026-02-24.json").write_text(json.dumps(gc_raw))

        gh_raw = json.loads((FIXTURES / "github_activity.json").read_text())
        (raw / "github-activity-2026-02-24.json").write_text(json.dumps(gh_raw))

        summary = aggregate(str(raw), str(out), str(hist), ThresholdsConfig())
        assert summary["goatcounter_available"] is True
        assert summary["github_available"] is True
        assert summary["page_count"] == 1

        # Verify output files exist
        assert (out / "engagement-metrics.json").exists()
        assert (out / "system-engagement-report.json").exists()

    def test_pipeline_with_no_raw_data(self, tmp_path):
        raw = tmp_path / "raw"
        out = tmp_path / "output"
        hist = tmp_path / "history"
        raw.mkdir()

        summary = aggregate(str(raw), str(out), str(hist), ThresholdsConfig())
        assert summary["goatcounter_available"] is False
        assert summary["github_available"] is False
        assert summary["page_count"] == 0

        # Should still produce output files
        assert (out / "engagement-metrics.json").exists()
