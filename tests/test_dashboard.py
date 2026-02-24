"""Tests for the static dashboard generator."""

import json
from pathlib import Path

from src.dashboard import (
    alerts_html,
    bar_chart_svg,
    generate_dashboard,
    pages_table_html,
    render_dashboard,
    sparkline_svg,
    trend_indicator,
)


class TestSparklineSvg:
    def test_generates_svg(self):
        svg = sparkline_svg([10, 20, 15, 30, 25])
        assert "<svg" in svg
        assert "polyline" in svg

    def test_empty_values_show_no_data(self):
        svg = sparkline_svg([])
        assert "No data" in svg

    def test_zero_values_show_no_data(self):
        svg = sparkline_svg([0, 0, 0])
        assert "No data" in svg

    def test_single_value(self):
        svg = sparkline_svg([42])
        assert "<svg" in svg


class TestBarChartSvg:
    def test_generates_svg_with_bars(self):
        svg = bar_chart_svg(["I", "II", "III"], [12, 8, 15])
        assert "<svg" in svg
        assert "rect" in svg
        assert "12" in svg

    def test_empty_labels(self):
        svg = bar_chart_svg([], [])
        assert "No data" in svg


class TestPagesTableHtml:
    def test_generates_table(self):
        pages = [
            {"path": "/test/", "title": "Test Page", "views": 100, "unique_visitors": 80}
        ]
        html = pages_table_html(pages)
        assert "<table>" in html
        assert "Test Page" in html
        assert "100" in html

    def test_empty_pages(self):
        html = pages_table_html([])
        assert "No page data" in html

    def test_sorts_by_views_descending(self):
        pages = [
            {"path": "/a/", "title": "Low", "views": 10, "unique_visitors": 5},
            {"path": "/b/", "title": "High", "views": 100, "unique_visitors": 50},
        ]
        html = pages_table_html(pages)
        # High should appear before Low
        assert html.index("High") < html.index("Low")


class TestTrendIndicator:
    def test_positive_trend(self):
        html = trend_indicator(12.3)
        assert "up" in html
        assert "+12.3%" in html

    def test_negative_trend(self):
        html = trend_indicator(-5.0)
        assert "down" in html
        assert "-5.0%" in html

    def test_zero_trend(self):
        html = trend_indicator(0.0)
        assert "neutral" in html

    def test_none_trend(self):
        html = trend_indicator(None)
        assert "neutral" in html
        assert "--" in html


class TestAlertsHtml:
    def test_renders_alerts(self):
        alerts = [{"severity": "warning", "description": "Traffic dropped 60%"}]
        html = alerts_html(alerts)
        assert "alert-warning" in html
        assert "Traffic dropped" in html

    def test_no_alerts(self):
        html = alerts_html([])
        assert "No alerts" in html


class TestRenderDashboard:
    def test_generates_valid_html(self):
        engagement = {
            "generated_at": "2026-02-24T08:00:00+00:00",
            "period": {"start": "2026-02-17", "end": "2026-02-24"},
            "site_totals": {"page_views": 1077, "unique_visitors": 782, "referrer_count": 12},
            "pages": [],
            "trends": {"views_delta_pct": 13.4, "visitors_delta_pct": 15.0},
        }
        report = {
            "generated_at": "2026-02-24T08:00:00+00:00",
            "period": {"start": "2026-02-17", "end": "2026-02-24"},
            "web_engagement": {
                "total_views": 1077, "total_visitors": 782,
                "top_essay": "01-orchestrate",
            },
            "github_activity": {"total_commits": 47, "total_prs": 5, "total_releases": 1,
                                "organ_breakdown": {"I": {"commits": 12}, "III": {"commits": 15}}},
            "alerts": [],
        }
        html = render_dashboard(engagement, report)
        assert "<!DOCTYPE html>" in html
        assert "ORGAN-V Analytics Dashboard" in html
        assert "1,077" in html

    def test_zero_data_shows_notice(self):
        engagement = {
            "generated_at": "",
            "period": {},
            "site_totals": {"page_views": 0, "unique_visitors": 0, "referrer_count": 0},
            "pages": [],
            "trends": {"views_delta_pct": None, "visitors_delta_pct": None},
        }
        report = {
            "generated_at": "",
            "period": {},
            "web_engagement": {"total_views": 0, "total_visitors": 0, "top_essay": None},
            "github_activity": {"total_commits": 0, "total_prs": 0, "total_releases": 0,
                                "organ_breakdown": {}},
            "alerts": [],
        }
        html = render_dashboard(engagement, report)
        assert "No analytics data collected yet" in html


class TestGenerateDashboard:
    def test_creates_index_html(self, tmp_path):
        inp = tmp_path / "input"
        out = tmp_path / "output"
        inp.mkdir()

        engagement = {
            "generated_at": "2026-02-24T08:00:00+00:00",
            "period": {"start": "2026-02-17", "end": "2026-02-24"},
            "site_totals": {"page_views": 100, "unique_visitors": 80, "referrer_count": 3},
            "pages": [],
            "trends": {"views_delta_pct": None, "visitors_delta_pct": None},
        }
        report = {
            "generated_at": "2026-02-24T08:00:00+00:00",
            "period": {"start": "2026-02-17", "end": "2026-02-24"},
            "web_engagement": {"total_views": 100, "total_visitors": 80, "top_essay": None},
            "github_activity": {"total_commits": 10, "total_prs": 2, "total_releases": 0,
                                "organ_breakdown": {}},
            "alerts": [],
        }
        (inp / "engagement-metrics.json").write_text(json.dumps(engagement))
        (inp / "system-engagement-report.json").write_text(json.dumps(report))

        path = generate_dashboard(str(inp), str(out))
        assert Path(path).exists()
        html = Path(path).read_text()
        assert "<!DOCTYPE html>" in html

    def test_handles_missing_input_files(self, tmp_path):
        inp = tmp_path / "input"
        out = tmp_path / "output"
        inp.mkdir()

        path = generate_dashboard(str(inp), str(out))
        assert Path(path).exists()
