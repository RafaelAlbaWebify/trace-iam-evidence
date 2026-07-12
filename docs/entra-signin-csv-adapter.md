# Entra Sign-in CSV Adapter

This adapter accepts a deliberately narrow, redacted CSV contract for Conditional Access evidence.

## Required headers

- `Sign-in ID`
- `Conditional Access Status`
- `Failure Reason`
- `Conditional Access Policy`

Supported status values are exactly:

- `failure`
- `success`
- `notApplied`

The adapter rejects missing or duplicate headers, blank sign-in identifiers, unsupported status values, empty files, and files with no data rows. It does not silently map unknown Microsoft export variants because doing so would weaken evidence integrity.

## Normalized facts

Depending on each row, the adapter can emit:

- `conditional_access_failed`
- `conditional_access_succeeded`
- `conditional_access_policy_name`
- `conditional_access_failure_reason`

Every normalized fact references a row-level `EvidenceItem` through `source_evidence_id`.

## Safety boundary

The input must already be redacted before it reaches TRACE. This adapter:

- performs no tenant or Microsoft Graph access;
- writes no external data;
- stores no credentials;
- does not alter Conditional Access;
- does not guess unsupported column names or status values.

A public-safe example is available at `samples/entra-signin-conditional-access-redacted.csv`.
