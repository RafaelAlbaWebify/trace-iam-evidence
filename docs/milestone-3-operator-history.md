# Milestone 3 — Operator history workspace

The TRACE browser now exposes the persisted investigation lifecycle.

## Operator workflow

After a successful Conditional Access analysis, the browser:

- displays the assigned immutable run number;
- refreshes the local investigation history;
- shows investigation status and run count;
- lists stored analysis runs and ruleset versions;
- links to the stored JSON and Markdown reports;
- archives an investigation without deleting its history;
- optionally displays archived investigations;
- reopens an archived investigation.

## Browser proof

The Playwright acceptance test uses the real FastAPI service and SQLite database to:

1. submit the public-safe CSV fixture;
2. verify the CA-001 report and run number;
3. verify the persisted investigation and run export links;
4. archive the investigation and confirm it disappears from the active list;
5. display archived investigations and reopen it;
6. download the stored JSON and Markdown reports;
7. retain the reports, service logs, Playwright report, and full-page history screenshot as CI artifacts.

## Milestone 3 completion boundary

Together with the persistence foundation and history API slices, this completes the roadmap requirements for:

- SQLite repository and migrations;
- immutable analysis-run versioning;
- investigation history;
- load, reopen, export, and archive workflow;
- configurable evidence-retention mode;
- automatic cross-platform and browser proof.
