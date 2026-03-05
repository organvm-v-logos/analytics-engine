"""Tests for the GitHub activity collector."""

from unittest.mock import MagicMock, patch

from src.config import GitHubConfig
from src.github_activity import (
    collect_activity,
    count_org_events,
    fetch_github_api,
    main,
    unconfigured_result,
)


class TestFetchGitHubApi:
    @patch("urllib.request.urlopen")
    def test_successful_request(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"test": "ok"}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        config = GitHubConfig(token="test")
        result = fetch_github_api(config, "/test")
        assert result == {"test": "ok"}

    @patch("urllib.request.urlopen")
    def test_handles_http_error(self, mock_urlopen):
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError("url", 404, "Not Found", {}, None)

        config = GitHubConfig(token="test")
        try:
            fetch_github_api(config, "/test")
        except urllib.error.HTTPError as e:
            assert e.code == 404


class TestGithubMain:
    @patch("src.github_activity.collect_activity")
    @patch("src.github_activity.GitHubConfig.from_env")
    @patch("sys.exit")
    def test_main_runs(self, mock_exit, mock_config, mock_collect, tmp_path):
        mock_config.return_value = MagicMock(configured=True)
        mock_collect.return_value = {
            "totals": {"commits": 10, "prs": 2, "releases": 1},
            "period": {"end": "2026-03-05"},
        }

        output_dir = tmp_path / "raw"
        with patch("sys.argv", ["prog", "--output", str(output_dir)]):
            main()

        assert (output_dir / "github-activity-2026-03-05.json").exists()
        mock_exit.assert_called_with(0)


class TestUnconfiguredResult:
    def test_has_correct_structure(self):
        result = unconfigured_result(7)
        assert result["source"] == "github"
        assert result["available"] is False
        assert result["totals"]["commits"] == 0
        assert result["organ_breakdown"] == {}

    def test_respects_days_parameter(self):
        result = unconfigured_result(14)
        assert result["period"]["days"] == 14


class TestCountOrgEvents:
    @patch("src.github_activity.fetch_github_api")
    def test_counts_push_events(self, mock_api):
        mock_api.return_value = [
            {
                "type": "PushEvent",
                "created_at": "2026-02-20T10:00:00Z",
                "payload": {"size": 3},
            },
            {
                "type": "PushEvent",
                "created_at": "2026-02-21T10:00:00Z",
                "payload": {"size": 2},
            },
        ]
        config = GitHubConfig(token="ghp_test")  # allow-secret

        from datetime import date

        counts = count_org_events(config, "organvm-v-logos", date(2026, 2, 17))
        assert counts["commits"] == 5
        assert counts["prs"] == 0

    @patch("src.github_activity.fetch_github_api")
    def test_counts_pr_events(self, mock_api):
        mock_api.return_value = [
            {
                "type": "PullRequestEvent",
                "created_at": "2026-02-20T10:00:00Z",
                "payload": {"action": "opened"},
            },
            {
                "type": "PullRequestEvent",
                "created_at": "2026-02-21T10:00:00Z",
                "payload": {"action": "closed"},
            },
            {
                "type": "PullRequestEvent",
                "created_at": "2026-02-22T10:00:00Z",
                "payload": {"action": "synchronize"},
            },
        ]
        config = GitHubConfig(token="ghp_test")  # allow-secret

        from datetime import date

        counts = count_org_events(config, "organvm-v-logos", date(2026, 2, 17))
        assert counts["prs"] == 2  # only opened + closed count

    @patch("src.github_activity.fetch_github_api")
    def test_filters_by_date(self, mock_api):
        mock_api.return_value = [
            {
                "type": "PushEvent",
                "created_at": "2026-02-20T10:00:00Z",
                "payload": {"size": 3},
            },
            {
                "type": "PushEvent",
                "created_at": "2026-02-10T10:00:00Z",  # before since date
                "payload": {"size": 5},
            },
        ]
        config = GitHubConfig(token="ghp_test")  # allow-secret

        from datetime import date

        counts = count_org_events(config, "organvm-v-logos", date(2026, 2, 17))
        assert counts["commits"] == 3  # only the one after since date

    @patch("src.github_activity.fetch_github_api")
    def test_handles_api_error(self, mock_api):
        import urllib.error

        mock_api.side_effect = urllib.error.URLError("Connection refused")

        config = GitHubConfig(token="ghp_test")  # allow-secret

        from datetime import date

        counts = count_org_events(config, "organvm-v-logos", date(2026, 2, 17))
        assert counts == {"commits": 0, "prs": 0, "releases": 0}

    @patch("src.github_activity.fetch_github_api")
    def test_counts_release_events(self, mock_api):
        mock_api.return_value = [
            {
                "type": "ReleaseEvent",
                "created_at": "2026-02-20T10:00:00Z",
                "payload": {},
            },
        ]
        config = GitHubConfig(token="ghp_test")  # allow-secret

        from datetime import date

        counts = count_org_events(config, "organvm-v-logos", date(2026, 2, 17))
        assert counts["releases"] == 1


class TestCollectActivity:
    @patch("src.github_activity.count_org_events")
    def test_aggregates_across_orgs(self, mock_count):
        mock_count.return_value = {"commits": 5, "prs": 2, "releases": 1}
        config = GitHubConfig(
            token="ghp_test",
            orgs=["organvm-v-logos", "meta-organvm"],
        )  # allow-secret

        result = collect_activity(config, days=7)
        assert result["totals"]["commits"] == 10  # 5 per org * 2 orgs
        assert result["totals"]["prs"] == 4
        assert result["totals"]["releases"] == 2
        assert "V" in result["organ_breakdown"]
        assert "META" in result["organ_breakdown"]

    @patch("src.github_activity.count_org_events")
    def test_output_structure(self, mock_count):
        mock_count.return_value = {"commits": 0, "prs": 0, "releases": 0}
        config = GitHubConfig(token="ghp_test", orgs=["organvm-v-logos"])  # allow-secret

        result = collect_activity(config, days=14)
        assert result["source"] == "github"
        assert "collected_at" in result
        assert result["available"] is True
        assert result["period"]["days"] == 14
        assert "start" in result["period"]
        assert "end" in result["period"]
        assert "totals" in result
        assert "organ_breakdown" in result
