# ADR 001: Initial Architecture Decisions

## Status

Accepted

## Date

2026-02-17

## Context

analytics-engine needs to collect web engagement metrics from the public-process Jekyll site, combine them with GitHub activity data across all eight organs, and produce actionable reports and dashboards. The initial architecture must choose a programming language, an analytics data source, a data interchange format, and a dashboard hosting strategy.

The system operates under several constraints:

- **Budget**: Zero recurring infrastructure cost at skeleton stage. Free tiers only.
- **Privacy**: The organvm system's values prohibit surveillance-grade analytics. No cookies, no personal data collection, no third-party data sharing.
- **Simplicity**: A single maintainer manages the entire eight-organ system. Operational complexity must be minimal.
- **Portability**: All artifacts should be hostable on GitHub Pages without additional infrastructure.
- **Automation**: The pipeline must run unattended via GitHub Actions on a weekly schedule.

## Decision

### Python as the Implementation Language

Python is selected as the sole implementation language for the analytics engine pipeline.

**Rationale:**
- The pipeline is a data-processing workflow (API calls, JSON transformation, HTML generation), which is Python's strongest domain.
- Python's standard library includes `urllib`, `json`, and `html` modules sufficient for a skeleton implementation with zero external dependencies.
- The existing CI template (`ci-minimal.yml`) already includes Python lint checks via `ruff`.
- Python is used elsewhere in the organvm system (ORGAN-IV orchestration scripts: `organ-audit.py`, `validate-deps.py`, `calculate-metrics.py`), maintaining language consistency.

**Alternatives considered:**
- **TypeScript/Node.js**: Strong ecosystem for API clients and HTML generation, but adds Node.js as a runtime dependency in CI. Python is lighter for data-focused pipelines.
- **Go**: Excellent for CLI tools but overly verbose for JSON manipulation and HTML templating. Compilation step adds CI complexity.
- **Shell scripts**: Sufficient for simple API calls (`curl` + `jq`) but unmaintainable for aggregation logic and HTML generation at scale.

### GoatCounter as the Analytics Platform

[GoatCounter](https://www.goatcounter.com/) is selected as the sole web analytics platform for the public-process site.

**Rationale:**
- **No cookies**: GoatCounter operates entirely without cookies. This eliminates cookie consent requirements and aligns with the system's privacy-first values.
- **No personal data**: No IP addresses stored, no browser fingerprinting, no cross-site tracking. Geographic data is country-level only and derived from request headers.
- **GDPR-compliant by default**: Because no personal data is collected, GDPR compliance is achieved through architectural design rather than legal process.
- **Open source**: GoatCounter is [fully open source](https://github.com/arp242/goatcounter) under the EUPL license, allowing audit, self-hosting, and forking.
- **Free tier**: GoatCounter offers a free hosted tier for non-commercial sites, requiring no credit card or payment information.
- **Simple API**: GoatCounter exposes a clean REST API (v1) with JSON responses, making integration straightforward from Python.

**Alternatives considered:**
- **Google Analytics (GA4)**: Rejected. Cookie-based tracking, complex consent management, data shared with Google's advertising network. Fundamentally incompatible with privacy-first principles. Also overly complex for a Jekyll blog with modest traffic.
- **Plausible Analytics**: Strong privacy-first alternative with a clean API. However, Plausible is paid-only (no free tier for hosted service). Self-hosting requires Docker infrastructure. Cost and complexity not justified at skeleton stage.
- **Fathom Analytics**: Similar ethical stance to Plausible, but also paid-only. No free tier available. Rejected on cost grounds.
- **Self-hosted Matomo**: Full-featured, open-source analytics. However, requires a MySQL/MariaDB database, PHP runtime, and ongoing server maintenance. Operationally disproportionate for a single Jekyll site's analytics needs.
- **No analytics**: Seriously considered. The argument for zero measurement has merit. But building in public requires some signal about whether the public interface is functioning. GoatCounter represents the minimum viable measurement.

### JSON as the Data Interchange Format

All intermediate and output artifacts use JSON as their data format.

**Rationale:**
- JSON is natively supported by Python's standard library (`json` module).
- GoatCounter's API returns JSON, eliminating format conversion at the collection stage.
- GitHub Actions and downstream consumers (ORGAN-IV orchestration) already parse JSON.
- JSON is human-readable and version-control friendly (meaningful diffs in git).

**Alternatives considered:**
- **CSV**: Simpler for tabular data but loses hierarchical structure needed for nested metrics. Poor support for schema evolution.
- **SQLite**: Better for querying historical data, but adds a binary file to version control and requires SQL knowledge for downstream consumers.
- **YAML**: More human-readable than JSON for configuration, but slower to parse and less standardized for data interchange.

### GitHub Pages for Dashboard Hosting

Static HTML dashboards are designed for GitHub Pages hosting alongside the public-process Jekyll site.

**Rationale:**
- GitHub Pages is already in use for the public-process site, so no additional hosting infrastructure is needed.
- Static HTML dashboards require no server-side runtime, no database, and no build pipeline beyond the Python generator.
- Dashboards are version-controlled alongside their source data, enabling historical review.

**Alternatives considered:**
- **Standalone hosting (Netlify, Vercel)**: Adds a deployment target and potential costs. Not justified when GitHub Pages is already available.
- **Embedded in README**: GitHub renders markdown but strips most HTML/SVG. Insufficient for charts and interactive elements.
- **Third-party dashboard tools (Grafana, Metabase)**: Full-featured but require server infrastructure. Disproportionate for weekly metrics from a single data source.

## Consequences

- The pipeline is Python-only, which simplifies CI but limits contributions from developers unfamiliar with Python.
- GoatCounter's free tier may have rate limits or feature restrictions that require monitoring as traffic grows.
- JSON file-based storage works at current scale but may need migration to a database if historical data grows beyond manageable file sizes.
- Static HTML dashboards cannot support real-time updates; they refresh only when the weekly pipeline runs.
- All architectural decisions favor simplicity and zero cost at the expense of scalability. This is appropriate for skeleton stage and should be revisited if the system's audience grows significantly.
