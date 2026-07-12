# Architecture

## Architectural style

TRACE is a local-first modular monolith.

The backend owns investigation state, evidence normalization, deterministic rule evaluation, persistence, and report generation. The frontend owns operator workflow and presentation. Domain logic must remain independent from FastAPI, React, CSV parsing, and filesystem details.

## High-level flow

```text
Operator input or supported import
  -> evidence adapter validation
  -> normalized evidence facts
  -> investigation context
  -> deterministic rule evaluation
  -> findings and uncertainty
  -> local persistence
  -> Markdown / JSON reports
```

## Proposed repository structure

```text
trace-iam-evidence/
|-- backend/
|   |-- src/trace/
|   |   |-- api/
|   |   |-- application/
|   |   |-- domain/
|   |   |-- evidence/
|   |   |-- rules/
|   |   |-- reporting/
|   |   |-- persistence/
|   |   `-- observability/
|   `-- tests/
|-- frontend/
|   |-- src/
|   |   |-- app/
|   |   |-- investigations/
|   |   |-- evidence/
|   |   |-- findings/
|   |   |-- reports/
|   |   `-- shared/
|   `-- tests/
|-- contracts/
|-- samples/
|-- scripts/
`-- docs/
```

## Module responsibilities

### Domain

Contains investigation, evidence, fact, rule result, finding, check, and non-action concepts. It imports no web framework, database implementation, UI code, or source-specific parser.

### Evidence

Contains source adapters. Each adapter validates raw input and converts it into normalized evidence facts while preserving provenance.

Initial adapters:

- `manual_structured`
- `entra_signin_csv`

Generic free-text evidence is deferred until structured paths are proven.

### Rules

Contains explicit versioned deterministic rules. Primary finding selection must use declared priority and evidence strength, never source-code ordering.

### Application

Coordinates use cases:

- create investigation;
- add evidence;
- validate evidence;
- normalize evidence;
- analyze investigation;
- review finding;
- generate report;
- list and load investigations;
- archive investigation.

### Persistence

Stores investigations, evidence references, normalized facts, and analysis runs locally. SQLite is the expected first implementation. Raw unredacted evidence must not be retained by default.

### Reporting

Generates Markdown and JSON from stable report contracts. Reports must be reproducible from persisted investigation and analysis data.

### API

Maps HTTP requests to application use cases. Route handlers must not contain rule logic, parser logic, or direct filesystem orchestration.

### Frontend

Implements the investigation workflow. It must show normalized evidence before findings and make uncertainty visible.

## Core domain concepts

### Investigation

A single access-support case with a scenario type, affected subject and resource, evidence items, analysis runs, status, and operator notes.

Lifecycle:

```text
draft -> evidence_validated -> analyzed -> reviewed -> exported -> archived
```

### Evidence item

One supplied piece of evidence with source, provenance, redaction state, original redacted excerpt where retained, structured payload, and validation state.

### Evidence fact

A normalized assertion linked to its source evidence. Examples include:

- authentication succeeded;
- Conditional Access evaluation failed;
- MFA was required;
- resource assignment was missing;
- guest invitation remained pending.

### Rule

A versioned deterministic evaluator with declared scenario, required facts, supporting facts, contradicting facts, priority, and finding construction.

### Finding

A rule-backed conclusion containing supporting evidence, contradicting evidence, missing evidence, confidence basis, limitations, safe checks, and non-actions.

## Error handling

Errors are classified as:

- input validation error;
- unsupported evidence format;
- normalization error;
- analysis precondition failure;
- persistence failure;
- report generation failure;
- internal unexpected error.

User-facing errors must be actionable and must not expose sensitive evidence or stack traces.

## Observability

Initial observability is local structured logging with correlation identifiers for investigation and analysis runs. Logs must avoid raw sensitive evidence by default.

## Test strategy

- domain unit tests for lifecycle and invariants;
- adapter contract tests for validation and normalization;
- rule tests for positive, negative, contradictory, and insufficient-evidence cases;
- repository tests for SQLite persistence and migrations;
- API integration tests;
- frontend component tests;
- end-to-end tests for the complete sample investigation workflow;
- generated report snapshot or schema tests where stable.

## Safety constraints

- read-only operation;
- no credentials;
- no tenant-wide scan;
- no external writes;
- no automatic remediation;
- redacted or public-safe evidence only;
- no confidence claim without explicit evidence basis;
- no production change recommendation where only a verification check is justified.
