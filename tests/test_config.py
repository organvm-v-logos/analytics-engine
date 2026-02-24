"""Tests for configuration management."""

from pathlib import Path

from src.config import (
    ORG_TO_ORGAN,
    EngineConfig,
    GitHubConfig,
    GoatCounterConfig,
    ThresholdsConfig,
)

FIXTURES = Path(__file__).parent / "fixtures"
THRESHOLDS_YAML = Path(__file__).parent.parent / "config" / "thresholds.yaml"


class TestGoatCounterConfig:
    def test_not_configured_by_default(self):
        config = GoatCounterConfig()
        assert not config.configured

    def test_configured_with_both_values(self):
        config = GoatCounterConfig(site="organvm", token="tok_abc123")  # allow-secret
        assert config.configured

    def test_not_configured_without_token(self):
        config = GoatCounterConfig(site="organvm", token="")  # allow-secret
        assert not config.configured

    def test_api_url_formatting(self):
        config = GoatCounterConfig(site="organvm", token="tok_abc123")  # allow-secret
        assert config.api_url == "https://organvm.goatcounter.com/api/v0"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("GOATCOUNTER_SITE", "testsite")
        monkeypatch.setenv("GOATCOUNTER_TOKEN", "tok_test")  # allow-secret
        config = GoatCounterConfig.from_env()
        assert config.site == "testsite"
        assert config.token == "tok_test"  # allow-secret
        assert config.configured

    def test_from_env_missing(self, monkeypatch):
        monkeypatch.delenv("GOATCOUNTER_SITE", raising=False)
        monkeypatch.delenv("GOATCOUNTER_TOKEN", raising=False)
        config = GoatCounterConfig.from_env()
        assert not config.configured


class TestGitHubConfig:
    def test_not_configured_by_default(self):
        config = GitHubConfig()
        assert not config.configured

    def test_configured_with_token(self):
        config = GitHubConfig(token="ghp_abc123")  # allow-secret
        assert config.configured

    def test_default_orgs(self):
        config = GitHubConfig()
        assert len(config.orgs) == 8
        assert "organvm-v-logos" in config.orgs

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")  # allow-secret
        config = GitHubConfig.from_env()
        assert config.configured
        assert config.token == "ghp_test"  # allow-secret


class TestOrgToOrgan:
    def test_all_orgs_mapped(self):
        config = GitHubConfig()
        for org in config.orgs:
            assert org in ORG_TO_ORGAN, f"Org {org} missing from ORG_TO_ORGAN"

    def test_organ_numerals(self):
        assert ORG_TO_ORGAN["ivviiviivvi"] == "I"
        assert ORG_TO_ORGAN["organvm-v-logos"] == "V"
        assert ORG_TO_ORGAN["meta-organvm"] == "META"


class TestThresholdsConfig:
    def test_load_from_yaml(self):
        config = ThresholdsConfig.from_yaml(THRESHOLDS_YAML)
        assert len(config.rules) == 4

    def test_rule_properties(self):
        config = ThresholdsConfig.from_yaml(THRESHOLDS_YAML)
        traffic_drop = next(r for r in config.rules if r.name == "traffic_drop")
        assert traffic_drop.operator == "<"
        assert traffic_drop.value == -50
        assert traffic_drop.severity == "warning"

    def test_missing_file_returns_empty(self, tmp_path):
        config = ThresholdsConfig.from_yaml(tmp_path / "nonexistent.yaml")
        assert config.rules == []

    def test_empty_file_returns_empty(self, tmp_path):
        (tmp_path / "empty.yaml").write_text("")
        config = ThresholdsConfig.from_yaml(tmp_path / "empty.yaml")
        assert config.rules == []


class TestEngineConfig:
    def test_from_env(self, monkeypatch):
        monkeypatch.delenv("GOATCOUNTER_SITE", raising=False)
        monkeypatch.delenv("GOATCOUNTER_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        config = EngineConfig.from_env()
        assert not config.goatcounter.configured
        assert not config.github.configured
        assert config.history_dir == "data/history"
