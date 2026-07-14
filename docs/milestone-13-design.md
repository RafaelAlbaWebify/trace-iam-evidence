# Milestone 13 — Search and operational dashboard

TRACE exposes operational workload state without vanity analytics.

## Search contract

Operators can search persisted investigations by:

- generated investigation ID;
- title;
- redacted external reference;
- redacted case summary.

Filters cover status, scenario, priority, and archived state. Results are ordered by the latest immutable timeline activity, falling back to case creation time only when no timeline event exists.

## Workload definitions

- **Active**: every non-archived investigation.
- **Waiting for evidence**: active cases in `draft`.
- **Ready for analysis**: active cases in `evidence_validated`.
- **Under review**: active cases in `analyzed` or `reviewed`.
- **Critical active**: non-archived investigations with critical priority.
- **Archived**: investigations in the archived state.

These are direct persisted-state counts. TRACE does not infer team performance, SLA compliance, productivity, ownership, or unsupported risk scores.

## Identity and navigation

Dashboard results open investigations by generated case ID, never by title. Opening a result loads its persisted metadata, evidence inventory, immutable timeline, analysis runs, and comparison workspace through the existing active-case workflow.
