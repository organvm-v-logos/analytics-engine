"""Static HTML dashboard generator for analytics-engine.

Produces a self-contained HTML page with inline CSS and inline SVG
charts. Zero JavaScript dependencies.

CLI: python -m src.dashboard --input data/ --output docs/dashboard/
"""

import argparse
import json
import sys
from pathlib import Path


def sparkline_svg(values: list[int | float], width: int = 200, height: int = 40) -> str:
    """Generate an inline SVG sparkline from a list of values."""
    if not values or all(v == 0 for v in values):
        return (
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
            f'<text x="{width // 2}" y="{height // 2 + 4}" text-anchor="middle" '
            f'fill="#999" font-size="11">No data</text></svg>'
        )

    max_val = max(values) or 1
    n = len(values)
    step = width / max(n - 1, 1)
    points = []
    for i, v in enumerate(values):
        x = round(i * step, 1)
        y = round(height - (v / max_val) * (height - 4) - 2, 1)
        points.append(f"{x},{y}")

    polyline = " ".join(points)
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'<polyline points="{polyline}" fill="none" stroke="#0d47a1" stroke-width="2" />'
        f'</svg>'
    )


def bar_chart_svg(
    labels: list[str],
    values: list[int | float],
    width: int = 400,
    bar_height: int = 24,
) -> str:
    """Generate an inline SVG horizontal bar chart."""
    if not labels:
        return (
            f'<svg width="{width}" height="40" xmlns="http://www.w3.org/2000/svg">'
            f'<text x="{width // 2}" y="20" text-anchor="middle" '
            f'fill="#999" font-size="11">No data</text></svg>'
        )

    max_val = max(values) or 1
    padding = 8
    label_width = 80
    chart_width = width - label_width - 60
    total_height = len(labels) * (bar_height + padding) + padding

    bars = []
    for i, (label, val) in enumerate(zip(labels, values)):
        y = padding + i * (bar_height + padding)
        bar_w = max(round((val / max_val) * chart_width, 1), 1)
        bars.append(
            f'<text x="{label_width - 4}" y="{y + bar_height // 2 + 4}" '
            f'text-anchor="end" fill="#333" font-size="12">{label}</text>'
            f'<rect x="{label_width}" y="{y}" width="{bar_w}" height="{bar_height}" '
            f'fill="#0d47a1" rx="3" />'
            f'<text x="{label_width + bar_w + 6}" y="{y + bar_height // 2 + 4}" '
            f'fill="#666" font-size="11">{val}</text>'
        )

    return (
        f'<svg width="{width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">'
        + "".join(bars)
        + '</svg>'
    )


def pages_table_html(pages: list[dict]) -> str:
    """Generate an HTML table of page metrics."""
    if not pages:
        return '<p class="empty-notice">No page data available.</p>'

    rows = []
    for p in sorted(pages, key=lambda x: x.get("views", 0), reverse=True):
        path = p.get("path", "")
        title = p.get("title", path)
        views = p.get("views", 0)
        unique = p.get("unique_visitors", 0)
        rows.append(
            f"<tr><td>{title}</td><td>{path}</td>"
            f"<td class='num'>{views}</td><td class='num'>{unique}</td></tr>"
        )

    return (
        '<table><thead><tr>'
        '<th>Title</th><th>Path</th><th>Views</th><th>Unique</th>'
        '</tr></thead><tbody>'
        + "".join(rows)
        + '</tbody></table>'
    )


def trend_indicator(delta_pct: float | None) -> str:
    """Return an HTML string showing trend direction and magnitude."""
    if delta_pct is None:
        return '<span class="trend neutral">--</span>'
    if delta_pct > 0:
        arrow = "&#9650;"
        cls = "up"
    elif delta_pct < 0:
        arrow = "&#9660;"
        cls = "down"
    else:
        arrow = "&#9654;"
        cls = "neutral"
    return f'<span class="trend {cls}">{arrow} {delta_pct:+.1f}%</span>'


def alerts_html(alerts: list[dict]) -> str:
    """Render alert entries as HTML."""
    if not alerts:
        return '<p class="empty-notice">No alerts triggered.</p>'

    items = []
    for a in alerts:
        severity = a.get("severity", "info")
        desc = a.get("description", a.get("rule", ""))
        items.append(f'<li class="alert-{severity}">{desc}</li>')
    return '<ul class="alerts">' + "".join(items) + '</ul>'


def render_dashboard(engagement: dict, report: dict) -> str:
    """Render the full dashboard as a self-contained HTML page."""
    period = engagement.get("period", {})
    totals = engagement.get("site_totals", {})
    pages = engagement.get("pages", [])
    trends = engagement.get("trends", {})
    gh = report.get("github_activity", {})
    report_alerts = report.get("alerts", [])

    # Prepare organ bar chart data
    organ_data = gh.get("organ_breakdown", {})
    organ_labels = sorted(organ_data.keys())
    organ_commits = [organ_data[o].get("commits", 0) for o in organ_labels]

    views_trend = trend_indicator(trends.get("views_delta_pct"))
    visitors_trend = trend_indicator(trends.get("visitors_delta_pct"))

    has_data = totals.get("page_views", 0) > 0 or gh.get("total_commits", 0) > 0

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ORGAN-V Analytics Dashboard</title>
<style>
  :root {{ --primary: #0d47a1; --bg: #fafafa; --card: #fff; --border: #e0e0e0;
           --text: #333; --muted: #999; --up: #2e7d32; --down: #c62828; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.6; padding: 2rem; max-width: 960px; margin: 0 auto; }}
  h1 {{ color: var(--primary); margin-bottom: 0.25rem; }}
  .subtitle {{ color: var(--muted); margin-bottom: 2rem; font-size: 0.9rem; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; }}
  .card h3 {{ font-size: 0.8rem; text-transform: uppercase; color: var(--muted); margin-bottom: 0.5rem; }}
  .card .value {{ font-size: 2rem; font-weight: 700; color: var(--primary); }}
  .trend {{ font-size: 0.85rem; margin-left: 0.5rem; }}
  .trend.up {{ color: var(--up); }}
  .trend.down {{ color: var(--down); }}
  .trend.neutral {{ color: var(--muted); }}
  section {{ margin-bottom: 2rem; }}
  section h2 {{ color: var(--primary); margin-bottom: 1rem; font-size: 1.2rem; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--card); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 0.6rem 1rem; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ background: #f5f5f5; font-size: 0.8rem; text-transform: uppercase; color: var(--muted); }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .empty-notice {{ color: var(--muted); font-style: italic; padding: 1rem; background: var(--card); border: 1px solid var(--border); border-radius: 8px; text-align: center; }}
  .alerts li {{ list-style: none; padding: 0.5rem 1rem; margin-bottom: 0.5rem; border-radius: 4px; }}
  .alert-warning {{ background: #fff3e0; border-left: 4px solid #ff9800; }}
  .alert-info {{ background: #e3f2fd; border-left: 4px solid #2196f3; }}
  footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.8rem; }}
</style>
</head>
<body>
<h1>ORGAN-V Analytics Dashboard</h1>
<p class="subtitle">Period: {period.get("start", "N/A")} to {period.get("end", "N/A")} | Generated: {engagement.get("generated_at", "N/A")[:10]}</p>

{"" if has_data else '<div class="empty-notice" style="margin-bottom:2rem">No analytics data collected yet. Configure GoatCounter and GitHub tokens to start tracking.</div>'}

<div class="cards">
  <div class="card">
    <h3>Page Views</h3>
    <div class="value">{totals.get("page_views", 0):,}</div>
    {views_trend}
  </div>
  <div class="card">
    <h3>Unique Visitors</h3>
    <div class="value">{totals.get("unique_visitors", 0):,}</div>
    {visitors_trend}
  </div>
  <div class="card">
    <h3>Total Commits</h3>
    <div class="value">{gh.get("total_commits", 0):,}</div>
  </div>
  <div class="card">
    <h3>Pull Requests</h3>
    <div class="value">{gh.get("total_prs", 0):,}</div>
  </div>
</div>

<section>
  <h2>Pages</h2>
  {pages_table_html(pages)}
</section>

<section>
  <h2>Commits by Organ</h2>
  {bar_chart_svg(organ_labels, organ_commits)}
</section>

<section>
  <h2>Alerts</h2>
  {alerts_html(report_alerts)}
</section>

<footer>
  ORGAN-V: Logos &mdash; analytics-engine v0.2.0 &mdash; Privacy-first analytics via GoatCounter
</footer>
</body>
</html>
"""


def generate_dashboard(input_dir: str, output_dir: str) -> str:
    """Load aggregated data and generate the dashboard HTML.

    Returns the path to the generated dashboard file.
    """
    inp = Path(input_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    engagement_path = inp / "engagement-metrics.json"
    report_path = inp / "system-engagement-report.json"

    if engagement_path.exists():
        engagement = json.loads(engagement_path.read_text())
    else:
        engagement = {
            "generated_at": "",
            "period": {},
            "site_totals": {"page_views": 0, "unique_visitors": 0, "referrer_count": 0},
            "pages": [],
            "trends": {"views_delta_pct": None, "visitors_delta_pct": None},
        }

    if report_path.exists():
        report = json.loads(report_path.read_text())
    else:
        report = {
            "generated_at": "",
            "period": {},
            "web_engagement": {"total_views": 0, "total_visitors": 0, "top_essay": None},
            "github_activity": {"total_commits": 0, "total_prs": 0, "total_releases": 0,
                                "organ_breakdown": {}},
            "alerts": [],
        }

    html = render_dashboard(engagement, report)
    output_file = out / "index.html"
    output_file.write_text(html)
    return str(output_file)


def main():
    parser = argparse.ArgumentParser(
        description="Generate static HTML analytics dashboard"
    )
    parser.add_argument("--input", required=True, help="Input directory with aggregated JSON")
    parser.add_argument("--output", required=True, help="Output directory for dashboard HTML")
    args = parser.parse_args()

    path = generate_dashboard(args.input, args.output)
    print(f"Dashboard generated: {path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
