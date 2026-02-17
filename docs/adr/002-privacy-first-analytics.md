# ADR 002: Privacy-First Analytics Strategy

## Status

Accepted

## Date

2026-02-17

## Context

The organvm eight-organ system publishes a public-facing website ([public-process](https://github.com/organvm-v-logos/public-process)) containing meta-system essays, architectural reflections, and creative philosophy. Measuring audience engagement is necessary to validate that the "building in public" mission is reaching readers, to inform editorial decisions, and to provide system-health signals to ORGAN-IV's orchestration layer.

However, the organvm system is built on explicit values of transparency, autonomy, and creative sovereignty. The analytics strategy must be consistent with these values. A system that advocates for individual agency while secretly profiling its visitors would be hypocritical at the infrastructure level.

This ADR documents the decision to adopt a strict privacy-first analytics policy and the specific constraints that follow from it.

### The Problem with Conventional Analytics

Modern web analytics, as popularized by Google Analytics and its derivatives, operates on a surveillance model:

1. **Cookies**: Persistent identifiers placed in the visitor's browser to track them across sessions and, in some implementations, across sites.
2. **Fingerprinting**: Techniques that combine browser version, screen resolution, installed fonts, and other signals to create a unique identifier without explicit cookies.
3. **Third-party data sharing**: Analytics data sent to platforms that aggregate it across millions of sites, building behavioral profiles that feed advertising networks.
4. **IP logging**: Full IP addresses stored in server logs, enabling geographic tracking to city level and potential re-identification.

These practices create legal obligations (GDPR consent requirements, CCPA opt-out mechanisms, cookie banner mandates) and ethical concerns (visitor profiling without meaningful consent, data broker ecosystems, chilling effects on browsing behavior).

For a project about creative autonomy and institutional transparency, adopting surveillance analytics would undermine the message at the medium level.

## Decision

analytics-engine adopts a **strict privacy-first analytics policy** with the following non-negotiable constraints:

### 1. No Cookies

The analytics system must not set, read, or depend on any cookies -- first-party or third-party. This means:

- No session cookies for visitor identification
- No persistent cookies for cross-session tracking
- No cookie consent banners required (because there are no cookies to consent to)
- Returning visitors cannot be distinguished from new visitors at the individual level (aggregate patterns only)

### 2. No Personal Data Collection

The analytics system must not collect, store, or process any data that could identify an individual visitor. Specifically:

- **No IP addresses**: Not stored in logs, not used for fingerprinting, not retained in any form
- **No browser fingerprinting**: No combination of User-Agent, screen resolution, fonts, or other browser properties used to create unique identifiers
- **No user accounts or login tracking**: Analytics are purely anonymous and aggregate
- **No form data capture**: No collection of search queries, form inputs, or typed content

### 3. Geographic Data: Country Level Only

Country-level geographic approximation is permitted (derived from request headers at collection time, not stored alongside individual page views). City-level, region-level, or coordinate-based location data is prohibited.

### 4. GDPR Compliance by Architecture

Rather than achieving GDPR compliance through legal mechanisms (privacy policies, consent flows, data processing agreements), the system achieves compliance through architectural absence: if no personal data is collected, there is no data to protect, no data subject access requests to fulfill, and no data breaches to report.

This is not a loophole -- it is the most robust form of compliance. Legal mechanisms can fail (consent forms can be poorly worded, data processing agreements can be violated). Architectural absence cannot.

### 5. Open-Source Analytics Platform

The analytics platform must be open source, enabling:

- Full code audit of what data is collected and how it is processed
- Self-hosting option if the hosted service changes its policies
- Community oversight of privacy practices
- Fork capability as an exit strategy

### Implementation: GoatCounter

[GoatCounter](https://www.goatcounter.com/) is selected as the analytics platform because it satisfies all five constraints above:

- **No cookies**: GoatCounter's tracking script does not set any cookies. It uses a lightweight image-based counter or a minimal JavaScript snippet that sends a single pageview event.
- **No personal data**: GoatCounter does not store IP addresses. The hosted service explicitly states that no personal data is collected or stored.
- **Country-level geography**: GoatCounter derives country from the request's Accept-Language header (not IP geolocation), providing aggregate geographic distribution without individual-level tracking.
- **GDPR by design**: GoatCounter's [privacy documentation](https://www.goatcounter.com/help/privacy) confirms it is designed to not require GDPR consent.
- **Open source**: GoatCounter is licensed under the EUPL and available at [github.com/arp242/goatcounter](https://github.com/arp242/goatcounter).

### Alternatives Evaluated

#### Google Analytics (GA4) -- Rejected

- Sets multiple cookies (`_ga`, `_gid`, `_gat`)
- Collects IP addresses (even with anonymization, partial IPs are still processed)
- Data shared with Google's advertising ecosystem
- Requires cookie consent banners in EU jurisdictions
- Complex setup with data streams, measurement IDs, and property configuration
- **Verdict**: Fundamentally incompatible with privacy-first constraints 1, 2, and 5

#### Plausible Analytics -- Viable but Rejected on Cost

- No cookies, no personal data, GDPR-compliant by design
- Open source (AGPL), self-hosting available
- Clean API, good dashboard
- **However**: Hosted service starts at $9/month. Self-hosting requires Docker infrastructure.
- **Verdict**: Meets all privacy constraints. Rejected at skeleton stage due to cost. May be reconsidered if analytics-engine scales beyond GoatCounter's capabilities.

#### Fathom Analytics -- Viable but Rejected on Cost

- No cookies, privacy-first design
- GDPR, CCPA, and PECR compliant
- Simple, focused dashboard
- **However**: Paid-only, starting at $14/month. No free tier. Not open source.
- **Verdict**: Meets privacy constraints 1-4 but fails constraint 5 (open source). Rejected on cost and licensing.

#### Self-Hosted Matomo -- Rejected on Complexity

- Open source (GPL), full self-hosting control
- Can be configured for privacy-first operation (disable cookies, anonymize IPs)
- **However**: Requires PHP runtime, MySQL/MariaDB database, web server, and ongoing maintenance. Default configuration includes cookies and IP logging; privacy-first mode must be manually enabled.
- **Verdict**: Can meet privacy constraints with significant configuration effort. Rejected due to operational complexity disproportionate to needs.

#### Server Log Analysis (AWStats, GoAccess) -- Rejected on Data Model

- No JavaScript, no cookies, uses existing server logs
- **However**: Server logs inherently contain full IP addresses. GitHub Pages does not provide access to raw server logs.
- **Verdict**: Not feasible with GitHub Pages hosting. Would require alternative hosting infrastructure.

#### No Analytics -- Seriously Considered

The strongest privacy position is to collect no data at all. This was seriously considered.

**Arguments for zero measurement:**
- Eliminates all privacy risk, no matter how small
- Removes the temptation to optimize for metrics rather than substance
- Simplifies the system (one less component to maintain)

**Arguments against zero measurement:**
- Building in public requires some signal that the public interface functions
- Editorial decisions benefit from knowing which essays reach readers
- ORGAN-IV's orchestration layer needs engagement data for system health monitoring
- GoatCounter's privacy profile makes the marginal risk nearly zero

**Verdict**: The "no analytics" position is philosophically defensible but practically insufficient for the system's stated mission. GoatCounter represents the minimum viable measurement that preserves both privacy and utility.

## Consequences

### Positive

- Visitors to the public-process site are never tracked, profiled, or identified
- No cookie consent banners clutter the reading experience
- No legal risk from GDPR, CCPA, or similar privacy regulations
- The analytics infrastructure is auditable end-to-end (open-source platform, open-source pipeline, public metrics)
- The system's values are consistent from the essay layer down to the infrastructure layer

### Negative

- **No individual-level data**: Cannot track user journeys, conversion funnels, or returning visitor rates. All metrics are aggregate.
- **Limited attribution**: Referrer data is available but less detailed than cookie-based systems. Cannot attribute conversions to specific campaigns or track multi-touch attribution.
- **No real-time analytics**: GoatCounter updates are near-real-time, but the analytics-engine pipeline runs weekly. Real-time monitoring is not supported.
- **Free tier limitations**: GoatCounter's free tier may have rate limits or feature restrictions as traffic grows. Migration to a paid tier or self-hosting may eventually be necessary.

### Monitoring

This decision should be revisited if:

- GoatCounter changes its privacy policy or data collection practices
- The public-process site's traffic exceeds GoatCounter's free tier limits
- Editorial or orchestration decisions require individual-level data that aggregate metrics cannot provide (unlikely given the system's values)
- A new privacy-first analytics platform emerges that offers better features at comparable cost

## References

- [GoatCounter privacy policy](https://www.goatcounter.com/help/privacy)
- [GoatCounter source code](https://github.com/arp242/goatcounter)
- [GDPR Article 6: Lawfulness of processing](https://gdpr-info.eu/art-6-gdpr/)
- [ePrivacy Directive (Cookie Law)](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX:32002L0058)
- [ADR 001: Initial Architecture Decisions](./001-initial-architecture.md)
