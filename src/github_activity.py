"""GitHub activity collector for analytics-engine.

Collects commit counts, PR activity, and release events across
all ORGANVM GitHub organizations. Uses stdlib urllib only.

CLI: python -m src.github_activity --days 7 --output data/raw/
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.config import ORG_TO_ORGAN, GitHubConfig


def fetch_github_api(config: GitHubConfig, endpoint: str) -> list | dict:
    """Make an authenticated GET request to the GitHub API."""
    url = f"{config.base_url}{endpoint}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {config.token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def count_org_events(config: GitHubConfig, org: str, since: date) -> dict:
    """Count commits, PRs, and releases for an org since the given date.

    Uses the /orgs/{org}/events endpoint (public events, last 90 days).
    """
    commits = 0
    prs = 0
    releases = 0

    try:
        events = fetch_github_api(config, f"/orgs/{org}/events?per_page=100")
        if not isinstance(events, list):
            events = []
    except (urllib.error.URLError, urllib.error.HTTPError):
        return {"commits": 0, "prs": 0, "releases": 0}

    since_str = since.isoformat()
    for event in events:
        created = event.get("created_at", "")[:10]
        if created < since_str:
            continue

        event_type = event.get("type", "")
        if event_type == "PushEvent":
            payload = event.get("payload", {})
            commits += payload.get("size", 0)
        elif event_type == "PullRequestEvent":
            action = event.get("payload", {}).get("action", "")
            if action in ("opened", "closed"):
                prs += 1
        elif event_type == "ReleaseEvent":
            releases += 1

    return {"commits": commits, "prs": prs, "releases": releases}


def collect_activity(config: GitHubConfig, days: int = 7) -> dict:
    """Collect GitHub activity across all ORGANVM orgs.

    Returns a structured dict ready for JSON serialization.
    """
    end = date.today()
    start = end - timedelta(days=days)

    organ_breakdown: dict[str, dict] = {}
    total_commits = 0
    total_prs = 0
    total_releases = 0

    for org in config.orgs:
        organ = ORG_TO_ORGAN.get(org, org)
        counts = count_org_events(config, org, start)
        organ_breakdown[organ] = counts
        total_commits += counts["commits"]
        total_prs += counts["prs"]
        total_releases += counts["releases"]

    return {
        "source": "github",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "available": True,
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": days,
        },
        "totals": {
            "commits": total_commits,
            "prs": total_prs,
            "releases": total_releases,
        },
        "organ_breakdown": organ_breakdown,
    }


def unconfigured_result(days: int = 7) -> dict:
    """Return a placeholder result when GitHub token is not configured."""
    end = date.today()
    start = end - timedelta(days=days)
    return {
        "source": "github",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "available": False,
        "reason": "GITHUB_TOKEN not set",
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": days,
        },
        "totals": {
            "commits": 0,
            "prs": 0,
            "releases": 0,
        },
        "organ_breakdown": {},
    }


def main():
    parser = argparse.ArgumentParser(
        description="Collect GitHub activity across ORGANVM organizations"
    )
    parser.add_argument(
        "--days", type=int, default=7, help="Number of days to collect (default: 7)"
    )
    parser.add_argument("--output", required=True, help="Output directory for raw JSON")
    args = parser.parse_args()

    config = GitHubConfig.from_env()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not config.configured:
        print("GitHub token not configured — writing placeholder", file=sys.stderr)
        result = unconfigured_result(args.days)
    else:
        try:
            result = collect_activity(config, args.days)
            print(f"Collected activity: {result['totals']['commits']} commits, "
                  f"{result['totals']['prs']} PRs, {result['totals']['releases']} releases")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"GitHub API error: {e} — writing placeholder", file=sys.stderr)
            result = unconfigured_result(args.days)
            result["reason"] = f"API error: {e}"

    today = date.today().isoformat()
    output_file = output_dir / f"github-activity-{today}.json"
    output_file.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {output_file}")
    sys.exit(0)


if __name__ == "__main__":
    main()
