# Roadmap

## Development rule

No feature is considered complete because code exists. Each milestone must define and pass automatic proof before local manual review.

## Milestone 0 — Foundation

Goal: establish product boundaries, architecture, contracts, quality gates, and CI.

Deliverables:

- product scope;
- architecture;
- contribution and development rules;
- backend and frontend skeletons;
- locked or reproducible dependencies;
- Linux and Windows CI where useful;
- test, lint, type-check, and build commands;
- generated CI proof artifact.

Exit proof:

- clean installation in CI;
- backend health test passes;
- frontend smoke test and production build pass;
- all quality checks run from documented commands;
- no manual PowerShell step required.

## Milestone 1 — Domain contracts

Goal: define stable investigation and evidence concepts before feature growth.

Deliverables:

- Investigation;
- EvidenceItem;
- EvidenceFact;
- RuleResult;
- Finding;
- RecommendedCheck;
- NonAction;
- report contract;
- lifecycle and invariant tests.

Exit proof:

- domain tests cover valid and invalid state transitions;
- findings require rule identity, evidence references, confidence basis, and limitations;
- no domain module imports FastAPI, SQLAlchemy, or source-specific parsers.

## Milestone 2 — Conditional Access vertical slice

Goal: complete one useful input-to-report workflow.

Deliverables:

- structured manual evidence adapter;
- documented redacted Entra sign-in CSV adapter;
- Conditional Access evidence facts;
- deterministic versioned rules;
- supporting, contradicting, and missing evidence;
- safe next checks and non-actions;
- Markdown and JSON report generation;
- API and minimal operator UI.

Exit proof:

- positive Conditional Access fixture triggers the expected finding;
- successful evaluation fixture does not trigger a block finding;
- contradictory evidence lowers confidence;
- malformed input produces actionable validation errors;
- full workflow passes in browser automation;
- CI uploads reports, logs, and screenshots as artifacts.

## Milestone 3 — Local persistence and history

Goal: make investigations reproducible and reviewable.

Deliverables:

- SQLite repository;
- migrations;
- analysis-run versioning;
- investigation history;
- load, reopen, export, and archive workflow;
- configurable evidence-retention mode.

Exit proof:

- migrations work against an empty database;
- investigations round-trip without loss;
- analysis history remains immutable;
- reports can be regenerated from persisted data.

## Milestone 4 — Entitlement and resource assignment

Goal: prove the architecture supports a second scenario without bypasses or synthetic log generation.

Exit proof:

- resource-assignment rules use the same domain contracts and rule interface;
- scenario-specific code remains in its adapter and rule modules;
- the Conditional Access workflow remains green.

## Milestone 5 — Guest and B2B lifecycle

Goal: support external-user evidence while preserving explicit uncertainty and safety boundaries.

Exit proof:

- invitation, redemption, tenant restriction, and resource-assignment evidence remain distinct;
- no recommendation weakens cross-tenant controls without evidence and approval boundaries.

## Milestone 6 — Portfolio release

Goal: create an evidence-backed release rather than a documentation-only claim.

Deliverables:

- reproducible release workflow;
- architecture diagram;
- public-safe scenario pack;
- generated sample reports;
- CI screenshots and proof artifact;
- setup and demo documentation;
- known limitations;
- release notes.

Exit proof:

- tagged commit passes all required checks;
- release proof can be downloaded from GitHub Actions;
- one controlled Windows release-candidate review is completed;
- README claims match verified behaviour.
