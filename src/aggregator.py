"""Metric aggregation engine for analytics-engine.

Merges raw GoatCounter and GitHub data into two output artifacts:
- engagement-metrics.json (for ORGAN-V editorial use)
- system-engagement-report.json (for ORGAN-IV orchestration)

Maintains rolling history in data/history/ for trend computation.

CLI: python -m src.aggregator --input data/raw/ --output data/
"""

import argparse
import json
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from src.config import ThresholdsConfig


def load_latest_raw(raw_dir: Path, prefix: str) -> dict | None:
    """Load the most recent raw JSON file matching the given prefix."""
    files = sorted(raw_dir.glob(f"{prefix}-*.json"), reverse=True)
    if not files:
        return None
    with open(files[0]) as f:
        return json.loads(f.read())


def load_previous_metrics(history_dir: Path) -> dict | None:
    """Load the most recent engagement-metrics.json from history."""
    files = sorted(history_dir.glob("engagement-metrics-*.json"), reverse=True)
    if not files:
        return None
    with open(files[0]) as f:
        return json.loads(f.read())


def compute_trend(current: int | float, previous: int | float | None) -> float | None:
    """Compute week-over-week percentage change."""
    if previous is None or previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def check_thresholds(
    thresholds: ThresholdsConfig,
    goatcounter_data: dict,
    github_data: dict,
    trends: dict,
) -> list[dict]:
    """Check all threshold rules and return triggered alerts."""
    alerts = []
    metric_values = {
        "views_delta_pct": trends.get("views_delta_pct"),
        "visitors_delta_pct": trends.get("visitors_delta_pct"),
        "total_commits": github_data.get("totals", {}).get("commits", 0),
    }

    # Check per-page zero traffic
    pages = goatcounter_data.get("pages", [])
    has_zero_traffic = any(p.get("count", 0) == 0 for p in pages) if pages else False

    for rule in thresholds.rules:
        if rule.metric == "page_views" and rule.operator == "==" and rule.value == 0:
            if has_zero_traffic and goatcounter_data.get("available", False):
                alerts.append({
                    "rule": rule.name,
                    "description": rule.description,
                    "severity": rule.severity,
                    "triggered_at": datetime.now(timezone.utc).isoformat(),
                })
            continue

        # Skip referrer_share_pct — not implemented in this scope
        if rule.metric == "referrer_share_pct":
            continue

        value = metric_values.get(rule.metric)
        if value is None:
            continue

        triggered = False
        if rule.operator == "<" and value < rule.value:
            triggered = True
        elif rule.operator == ">" and value > rule.value:
            triggered = True
        elif rule.operator == "==" and value == rule.value:
            triggered = True

        if triggered:
            alerts.append({
                "rule": rule.name,
                "description": rule.description,
                "severity": rule.severity,
                "current_value": value,
                "threshold": rule.value,
                "triggered_at": datetime.now(timezone.utc).isoformat(),
            })

    return alerts


def build_engagement_metrics(goatcounter_data: dict, previous: dict | None) -> dict:
    """Build the engagement-metrics.json artifact."""
    period = goatcounter_data.get("period", {})
    site_totals = goatcounter_data.get("site_totals", {})
    pages = goatcounter_data.get("pages", [])

    prev_totals = (previous or {}).get("site_totals", {})
    prev_views = prev_totals.get("page_views")
    prev_visitors = prev_totals.get("unique_visitors")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": {
            "start": period.get("start", ""),
            "end": period.get("end", ""),
        },
        "site_totals": {
            "page_views": site_totals.get("page_views", 0),
            "unique_visitors": site_totals.get("unique_visitors", 0),
            "referrer_count": 0,
        },
        "pages": [
            {
                "path": p.get("path", ""),
                "title": p.get("title", ""),
                "views": p.get("count", 0),
                "unique_visitors": p.get("count_unique", 0),
            }
            for p in pages
        ],
        "trends": {
            "views_delta_pct": compute_trend(
                site_totals.get("page_views", 0), prev_views
            ),
            "visitors_delta_pct": compute_trend(
                site_totals.get("unique_visitors", 0), prev_visitors
            ),
        },
    }


def build_system_report(
    goatcounter_data: dict,
    github_data: dict,
    alerts: list[dict],
) -> dict:
    """Build the system-engagement-report.json artifact."""
    gc_period = goatcounter_data.get("period", {})
    gh_period = github_data.get("period", {})

    # Use whichever period is available
    period_start = gc_period.get("start") or gh_period.get("start", "")
    period_end = gc_period.get("end") or gh_period.get("end", "")

    site_totals = goatcounter_data.get("site_totals", {})
    pages = goatcounter_data.get("pages", [])
    top_essay = None
    if pages:
        top_page = max(pages, key=lambda p: p.get("count", 0))
        path = top_page.get("path", "")
        # Extract slug from path like /essays/meta-system/01-orchestrate/
        parts = [p for p in path.strip("/").split("/") if p]
        top_essay = parts[-1] if parts else path

    gh_totals = github_data.get("totals", {})
    organ_breakdown = github_data.get("organ_breakdown", {})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": {
            "start": period_start,
            "end": period_end,
        },
        "web_engagement": {
            "total_views": site_totals.get("page_views", 0),
            "total_visitors": site_totals.get("unique_visitors", 0),
            "top_essay": top_essay,
        },
        "github_activity": {
            "total_commits": gh_totals.get("commits", 0),
            "total_prs": gh_totals.get("prs", 0),
            "total_releases": gh_totals.get("releases", 0),
            "organ_breakdown": organ_breakdown,
        },
        "alerts": alerts,
    }


def save_to_history(output_dir: Path, history_dir: Path) -> None:
    """Copy current output artifacts to the history directory with date suffix."""
    history_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    for name in ("engagement-metrics.json", "system-engagement-report.json"):
        src = output_dir / name
        if src.exists():
            dst = history_dir / f"{name.replace('.json', '')}-{today}.json"
            shutil.copy2(src, dst)


def aggregate(
    raw_dir: str,
    output_dir: str,
    history_dir: str = "data/history",
    thresholds: ThresholdsConfig | None = None,
) -> dict:
    """Run the full aggregation pipeline.

    Returns a summary dict with counts.
    """
    raw = Path(raw_dir)
    out = Path(output_dir)
    hist = Path(history_dir)
    out.mkdir(parents=True, exist_ok=True)

    if thresholds is None:
        thresholds = ThresholdsConfig.default()

    # Load raw data
    goatcounter_data = load_latest_raw(raw, "goatcounter") or {
        "available": False,
        "period": {},
        "site_totals": {"page_views": 0, "unique_visitors": 0},
        "pages": [],
    }
    github_data = load_latest_raw(raw, "github-activity") or {
        "available": False,
        "period": {},
        "totals": {"commits": 0, "prs": 0, "releases": 0},
        "organ_breakdown": {},
    }

    # Load previous for trend computation
    previous = load_previous_metrics(hist)

    # Build output artifacts
    engagement = build_engagement_metrics(goatcounter_data, previous)
    trends = engagement["trends"]

    alerts = check_thresholds(thresholds, goatcounter_data, github_data, trends)
    report = build_system_report(goatcounter_data, github_data, alerts)

    # Write outputs
    (out / "engagement-metrics.json").write_text(
        json.dumps(engagement, indent=2, ensure_ascii=False) + "\n"
    )
    (out / "system-engagement-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    )

    # Save to history
    save_to_history(out, hist)

    return {
        "goatcounter_available": goatcounter_data.get("available", False),
        "github_available": github_data.get("available", False),
        "page_count": len(engagement["pages"]),
        "alert_count": len(alerts),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate raw metrics into engagement reports"
    )
    parser.add_argument("--input", required=True, help="Input directory with raw JSON files")
    parser.add_argument("--output", required=True, help="Output directory for aggregated JSON")
    parser.add_argument("--history", default="data/history", help="History directory for trends")
    args = parser.parse_args()

    summary = aggregate(args.input, args.output, args.history)
    gc_status = "available" if summary["goatcounter_available"] else "unavailable"
    gh_status = "available" if summary["github_available"] else "unavailable"
    print(
        f"Aggregated: GoatCounter {gc_status}, GitHub {gh_status}, "
        f"{summary['page_count']} pages, {summary['alert_count']} alerts"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
