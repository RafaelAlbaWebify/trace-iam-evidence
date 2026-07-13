# Release notes

## v0.1.0-rc.1 — Portfolio release candidate

TRACE IAM Evidence now provides an evidence-backed, local-first IAM investigation portfolio release.

### Included scenarios

- Conditional Access evidence review with manual and documented redacted CSV input.
- Resource-assignment investigation using the shared domain and rule contracts.
- Guest/B2B lifecycle investigation with distinct invitation, redemption, tenant-restriction, and assignment evidence.

### Investigation workflow

- deterministic versioned rules;
- supporting, contradicting, and missing evidence;
- safe recommended checks and explicit non-actions;
- Markdown and JSON reports;
- local SQLite persistence and Alembic migrations;
- immutable analysis-run history;
- load, export, archive, and reopen workflow;
- configurable redacted-evidence retention.

### Release proof

- reproducible three-scenario release-pack builder;
- SHA-256 manifest for source fixtures and generated reports;
- Linux and Windows release-candidate jobs;
- backend lint, strict typing, and tests;
- frontend type checking, tests, and production build;
- Chromium browser acceptance proof with reports, logs, and screenshot artifacts.

### Safety boundary

This release contains no tenant connection, credential storage, automated remediation, access grants, policy changes, or external writes.
