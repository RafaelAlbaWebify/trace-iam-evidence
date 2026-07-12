# Milestone 3 — Persistence foundation

This slice establishes the local SQLite persistence boundary for TRACE.

## Stored data

- reconstructable investigation snapshots;
- evidence metadata contained in the investigation snapshot;
- append-only analysis runs;
- ruleset version per run;
- normalized facts used by the run;
- findings and generated JSON/Markdown reports.

## Invariants

- schema changes are applied through Alembic migrations;
- an analysis run receives the next sequential number for its investigation;
- existing analysis runs are never updated by the repository;
- reports can be loaded again without recalculation;
- persistence remains local and does not connect to Microsoft Graph or a tenant.

## Deliberate limits

This slice does not yet expose persistence through the API or UI. Investigation listing, reopen, export, archive, and retention modes will build on this verified repository contract.

## Automatic proof

CI proves that:

- migration `0001` upgrades an empty SQLite database;
- investigation and evidence metadata round-trip without loss;
- multiple analysis runs remain separately addressable and ordered;
- stored findings, facts, and reports reload unchanged;
- Linux and Windows quality gates remain green.
