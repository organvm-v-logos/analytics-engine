"""Configuration management for analytics-engine.

Loads settings from environment variables with sensible defaults.
All config objects expose a `.configured` property that returns True
only when the required credentials are present.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class GoatCounterConfig:
    """GoatCounter API configuration."""

    site: str = ""  # allow-secret
    token: str = ""  # allow-secret
    base_url: str = "https://{site}.goatcounter.com/api/v0"

    @property
    def configured(self) -> bool:
        return bool(self.site and self.token)

    @property
    def api_url(self) -> str:
        return self.base_url.format(site=self.site)

    @classmethod
    def from_env(cls) -> "GoatCounterConfig":
        return cls(
            site=os.environ.get("GOATCOUNTER_SITE", ""),  # allow-secret
            token=os.environ.get("GOATCOUNTER_TOKEN", ""),  # allow-secret
        )


@dataclass
class GitHubConfig:
    """GitHub API configuration."""

    token: str = ""  # allow-secret
    base_url: str = "https://api.github.com"
    orgs: list[str] = field(default_factory=lambda: [
        "ivviiviivvi",
        "omni-dromenon-machina",
        "labores-profani-crux",
        "organvm-iv-taxis",
        "organvm-v-logos",
        "organvm-vi-koinonia",
        "organvm-vii-kerygma",
        "meta-organvm",
    ])

    @property
    def configured(self) -> bool:
        return bool(self.token)

    @classmethod
    def from_env(cls) -> "GitHubConfig":
        return cls(
            token=os.environ.get("GITHUB_TOKEN", ""),  # allow-secret
        )


# Mapping from GitHub org name to ORGANVM organ numeral
ORG_TO_ORGAN: dict[str, str] = {
    "ivviiviivvi": "I",
    "omni-dromenon-machina": "II",
    "labores-profani-crux": "III",
    "organvm-iv-taxis": "IV",
    "organvm-v-logos": "V",
    "organvm-vi-koinonia": "VI",
    "organvm-vii-kerygma": "VII",
    "meta-organvm": "META",
}


@dataclass
class ThresholdRule:
    """A single alert threshold rule."""

    name: str
    description: str
    metric: str
    operator: str
    value: float
    severity: str = "warning"


@dataclass
class ThresholdsConfig:
    """Alert threshold configuration loaded from thresholds.yaml."""

    rules: list[ThresholdRule] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ThresholdsConfig":
        path = Path(path)
        if not path.exists():
            return cls()
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        rules = []
        for name, spec in data.items():
            rules.append(ThresholdRule(
                name=name,
                description=spec.get("description", ""),
                metric=spec.get("metric", ""),
                operator=spec.get("operator", ""),
                value=float(spec.get("value", 0)),
                severity=spec.get("severity", "warning"),
            ))
        return cls(rules=rules)

    @classmethod
    def default(cls) -> "ThresholdsConfig":
        config_path = Path(__file__).parent.parent / "config" / "thresholds.yaml"
        return cls.from_yaml(config_path)


@dataclass
class EngineConfig:
    """Top-level configuration aggregating all sub-configs."""

    goatcounter: GoatCounterConfig = field(default_factory=GoatCounterConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    history_dir: str = "data/history"
    raw_dir: str = "data/raw"
    output_dir: str = "data"
    dashboard_dir: str = "docs/dashboard"

    @classmethod
    def from_env(cls) -> "EngineConfig":
        return cls(
            goatcounter=GoatCounterConfig.from_env(),
            github=GitHubConfig.from_env(),
            thresholds=ThresholdsConfig.default(),
            history_dir=os.environ.get("METRICS_HISTORY_DIR", "data/history"),
        )
