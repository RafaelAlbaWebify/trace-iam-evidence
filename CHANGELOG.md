# Release notes

## v0.1.0 — Stable operator release

TRACE IAM Evidence provides a local-first, read-only IAM evidence workbench with three complete browser workflows, immutable local history, report exports, and cross-platform release proof.

### Operator workflows

- Conditional Access evidence review using the documented redacted CSV contract.
- Resource-assignment investigation using `RA-001` and the shared domain contracts.
- Guest/B2B lifecycle investigation with invitation, redemption, tenant restriction, and resource assignment kept as separate evidence states.
- Scenario navigation, responsive workflow panels, and readable analysis summaries.
- Investigation history, immutable runs, archive/reopen behavior, and stored JSON/Markdown exports for every scenario.

### Validation and safety

- Scenario-specific redaction and evidence guidance.
- Explicit reminders not to submit identities, tenant IDs, tokens, credentials, or unrestricted exports.
- Readable FastAPI validation errors instead of raw structured objects.
- Distinct loading, empty-history, API-connection, failure, and success states.
- Safe recommended checks and explicit non-actions preserved in every report.
- No live-tenant connection, access grant, invitation change, policy modification, or automated remediation.

### Release proof

- Backend lint, strict typing, and tests on Ubuntu and Windows.
- Frontend type checking, tests, and production builds on Ubuntu and Windows.
- Chromium acceptance proof for all three operator workflows.
- Reproducible public-safe release packs on Ubuntu and Windows.
- SHA-256 manifest for source fixtures and generated reports.
- Self-locating, Windows-tested release publication script.

## v0.1.0-rc.1 — Portfolio release candidate

TRACE IAM Evidence introduced the evidence-backed architecture, three public-safe scenarios, deterministic versioned rules, SQLite persistence, immutable analysis history, report generation, and reproducible release proof that formed the basis of the stable release.
