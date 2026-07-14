# Milestone 9.3 — Immutable evidence snapshots

Each analysis run must preserve the exact redacted evidence set that supported it.

## Invariants

- A populated live case inventory is never replaced by temporary scenario-form evidence during analysis.
- Existing case evidence must be fully validated before it can support a run.
- Legacy scenario workflows without a prebuilt inventory remain supported; their generated redacted evidence is validated at run creation and captured once.
- Every stored JSON report contains an `evidence_snapshot` array.
- Every stored Markdown report contains an `Evidence snapshot` section.
- Snapshot items preserve evidence ID, kind, source, capture timestamp, subject, resource, excerpt according to retention mode, reliability, notes and validation timestamp.
- Later live-case evidence changes cannot mutate earlier run snapshots.
- Existing runs created before Milestone 9.3 remain readable and expose an empty snapshot rather than failing.

The snapshot is embedded inside the existing immutable report payload. This avoids a database migration while preserving append-only run records and backward compatibility.
