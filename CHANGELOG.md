# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-02-24

### Added

- `src/config.py` — Configuration management with env-based loading and `.configured` checks
- `src/goatcounter.py` — GoatCounter API client (stdlib urllib only, graceful degradation)
- `src/github_activity.py` — GitHub activity collector across all 8 ORGANVM orgs
- `src/aggregator.py` — Metric fusion: merges raw data, computes trends, checks thresholds
- `src/dashboard.py` — Static HTML dashboard generator (zero-JS, inline SVG charts)
- `config/thresholds.yaml` — Alert threshold definitions
- `config/env.example` — Example environment configuration
- 71 offline tests across 5 test modules (all fixture-driven, mocked APIs)
- `.github/workflows/ci.yml` — Full Python CI (ruff + pytest, Python 3.10/3.12)
- `.github/workflows/weekly-metrics.yml` — Monday 08:00 UTC cron pipeline
- Three produce edges now fulfilled: engagement-metrics, system-engagement-report, analytics-dashboard

### Changed

- `seed.yaml` implementation_status: SKELETON → CANDIDATE

## [0.1.0] - 2026-02-17

### Added

- Initial creation as part of ORGAN-V LOGOS Infrastructure Campaign
- Core project structure and documentation
- README with portfolio-quality documentation

[Unreleased]: https://github.com/organvm-v-logos/analytics-engine/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/organvm-v-logos/analytics-engine/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/organvm-v-logos/analytics-engine/releases/tag/v0.1.0
