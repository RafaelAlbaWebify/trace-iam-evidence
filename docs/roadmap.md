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

## Current status

Milestones 0–6 and Post-release Milestones 7.1–7.2 are complete. Release candidate `v0.1.0-rc.1` is published. Post-release Milestone 7.3 is in progress.

## Post-release Milestone 7 — Operator workflow parity

Goal: expose every supported scenario through the same local operator experience, persistence model, report exports, and browser proof.

### 7.1 Resource-assignment operator workflow — complete

Deliverables:

- redacted resource-assignment form;
- persisted `RA-001` analysis through the API;
- investigation history and report exports;
- scenario identity visible in history;
- browser proof preserving the Conditional Access workflow.

Exit proof:

- missing assignment evidence produces the expected `RA-001` finding in the browser;
- the investigation is persisted with `RA-001@1.0.0` history;
- JSON and Markdown reports export successfully;
- Conditional Access browser proof remains green.

### 7.2 Guest/B2B operator workflow — complete

Deliverables:

- invitation, redemption, tenant restriction, and resource-assignment inputs remain distinct;
- persisted guest/B2B analysis and report export;
- browser proof for safe non-actions.

Exit proof:

- an unredeemed invitation produces the expected `GB-001` finding in the browser;
- the investigation is persisted with the complete Guest/B2B ruleset version;
- JSON and Markdown reports export successfully;
- Conditional Access and resource-assignment browser proof remain green.

### 7.3 Operator usability and release polish — in progress

#### 7.3.1 Scenario navigation and result presentation

Deliverables:

- compact navigation to every supported workflow and history;
- visually distinct scenario panels without changing backend contracts;
- accessible analysis summary for run, finding count, and evaluated rules;
- preserved detailed evidence report and safe non-actions;
- responsive operator layout and refreshed browser screenshots.

Exit proof:

- all scenario navigation targets are keyboard-accessible;
- all three browser workflows retain persistence and report exports;
- result summary and detailed evidence report are both visible in browser proof;
- Ubuntu, Windows, release-publisher, and release-pack gates remain green.

#### 7.3.2 Validation guidance and release preparation

Deliverables:

- scenario-specific validation guidance and clearer API errors;
- improved loading, empty-history, and failure states;
- refreshed README, demo guide, screenshots, and release notes;
- stable `v0.1.0` release after controlled review.
