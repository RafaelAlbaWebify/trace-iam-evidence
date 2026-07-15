# TRACE GUI refurbishment implementation plan

Implementation follows `docs/gui-refurbishment-audit.md`.

## Milestone G1 — Design foundation

Deliverables:

- shared CSS tokens for neutral, accent, semantic, spacing, radius and elevation;
- global typography and focus defaults;
- reusable shell, page-header, surface, metric-strip and state patterns;
- responsive sidebar/drawer structure;
- no workflow or backend changes.

Acceptance:

- existing frontend tests and build pass;
- all current anchor targets remain reachable;
- no unsupported controls or metrics are introduced;
- existing browser workflow remains green.

## Milestone G2 — Operational dashboard pilot

Deliverables:

- dashboard rendered inside the new shell;
- real workload metrics only;
- compact filter toolbar;
- case records changed from cards to a semantic table at wide widths;
- intentional narrow layout and horizontal-overflow handling;
- deterministic desktop and narrow screenshots.

Acceptance:

- all existing dashboard filters preserve their API contract;
- opening an investigation still activates the exact case;
- loading, empty, error and populated states are verified;
- keyboard, focus, 200% zoom and long-data behaviour are reviewed;
- pilot direction is approved before broad migration.

## Milestone G3 — Case and evidence workflow

Deliverables:

- focused case intake;
- persistent active-case context;
- metadata and lifecycle controls;
- dense evidence inventory and detail composition;
- consistent validation, reliability and immutable-state semantics.

## Milestone G4 — Analysis and findings

Deliverables:

- scenario-aware analysis workspace;
- structured findings list/detail composition;
- explicit supporting, contradicting and missing evidence;
- limitations, safe checks and non-actions kept first-class;
- report inspection and exports preserved.

## Milestone G5 — Timeline, comparison and history

Deliverables:

- dense append-only timeline;
- clear system-event versus operator-note treatment;
- run comparison and export workspace;
- history consolidation only where semantics remain unchanged.

## Milestone G6 — Accessibility, responsiveness and release proof

Deliverables:

- browser-console evidence;
- automated accessibility scan where practical;
- keyboard and focus validation;
- desktop, narrow and 200% zoom proof;
- long-data and state fixtures;
- before/after screenshots;
- complete CI, Windows runtime, Chromium and release proof;
- review ZIP and rollback instructions.

## Branch sequence

- `gui/design-foundation`
- `gui/operational-dashboard-pilot`
- `gui/case-evidence-workflow`
- `gui/analysis-findings-workflow`
- `gui/timeline-comparison-history`
- `gui/accessibility-final-proof`

Each branch is based on the latest verified `main` and remains focused. `v0.2.0` is the stable rollback point.