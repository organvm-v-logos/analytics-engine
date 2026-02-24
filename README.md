[![ORGAN-V: Logos](https://img.shields.io/badge/ORGAN--V-Logos-0d47a1?style=flat-square)](https://github.com/organvm-v-logos) [![CI](https://github.com/organvm-v-logos/analytics-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/organvm-v-logos/analytics-engine/actions/workflows/ci.yml) [![Tier: Standard](https://img.shields.io/badge/tier-standard-blue?style=flat-square)]() [![Status: Initial Implementation](https://img.shields.io/badge/status-initial_implementation-green?style=flat-square)]()

# analytics-engine

_Engagement tracking and audience analytics for the ORGAN-V discourse layer_

---

> **Status: Initial Implementation**
>
> The three-stage pipeline (collection → aggregation → visualization) is implemented
> and passing 71 tests. All three `seed.yaml` produce edges are fulfilled.
> GoatCounter and GitHub API tokens are optional — the pipeline degrades gracefully
> when unconfigured, writing `available: false` JSON and exiting 0.
> See [Current State](#current-state) below for details.

---

## Current State

As of 2026-02-24, this repository contains:

- `src/config.py` — Configuration management (env-based, dataclasses, `.configured` checks)
- `src/goatcounter.py` — GoatCounter API client (stdlib urllib only)
- `src/github_activity.py` — GitHub activity collector across all 8 ORGANVM orgs
- `src/aggregator.py` — Metric fusion, trend computation, threshold alerting
- `src/dashboard.py` — Static HTML dashboard generator (zero-JS, inline SVG)
- `config/thresholds.yaml` — Alert threshold definitions
- `tests/` — 71 offline tests (fixture-driven, mocked APIs)
- `.github/workflows/ci.yml` — Python CI (ruff + pytest, Python 3.10/3.12)
- `.github/workflows/weekly-metrics.yml` — Monday 08:00 UTC cron pipeline
- `seed.yaml` — Automation contract (`implementation_status: CANDIDATE`)

All three produce edges are now fulfilled: `engagement-metrics.json`, `system-engagement-report.json`, and `docs/dashboard/index.html`.

---

## Architecture

### Overview

analytics-engine is the measurement backbone of ORGAN-V (Logos / Public Process). It exists to answer a deceptively simple question: is anyone reading?

Building in public means nothing if the "public" part is an illusion. The ten meta-system essays published through [public-process](https://github.com/organvm-v-logos/public-process) represent thousands of words of institutional reflection, architectural rationale, and creative philosophy. But words on a page without readers are a monologue, not discourse. analytics-engine closes the feedback loop by collecting engagement signals, aggregating them into meaningful patterns, and rendering dashboards that make audience behavior legible to the system's maintainers.

The engine integrates with [GoatCounter](https://www.goatcounter.com/), a privacy-first, open-source web analytics platform that requires no cookies, collects no personal data, and complies with GDPR by default. Page view counts, referrer chains, browser distributions, and geographic approximations flow through a three-stage pipeline: **collection** (GoatCounter API client), **aggregation** (cross-source metric fusion), and **visualization** (static HTML dashboard generation). The resulting artifacts feed back into both ORGAN-V's editorial workflow and ORGAN-IV's orchestration layer, enabling data-informed decisions about what to write next, where to distribute it, and whether the system's public interface is reaching its intended audience.

This is not surveillance analytics. There are no tracking pixels, no fingerprinting scripts, no third-party data brokers. Every metric collected here could be derived from a standard web server access log. The difference is structure: analytics-engine transforms raw signals into narrative-ready insights that serve the system's reflective mission.

### Key Capabilities

- **GoatCounter API Integration**: Automated weekly collection of page views, referrers, browser stats, and visitor counts from the public-process Jekyll site
- **Multi-Source Aggregation**: Combines GoatCounter web analytics with GitHub activity data (commits, PRs, releases, stars) across all eight organs
- **Dashboard Generation**: Produces static HTML dashboards suitable for embedding in GitHub Pages or serving alongside the public-process site
- **Threshold Alerting**: Configurable engagement thresholds that trigger notifications when metrics deviate from baselines
- **System-Wide Reporting**: Generates `system-engagement-report.json` consumed by ORGAN-IV's orchestration layer for cross-organ health monitoring

## Architecture

The analytics engine follows a three-stage pipeline architecture designed for simplicity, auditability, and offline operation. Each stage is a standalone Python module that reads from and writes to well-defined JSON interfaces.

```
                          +-----------------------+
                          |   GoatCounter API     |
                          |  (goatcounter.com)    |
                          +-----------+-----------+
                                      |
                                      v
+------------------+       +----------+-----------+       +-------------------+
|  GitHub API      +------>+    aggregator.py      +------>+   dashboard.py    |
|  (all organs)    |       | (metric fusion layer) |       | (HTML generator)  |
+------------------+       +----------+-----------+       +--------+----------+
                                      |                            |
                    +-----------------+------------------+         |
                    |                                    |         |
                    v                                    v         v
        +-----------+----------+    +------------+------+-+  +----+----------+
        | engagement-metrics   |    | system-engagement   |  | Dashboard     |
        | .json                |    | -report.json        |  | (static HTML) |
        +----------------------+    +---------------------+  +---------------+
              |                              |                       |
              v                              v                       v
        public-process              orchestration-start-here   public-process
        (ORGAN-V)                   (ORGAN-IV)                 (ORGAN-V)
```

**Stage 1: Collection** (`goatcounter.py`). The GoatCounter client authenticates against the GoatCounter API using a site-specific token, then pulls page-level and aggregate metrics for a configurable time window (default: 7 days). It also queries the GitHub API for commit counts, PR activity, and release events across all organs. Raw responses are normalized into a common intermediate format and written to `data/raw/` as dated JSON files. The collection stage is fully idempotent: running it multiple times for the same time window overwrites the same output files with identical content, making retries safe in CI.

**Stage 2: Aggregation** (`aggregator.py`). The aggregator merges GoatCounter web metrics with GitHub activity data, computes derived metrics (engagement ratios, trend deltas, per-essay performance), and applies threshold checks. It outputs two JSON artifacts: `engagement-metrics.json` (detailed per-page breakdown for ORGAN-V editorial use) and `system-engagement-report.json` (organ-level summary for ORGAN-IV orchestration). The aggregator also maintains a rolling history of previous reports in `data/history/`, enabling trend computation (week-over-week deltas, rolling four-week averages) without requiring a database or external state store.

**Stage 3: Visualization** (`dashboard.py`). The dashboard generator reads aggregated metrics and produces a self-contained static HTML page with charts, tables, and trend indicators. Charts are rendered as inline SVG, eliminating any dependency on JavaScript charting libraries or CDN-hosted assets. The dashboard is designed to be served from GitHub Pages alongside the public-process Jekyll site, requiring no JavaScript frameworks or build tools beyond standard HTML. A secondary output mode generates an embeddable summary widget (a small HTML fragment) that can be included in other pages via an iframe or server-side include.

### Data Flow Principles

The pipeline is designed around three principles that govern how data moves between stages:

1. **JSON at every boundary**: Every interface between stages is a well-defined JSON file with a documented schema. There are no in-memory hand-offs, no shared databases, no message queues. This means any stage can be run independently, debugged by inspecting its input files, or replaced without affecting the others.

2. **Append-only history**: The `data/history/` directory accumulates dated snapshots of aggregated metrics. Old files are never modified or deleted by the pipeline. This creates a natural audit trail and enables retrospective analysis without any additional infrastructure.

3. **No external state**: The pipeline carries all necessary context in its file-based artifacts. It does not depend on databases, caches, or environment state beyond API credentials. A fresh clone of the repository plus valid API tokens is sufficient to run the full pipeline.

## Components

### `src/goatcounter.py` — GoatCounter API Client

The GoatCounter client handles all communication with the GoatCounter API v1. It manages authentication via API token, implements rate limiting to stay within free-tier constraints, and normalizes the API's response format into the engine's internal schema.

Key responsibilities:
- Authenticate and manage API sessions
- Fetch page view counts, unique visitor counts, referrer chains
- Pull browser and OS distribution data
- Retrieve geographic approximations (country-level only, no city/IP data)
- Handle pagination for high-traffic periods
- Normalize timestamps to UTC

The client is designed to be idempotent: running it twice for the same time window produces identical output, enabling safe retries in CI environments.

### `src/aggregator.py` — Metric Aggregation Engine

The aggregator is the analytical core of the pipeline. It consumes raw metrics from the GoatCounter client and GitHub API, then produces two distinct output artifacts optimized for different consumers.

Key responsibilities:
- Merge web analytics with GitHub activity data
- Compute per-essay engagement metrics (views, unique visitors, average time proxy)
- Calculate system-wide trends (week-over-week deltas, rolling averages)
- Apply configurable alert thresholds (e.g., traffic drops > 50%)
- Generate `engagement-metrics.json` for ORGAN-V editorial use
- Generate `system-engagement-report.json` for ORGAN-IV orchestration

The aggregator maintains a rolling history of past reports to enable trend computation without requiring a database. Historical data is stored as dated JSON files in `data/history/`.

### `src/dashboard.py` — Static Dashboard Generator

The dashboard generator transforms aggregated metrics into human-readable HTML dashboards. It produces self-contained pages that require no external dependencies, making them suitable for GitHub Pages hosting.

Key responsibilities:
- Render page view trends as inline SVG sparkline charts
- Generate referrer breakdown tables
- Display organ-level activity summaries
- Highlight threshold violations with visual indicators
- Produce both a full dashboard and an embeddable summary widget
- Output valid, accessible HTML5 with semantic markup

## Data Model

### `engagement-metrics.json`

The primary output artifact, consumed by the public-process editorial workflow. This file contains detailed per-page analytics for the ORGAN-V Jekyll site.

```json
{
  "generated_at": "2026-02-17T08:00:00Z",
  "period": {
    "start": "2026-02-10",
    "end": "2026-02-17"
  },
  "site_totals": {
    "page_views": 1247,
    "unique_visitors": 843,
    "referrer_count": 12
  },
  "pages": [
    {
      "path": "/essays/meta-system/01-orchestrate/",
      "title": "Orchestrate: Why Build a System of Systems",
      "views": 312,
      "unique_visitors": 218,
      "referrers": {
        "direct": 142,
        "mastodon.social": 48,
        "github.com": 28
      }
    }
  ],
  "trends": {
    "views_delta_pct": 12.3,
    "visitors_delta_pct": 8.7
  }
}
```

### `system-engagement-report.json`

The orchestration-facing artifact, consumed by ORGAN-IV's health monitoring workflows. This file provides organ-level summaries rather than page-level detail.

```json
{
  "generated_at": "2026-02-17T08:00:00Z",
  "period": {
    "start": "2026-02-10",
    "end": "2026-02-17"
  },
  "web_engagement": {
    "total_views": 1247,
    "total_visitors": 843,
    "top_essay": "01-orchestrate"
  },
  "github_activity": {
    "total_commits": 47,
    "total_prs": 5,
    "total_releases": 1,
    "organ_breakdown": {
      "I": { "commits": 12, "prs": 1 },
      "II": { "commits": 8, "prs": 0 },
      "III": { "commits": 15, "prs": 2 },
      "IV": { "commits": 7, "prs": 1 },
      "V": { "commits": 5, "prs": 1 }
    }
  },
  "alerts": []
}
```

## Workflow Integration

### Weekly Metrics Collection (`weekly-metrics.yml`)

The primary automation runs every Monday at 08:00 UTC via GitHub Actions cron trigger. The workflow:

1. Checks out the repository
2. Installs Python dependencies
3. Runs `goatcounter.py` to collect the previous week's web analytics
4. Runs `aggregator.py` to merge web + GitHub data and produce output artifacts
5. Runs `dashboard.py` to regenerate the static dashboard
6. Commits updated metrics and dashboard files back to the repository
7. Optionally triggers a deployment to update the live dashboard

The workflow can also be triggered manually via `workflow_dispatch` for ad-hoc metric pulls.

### Alert Thresholds

The aggregator supports configurable alert thresholds defined in `config/thresholds.yaml`:

- **Traffic drop**: Alert if weekly views decrease by more than 50% compared to the rolling 4-week average
- **Zero traffic**: Alert if any published essay receives zero views in a 7-day window
- **Referrer anomaly**: Alert if a single referrer accounts for more than 80% of traffic (potential bot activity)
- **GitHub stall**: Alert if total system commits drop below 5 in a 7-day window

When thresholds are violated, the `system-engagement-report.json` includes alert entries that ORGAN-IV's monitoring can act on.

## Privacy-First Analytics

analytics-engine uses [GoatCounter](https://www.goatcounter.com/) as its sole web analytics platform. This is a deliberate architectural choice rooted in the system's values.

**Why GoatCounter?**

The organvm system is built on principles of transparency, autonomy, and creative sovereignty. Using surveillance-grade analytics tools like Google Analytics would contradict those principles at the infrastructure level. GoatCounter aligns with the system's ethics:

- **No cookies**: GoatCounter does not set any cookies. Zero. This means no cookie consent banners, no GDPR consent flows, no dark patterns. Visitors are never tracked across sessions or sites.
- **No personal data**: No IP addresses are stored. No browser fingerprinting is performed. Geographic data is approximated at the country level from request headers and immediately discarded after aggregation.
- **GDPR-compliant by default**: Because no personal data is collected, there is no data to protect, no retention policies to enforce, and no data subject access requests to handle. Compliance is achieved through absence, not through bureaucracy.
- **Open source**: GoatCounter's source code is [publicly available](https://github.com/arp242/goatcounter). The analytics platform itself can be audited, self-hosted, or forked. This mirrors the organvm system's own commitment to building in public.
- **Free tier**: GoatCounter offers a generous free tier for non-commercial sites, which fits the public-process site's profile. No vendor lock-in, no credit card required.

**Alternatives Considered and Rejected**

- **Google Analytics**: Rejected. Cookie-based tracking, complex GDPR compliance requirements, data shared with Google's advertising ecosystem. Fundamentally incompatible with privacy-first principles.
- **Plausible Analytics**: Strong privacy-first alternative, but requires a paid subscription. GoatCounter's free tier and simpler API made it preferable for a skeleton-stage project.
- **Fathom Analytics**: Similar to Plausible — good ethics, but paid-only. Cost not justified at current scale.
- **Self-hosted Matomo**: Full-featured but operationally heavy. Requires server maintenance, database administration, and security updates. Disproportionate infrastructure for a Jekyll blog's analytics needs.
- **No analytics at all**: Considered. The argument for zero measurement has merit. But building in public requires some signal about whether the public interface is functioning. GoatCounter represents the minimum viable measurement that respects both the audience and the system's values.

## Development

### Prerequisites

- Python 3.11+
- A GoatCounter account and API token (for live data collection)
- GitHub personal access token with `repo:read` scope (for cross-organ activity data)

### Setup

```bash
# Clone the repository
git clone https://github.com/organvm-v-logos/analytics-engine.git
cd analytics-engine

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API credentials
cp config/env.example .env
# Edit .env with your GoatCounter and GitHub tokens
```

### Environment Variables

| Variable | Description | Required |
|---|---|---|
| `GOATCOUNTER_SITE` | GoatCounter site code (e.g., `organvm`) | Yes |
| `GOATCOUNTER_TOKEN` | GoatCounter API token | Yes |
| `GITHUB_TOKEN` | GitHub PAT with `repo:read` scope | Yes |
| `METRICS_HISTORY_DIR` | Path to historical metrics storage | No (default: `data/history/`) |

### Running Locally

```bash
# Collect metrics (requires API tokens)
python src/goatcounter.py --days 7 --output data/raw/

# Aggregate metrics
python src/aggregator.py --input data/raw/ --output data/

# Generate dashboard
python src/dashboard.py --input data/ --output docs/dashboard/
```

### Testing

```bash
# Run tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Lint
ruff check src/ tests/
```

## How It Fits the System

analytics-engine operates within the eight-organ creative-institutional system:

| Organ | Name | Role | Relationship |
|---|---|---|---|
| **I** | Theoria | Foundational theory & knowledge architecture | Measured by GitHub activity metrics |
| **II** | Poiesis | Creative production & artistic output | Measured by GitHub activity metrics |
| **III** | Ergon | Applied projects & commercial work | Measured by GitHub activity metrics |
| **IV** | Taxis | Orchestration & infrastructure | Receives `system-engagement-report.json` |
| **V** | **Logos** | **Public process & discourse** | **analytics-engine lives here** |
| **VI** | Koinonia | Community & collaboration | Measured by GitHub activity metrics |
| **VII** | Kerygma | Publication & outreach | Measured by GitHub activity metrics |
| **META** | meta-organvm | Umbrella governance | System-wide metrics aggregation |

Within ORGAN-V, analytics-engine relates to sibling repositories:

- **[public-process](https://github.com/organvm-v-logos/public-process)**: The Jekyll site whose engagement metrics this engine tracks. Consumes `engagement-metrics.json` and the generated dashboard.
- **[content-pipeline](https://github.com/organvm-v-logos/content-pipeline)**: The editorial workflow engine. Analytics data informs content prioritization decisions.
- **[distribution-network](https://github.com/organvm-v-logos/distribution-network)**: POSSE distribution layer. Referrer data from analytics reveals which distribution channels are effective.

## Design Philosophy

analytics-engine embodies several design principles that recur throughout the organvm system:

**Measurement without surveillance.** The fundamental tension in analytics is that measurement can easily become surveillance. analytics-engine resolves this tension by choosing tools and techniques that provide aggregate insight without individual tracking. GoatCounter tells us that 300 people read an essay last week; it does not tell us who they are, where they came from, or what they did afterward. This is sufficient for editorial decisions and system health monitoring. It is insufficient for advertising, profiling, or behavioral manipulation -- and that insufficiency is a feature, not a limitation.

**Artifacts over services.** The pipeline produces files, not live dashboards. There is no running server, no database process, no long-lived service to monitor. Files are committed to git, served from GitHub Pages, and consumed by downstream workflows. This means the entire analytics infrastructure can be understood by reading files in a repository. There is no hidden state, no configuration drift, no "it works on my machine" debugging. When something breaks, the diagnosis starts with `git log` and `git diff`.

**Proportional complexity.** A Jekyll blog with ten essays does not need Grafana, Prometheus, and a Kubernetes cluster. It needs a Python script that runs once a week and produces a JSON file. analytics-engine is deliberately minimal: three Python modules, two JSON output schemas, one HTML dashboard. As the system grows, the analytics infrastructure can grow with it, but it starts at the smallest viable scale rather than anticipating complexity that may never arrive.

**Institutional memory through data.** Every weekly metrics snapshot is preserved in `data/history/`. Over time, this accumulates into a quantitative history of the system's public presence: when readership grew, which essays resonated, which distribution channels worked, when interest waned. Combined with the qualitative reflection in the meta-system essays, this data layer creates a richer institutional memory than either approach alone.

## Contributing

Contributions are welcome. This project follows the [community guidelines](https://github.com/organvm-v-logos/.github/blob/main/CONTRIBUTING.md) established for ORGAN-V.

Before contributing:

1. Check the [open issues](https://github.com/organvm-v-logos/analytics-engine/issues) for existing work
2. For new features, open an issue first to discuss the approach
3. Follow the existing code style and test patterns
4. Ensure all tests pass before submitting a PR

### Development Principles

- **Privacy first**: Never introduce tracking that collects personal data
- **Simplicity**: Prefer standard library solutions over heavy dependencies
- **Auditability**: Every metric should be traceable to its source
- **Offline-capable**: The aggregator and dashboard generator should work with cached data

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) for details.

---

<sub>analytics-engine — ORGAN V: Logos — part of the eight-organ creative-institutional system — [@4444j99](https://github.com/4444j99) — LOGOS Sprint 2026-02-17</sub>
