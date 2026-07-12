# Milestone 3 — Investigation history workflows

This slice connects the verified SQLite persistence foundation to the analysis API.

## Persisted workflow

Every successful manual or CSV Conditional Access analysis now:

1. stores or updates the investigation snapshot;
2. marks the investigation as analyzed;
3. appends a new immutable analysis run;
4. records the ruleset version, normalized facts, findings, JSON report, and Markdown report;
5. returns the assigned sequential run number.

Re-running an existing investigation creates a new run instead of overwriting the earlier result.

## History API

- `GET /api/investigations` lists active investigations;
- `GET /api/investigations?include_archived=true` includes archived records;
- `GET /api/investigations/{id}` loads investigation metadata;
- `GET /api/investigations/{id}/runs` lists immutable analysis runs;
- `GET /api/investigations/{id}/runs/{run}/report.json` exports the stored JSON report;
- `GET /api/investigations/{id}/runs/{run}/report.md` exports the stored Markdown report;
- `POST /api/investigations/{id}/archive` archives without deleting history;
- `POST /api/investigations/{id}/reopen` restores an archived investigation to active analyzed status.

## Runtime configuration

`TRACE_DB_PATH` selects the local SQLite database path. The default is `backend/trace_iam.db`.

`TRACE_EVIDENCE_RETENTION` supports:

- `full_redacted` — retain the complete redacted evidence metadata supplied to TRACE;
- `metadata_only` — retain evidence identity, kind, source, and related metadata while discarding `original_excerpt` content.

An unsupported retention value stops repository initialization with an actionable error rather than silently choosing a mode.

## Safety and limits

- database files remain local and are ignored by Git;
- archive is reversible and does not delete analysis history;
- exported reports are the immutable reports stored for the selected run;
- no Microsoft Graph or tenant connection is introduced;
- no credentials or remediation actions are stored or executed.

## Automatic proof

CI must prove:

- successful analyses create history records;
- run numbering starts at one and remains sequential;
- stored JSON and Markdown reports can be exported;
- archived investigations are hidden by default and recoverable through reopen;
- metadata-only retention removes evidence excerpts;
- previous Conditional Access browser behavior remains green on Ubuntu and Windows.
