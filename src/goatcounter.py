"""GoatCounter API client for analytics-engine.

Collects page views, unique visitors, and referrer data from the
GoatCounter API. Uses only stdlib urllib — no external HTTP dependencies.

CLI: python -m src.goatcounter --days 7 --output data/raw/
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.config import GoatCounterConfig


def fetch_api(config: GoatCounterConfig, endpoint: str, params: dict | None = None) -> dict:
    """Make an authenticated GET request to the GoatCounter API."""
    url = f"{config.api_url}{endpoint}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {config.token}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_page_hits(
    config: GoatCounterConfig,
    start: date,
    end: date,
) -> list[dict]:
    """Fetch per-page hit counts for the given date range.

    Returns a list of dicts with path, title, count, count_unique.
    """
    params = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "limit": "100",
    }
    data = fetch_api(config, "/stats/hits", params)
    pages = []
    for hit in data.get("hits", []):
        pages.append({
            "path": hit.get("path", ""),
            "title": hit.get("title", ""),
            "count": hit.get("count", 0),
            "count_unique": hit.get("count_unique", 0),
        })
    return pages


def fetch_total_stats(
    config: GoatCounterConfig,
    start: date,
    end: date,
) -> dict:
    """Fetch site-wide totals for the given date range."""
    params = {
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    data = fetch_api(config, "/stats/total", params)
    return {
        "total_count": data.get("total", {}).get("count", 0),
        "total_unique": data.get("total", {}).get("count_unique", 0),
    }


def collect_metrics(config: GoatCounterConfig, days: int = 7) -> dict:
    """Collect all GoatCounter metrics for the given number of days.

    Returns a structured dict ready for JSON serialization.
    """
    end = date.today()
    start = end - timedelta(days=days)

    pages = fetch_page_hits(config, start, end)
    totals = fetch_total_stats(config, start, end)

    total_views = sum(p["count"] for p in pages)
    total_unique = sum(p["count_unique"] for p in pages)

    return {
        "source": "goatcounter",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "available": True,
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": days,
        },
        "site_totals": {
            "page_views": totals.get("total_count", total_views),
            "unique_visitors": totals.get("total_unique", total_unique),
        },
        "pages": pages,
    }


def unconfigured_result(days: int = 7) -> dict:
    """Return a placeholder result when GoatCounter is not configured."""
    end = date.today()
    start = end - timedelta(days=days)
    return {
        "source": "goatcounter",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "available": False,
        "reason": "GOATCOUNTER_SITE and/or GOATCOUNTER_TOKEN not set",
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": days,
        },
        "site_totals": {
            "page_views": 0,
            "unique_visitors": 0,
        },
        "pages": [],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Collect GoatCounter metrics for ORGAN-V public-process"
    )
    parser.add_argument(
        "--days", type=int, default=7, help="Number of days to collect (default: 7)"
    )
    parser.add_argument("--output", required=True, help="Output directory for raw JSON")
    args = parser.parse_args()

    config = GoatCounterConfig.from_env()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not config.configured:
        print("GoatCounter not configured — writing placeholder", file=sys.stderr)
        result = unconfigured_result(args.days)
    else:
        try:
            result = collect_metrics(config, args.days)
            print(f"Collected metrics: {result['site_totals']['page_views']} views")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"GoatCounter API error: {e} — writing placeholder", file=sys.stderr)
            result = unconfigured_result(args.days)
            result["reason"] = f"API error: {e}"

    today = date.today().isoformat()
    output_file = output_dir / f"goatcounter-{today}.json"
    output_file.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {output_file}")
    sys.exit(0)


if __name__ == "__main__":
    main()
