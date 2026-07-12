# TRACE Domain Contracts

Milestone 1 defines the framework-independent vocabulary used by later evidence adapters, rules, persistence, API, and UI layers.

## Core boundaries

- `Investigation` represents one IAM troubleshooting case.
- `EvidenceItem` records the source and provenance of supplied evidence.
- `EvidenceFact` is a normalized assertion derived from an evidence item.
- `AnalysisContext` provides a read-only investigation and fact set to rules.
- `Rule` evaluates normalized evidence without external writes.
- `RuleResult` either contains one supported finding or records no match.
- `Finding` references supporting, contradicting, and missing fact types.
- `RecommendedCheck` is a verification action, not remediation.
- `NonAction` records an action that is not justified by current evidence.

## Safety properties

The domain layer:

- has no FastAPI imports;
- has no database imports;
- performs no network or filesystem writes;
- does not store credentials;
- does not connect to a Microsoft tenant;
- does not execute remediation;
- preserves evidence provenance through `source_evidence_id`.

## Current scenario identifiers

- `conditional_access`
- `resource_assignment`
- `guest_b2b`

Only Conditional Access belongs to the first vertical slice. The additional identifiers prevent naming drift; they do not mean those scenarios are implemented.

## Proof

Milestone 1 is accepted only when CI proves on Ubuntu and Windows that:

- invalid blank identifiers are rejected;
- facts preserve their evidence source;
- fact filtering is deterministic;
- matched rules cannot exist without a finding;
- linting, strict type checking, and all tests pass.
