"""Weekly operating signals and KPI narrative generator.

Reads aggregated analytics artifacts and emits:
- weekly-signals.json
- weekly-signals.md
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

DEFAULT_TARGETS = {
    "stranger_tests_completed": 10,
    "external_feedback_items": 3,
    "external_contributions": 3,
    "community_events_hosted": 1,
    "revenue_events": 1,
}


def _load_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def _load_kpi_config(path: Path) -> dict:
    if not path.exists():
        return {"targets": DEFAULT_TARGETS, "manual_metrics": {}}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    targets = data.get("targets") or {}
    manual_metrics = data.get("manual_metrics") or {}
    resolved_targets = {**DEFAULT_TARGETS, **targets}
    return {
        "targets": resolved_targets,
        "manual_metrics": manual_metrics,
    }


def build_weekly_signals(engagement: dict, report: dict, kpi_config: dict) -> dict:
    """Build a weekly KPI/signal summary from aggregated artifacts."""
    totals = engagement.get("site_totals", {})
    trends = engagement.get("trends", {})
    github = report.get("github_activity", {})
    distribution = report.get("distribution", {})
    alerts = report.get("alerts", [])

    manual_metrics = kpi_config.get("manual_metrics", {})
    targets = kpi_config.get("targets", DEFAULT_TARGETS)

    outcome_progress = {}
    for metric, target in targets.items():
        current = int(manual_metrics.get(metric, 0))
        pct = round((current / target) * 100, 1) if target else 0.0
        outcome_progress[metric] = {
            "current": current,
            "target": target,
            "progress_pct": pct,
        }

    strengths = []
    risks = []
    recommendations = []

    views_delta = trends.get("views_delta_pct")
    if views_delta is not None and views_delta > 0:
        strengths.append(f"Web views increased by {views_delta:+.1f}% week-over-week.")
    elif views_delta is not None and views_delta < 0:
        risks.append(f"Web views declined by {views_delta:+.1f}% week-over-week.")
        recommendations.append("Run a distribution experiment on headline + CTA format.")

    tracked_ratio = distribution.get("tracked_views_ratio_pct", 0.0)
    if tracked_ratio >= 60:
        strengths.append(f"UTM attribution coverage is {tracked_ratio:.1f}% of views.")
    else:
        risks.append(f"UTM attribution coverage is low at {tracked_ratio:.1f}%.")
        recommendations.append("Increase UTM-tagged outbound campaigns for all distribution posts.")

    commits = github.get("total_commits", 0)
    if commits < 5:
        risks.append(f"GitHub commit volume is low ({commits}) for the period.")
        recommendations.append("Plan one focused implementation sprint to restore throughput.")
    else:
        strengths.append(f"GitHub activity remained healthy ({commits} commits).")

    if alerts:
        risks.append(f"{len(alerts)} threshold alert(s) triggered this period.")
        recommendations.append("Triage alerts and record remediation status in the weekly log.")

    if not recommendations:
        recommendations.append("Maintain current cadence and expand external feedback collection.")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": engagement.get("period", report.get("period", {})),
        "kpis": {
            "page_views": totals.get("page_views", 0),
            "unique_visitors": totals.get("unique_visitors", 0),
            "views_delta_pct": views_delta,
            "visitors_delta_pct": trends.get("visitors_delta_pct"),
            "tracked_views_ratio_pct": tracked_ratio,
            "total_commits": commits,
            "total_prs": github.get("total_prs", 0),
            "total_releases": github.get("total_releases", 0),
            "alerts_count": len(alerts),
        },
        "outcome_progress": outcome_progress,
        "highlights": {
            "strengths": strengths,
            "risks": risks,
        },
        "recommendations": recommendations,
    }


def render_weekly_signals_markdown(signals: dict) -> str:
    """Render weekly signals as concise markdown."""
    period = signals.get("period", {})
    kpis = signals.get("kpis", {})
    strengths = signals.get("highlights", {}).get("strengths", [])
    risks = signals.get("highlights", {}).get("risks", [])
    recommendations = signals.get("recommendations", [])
    progress = signals.get("outcome_progress", {})

    def _line_items(items: list[str]) -> str:
        if not items:
            return "- None"
        return "\n".join(f"- {item}" for item in items)

    progress_lines = []
    for metric, snapshot in progress.items():
        progress_lines.append(
            f"- `{metric}`: {snapshot['current']}/{snapshot['target']} "
            f"({snapshot['progress_pct']:.1f}%)"
        )

    return (
        "# Weekly Signals\n\n"
        f"- Period: {period.get('start', 'N/A')} to {period.get('end', 'N/A')}\n"
        f"- Generated: {signals.get('generated_at', '')}\n\n"
        "## KPI Snapshot\n\n"
        f"- Page views: {kpis.get('page_views', 0)}\n"
        f"- Unique visitors: {kpis.get('unique_visitors', 0)}\n"
        f"- Views delta: {kpis.get('views_delta_pct')}\n"
        f"- Visitors delta: {kpis.get('visitors_delta_pct')}\n"
        f"- Tracked views ratio: {kpis.get('tracked_views_ratio_pct', 0.0)}%\n"
        f"- Commits: {kpis.get('total_commits', 0)}\n"
        f"- PRs: {kpis.get('total_prs', 0)}\n"
        f"- Releases: {kpis.get('total_releases', 0)}\n"
        f"- Alerts: {kpis.get('alerts_count', 0)}\n\n"
        "## Strengths\n\n"
        f"{_line_items(strengths)}\n\n"
        "## Risks\n\n"
        f"{_line_items(risks)}\n\n"
        "## Outcome Progress\n\n"
        f"{_line_items(progress_lines)}\n\n"
        "## Recommendations\n\n"
        f"{_line_items(recommendations)}\n"
    )


def generate_signals(input_dir: str, output_dir: str, kpi_config: str) -> dict:
    """Generate weekly signal artifacts from aggregated analytics data."""
    inp = Path(input_dir)
    out = Path(output_dir)
    cfg = Path(kpi_config)
    out.mkdir(parents=True, exist_ok=True)

    engagement = _load_json(
        inp / "engagement-metrics.json",
        {
            "period": {},
            "site_totals": {"page_views": 0, "unique_visitors": 0},
            "trends": {"views_delta_pct": None, "visitors_delta_pct": None},
            "attribution": {"tracked_views_ratio_pct": 0.0},
        },
    )
    report = _load_json(
        inp / "system-engagement-report.json",
        {
            "period": {},
            "distribution": {"tracked_views_ratio_pct": 0.0},
            "github_activity": {"total_commits": 0, "total_prs": 0, "total_releases": 0},
            "alerts": [],
        },
    )
    kpi_cfg = _load_kpi_config(cfg)

    signals = build_weekly_signals(engagement, report, kpi_cfg)
    markdown = render_weekly_signals_markdown(signals)

    json_path = out / "weekly-signals.json"
    md_path = out / "weekly-signals.md"
    json_path.write_text(json.dumps(signals, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def main():
    parser = argparse.ArgumentParser(description="Generate weekly KPI signal artifacts")
    parser.add_argument(
        "--input",
        required=True,
        help="Input directory with aggregated analytics JSON",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for weekly signal artifacts",
    )
    parser.add_argument(
        "--kpi-config",
        default="config/outcome-kpis.yaml",
        help="Path to manual KPI progress config YAML",
    )
    args = parser.parse_args()

    result = generate_signals(args.input, args.output, args.kpi_config)
    print(f"Wrote {result['json']}")
    print(f"Wrote {result['markdown']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
