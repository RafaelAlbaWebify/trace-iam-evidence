# Release notes

## v0.2.0 — 2026-07-15

### Investigation workbench

- Persisted case creation, metadata, lifecycle and generated case identifiers.
- Evidence inventory with provenance, reliability, validation and immutable run snapshots.
- Structured findings with evidence basis, confidence, limitations, safe checks and non-actions.
- Append-only investigation timeline, report-export audit and operator notes.
- Immutable analysis-run comparison and JSON comparison export.
- Operational search, workload dashboard and deterministic latest-activity ordering.

### Local product packaging

- Self-locating Windows runtime manager with start, status, diagnostics and stop actions.
- Configurable runtime data directory separated from the repository.
- Backend/frontend process management, health verification, state metadata and retained logs.
- Verified SQLite online backup, integrity checking and guarded restore.
- Full Windows lifecycle acceptance executed from outside the repository.
- Timestamped public-safe review ZIP generated directly in Downloads without opening the folder.
- Portable review source/version metadata, package diagnostics, scenario/release evidence inventory, review instructions and SHA-256 manifest.
- Explicit exclusion of credentials, private evidence, runtime state, databases, logs, backups, dependency directories, virtual environments and build output.
- Repeatability proof for replacing an explicitly named review ZIP at the same destination.

### Verification

- Backend lint, strict typing and tests on Ubuntu and Windows.
- Frontend type checking, tests and builds on Ubuntu and Windows.
- Chromium acceptance for supported investigation workflows.
- Ubuntu and Windows release-proof packs.
- Windows runtime lifecycle and portable review safety/integrity acceptance.

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
