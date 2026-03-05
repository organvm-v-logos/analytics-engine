"""Tests for weekly signals generation."""

import json
from unittest.mock import patch

from src.signals import (
    build_weekly_signals,
    generate_signals,
    main,
    render_weekly_signals_markdown,
)


class TestSignalsMain:
    @patch("src.signals.generate_signals")
    @patch("sys.exit")
    def test_main_runs(self, mock_exit, mock_gen):
        mock_gen.return_value = {"json": "out.json", "markdown": "out.md"}
        with patch("sys.argv", ["prog", "--input", "in", "--output", "out"]):
            main()
        mock_exit.assert_called_with(0)


class TestBuildWeeklySignals:
    def test_basic_structure(self):
        engagement = {
            "period": {"start": "2026-03-01", "end": "2026-03-08"},
            "site_totals": {"page_views": 1000, "unique_visitors": 600},
            "trends": {"views_delta_pct": 12.5, "visitors_delta_pct": 8.0},
        }
        report = {
            "distribution": {"tracked_views_ratio_pct": 72.0},
            "github_activity": {"total_commits": 12, "total_prs": 3, "total_releases": 1},
            "alerts": [],
        }
        cfg = {
            "targets": {"stranger_tests_completed": 10},
            "manual_metrics": {"stranger_tests_completed": 2},
        }
        signals = build_weekly_signals(engagement, report, cfg)
        assert "generated_at" in signals
        assert signals["kpis"]["page_views"] == 1000
        assert signals["kpis"]["tracked_views_ratio_pct"] == 72.0
        assert signals["outcome_progress"]["stranger_tests_completed"]["progress_pct"] == 20.0
        assert "strengths" in signals["highlights"]

    def test_low_coverage_creates_risk_and_recommendation(self):
        engagement = {
            "period": {"start": "2026-03-01", "end": "2026-03-08"},
            "site_totals": {"page_views": 100, "unique_visitors": 80},
            "trends": {"views_delta_pct": -10.0, "visitors_delta_pct": -5.0},
        }
        report = {
            "distribution": {"tracked_views_ratio_pct": 25.0},
            "github_activity": {"total_commits": 2, "total_prs": 0, "total_releases": 0},
            "alerts": [{"rule": "traffic_drop", "severity": "warning"}],
        }
        cfg = {"targets": {}, "manual_metrics": {}}
        signals = build_weekly_signals(engagement, report, cfg)
        assert any(
            "UTM attribution coverage is low" in item for item in signals["highlights"]["risks"]
        )
        assert signals["kpis"]["alerts_count"] == 1
        assert len(signals["recommendations"]) > 0


class TestRenderWeeklySignalsMarkdown:
    def test_renders_sections(self):
        signals = {
            "generated_at": "2026-03-08T00:00:00+00:00",
            "period": {"start": "2026-03-01", "end": "2026-03-08"},
            "kpis": {
                "page_views": 100,
                "unique_visitors": 80,
                "views_delta_pct": 5.0,
                "visitors_delta_pct": 3.0,
                "tracked_views_ratio_pct": 70.0,
                "total_commits": 9,
                "total_prs": 2,
                "total_releases": 1,
                "alerts_count": 0,
            },
            "outcome_progress": {
                "stranger_tests_completed": {"current": 1, "target": 10, "progress_pct": 10.0}
            },
            "highlights": {"strengths": ["Good"], "risks": []},
            "recommendations": ["Keep going"],
        }
        md = render_weekly_signals_markdown(signals)
        assert "# Weekly Signals" in md
        assert "## KPI Snapshot" in md
        assert "## Outcome Progress" in md


class TestGenerateSignals:
    def test_writes_json_and_markdown(self, tmp_path):
        inp = tmp_path / "input"
        out = tmp_path / "output"
        cfg = tmp_path / "kpis.yaml"
        inp.mkdir()

        (inp / "engagement-metrics.json").write_text(
            json.dumps(
                {
                    "period": {"start": "2026-03-01", "end": "2026-03-08"},
                    "site_totals": {"page_views": 100, "unique_visitors": 80},
                    "trends": {"views_delta_pct": 2.0, "visitors_delta_pct": 1.0},
                }
            )
        )
        (inp / "system-engagement-report.json").write_text(
            json.dumps(
                {
                    "distribution": {"tracked_views_ratio_pct": 65.0},
                    "github_activity": {"total_commits": 8, "total_prs": 2, "total_releases": 0},
                    "alerts": [],
                }
            )
        )
        cfg.write_text(
            "targets:\n"
            "  stranger_tests_completed: 10\n"
            "manual_metrics:\n"
            "  stranger_tests_completed: 3\n"
        )

        result = generate_signals(str(inp), str(out), str(cfg))
        assert (out / "weekly-signals.json").exists()
        assert (out / "weekly-signals.md").exists()
        assert result["json"].endswith("weekly-signals.json")
