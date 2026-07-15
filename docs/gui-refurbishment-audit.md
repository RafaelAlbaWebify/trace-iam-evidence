# TRACE GUI refurbishment audit

## Control and baseline

This audit follows the uploaded `UNIVERSAL_GUI_REFURBISHMENT_PROMPT.md`.

- Repository: `RafaelAlbaWebify/trace-iam-evidence`
- Default branch: `main`
- Refurbishment baseline before this audit document: `589f834048dce1d1bb4aad268949c45e0a156060`
- Stable rollback point: `v0.2.0`
- Frontend: React 19, TypeScript 5.8, Vite 6
- Backend: FastAPI, SQLAlchemy, Alembic, SQLite
- Browser proof: Playwright/Chromium
- Supported Windows launch: self-locating `scripts/trace.ps1`

The uploaded reference manifest lists nine images, but the supplied ZIP contains no `reference/images/` directory. The visual comparison therefore uses the written reference themes and the approved TRACE concept mock. Missing images are recorded as a constraint and are not reconstructed from assumptions.

## Verified product purpose

TRACE IAM Evidence is a local-first, read-only IAM and access-support investigation workbench. It creates persisted cases, records redacted evidence and provenance, evaluates deterministic versioned rules, exposes uncertainty and limitations, produces JSON and Markdown reports, and preserves immutable local history.

Supported browser workflows:

1. Conditional Access review from redacted sign-in CSV evidence.
2. Resource-assignment investigation for a missing subject-to-resource assignment.
3. Guest/B2B lifecycle investigation separating invitation, redemption, tenant restriction and resource assignment.

## Intended user and operator goals

The primary user is an IAM, application-support or technical-support operator performing evidence-backed investigation rather than direct administration.

Primary goals:

- create and triage an investigation;
- preserve redacted case metadata;
- collect and validate evidence with provenance and reliability;
- run the correct deterministic scenario analysis;
- review supporting, contradicting and missing evidence;
- retain uncertainty, limitations, safe checks and non-actions;
- compare immutable runs;
- inspect the append-only timeline;
- search, archive, reopen and export cases.

## Safety and truth boundaries

The GUI must continue to communicate and enforce:

- local-first operation;
- redacted/public-safe evidence only;
- no credential storage;
- no Microsoft Graph or tenant-wide scan;
- no automatic access, identity, invitation, policy, licensing or remediation changes;
- no recommendation to weaken Conditional Access or cross-tenant controls;
- no root-cause claim without sufficient supporting evidence;
- visible rule identity, evidence basis, limitations and uncertainty.

The refurbishment must not imply assignment, remediation, approval, policy editing, live monitoring or collaboration features that do not exist.

## Current architecture and interface model

The frontend is one React application without a routing library. `App.tsx` owns active-case state, case lifecycle, scenario forms and analysis execution. Specialist components cover the operational dashboard, evidence, findings, run comparison and timeline.

Current navigation is a grid of anchor links into one long page:

- Dashboard
- New case
- Active case
- Evidence
- Conditional Access
- Resource assignment
- Guest/B2B
- Findings
- History

The verified browser screenshot shows all workspaces rendered vertically. This preserves reachability but produces very long scroll distance, weak location awareness and repeated context.

## Surface and state inventory

| Surface | Purpose | Important states | Classification |
|---|---|---|---|
| Operational dashboard | Search, workload counts, filters, case opening | loading, empty, filtered, populated, API error | Pilot; restructure visually |
| Case intake | Create persisted case | default, validation error, submitting, success | Restyle/focus |
| Active-case control | Metadata and lifecycle | no active case, editable, archived, transition error | Persistent context |
| Evidence workspace | Inventory, create, preview, validate, delete | empty, partial, validated, immutable, archived, error | Priority migration |
| Timeline | System events and notes | loading, empty, populated, archived restriction | Dense record view |
| Run comparison | Compare immutable runs | insufficient runs, selectable, result, export | Clarify hierarchy |
| Scenario forms | Execute supported analysis | unavailable, editable, loading, error, success | Group by active scenario |
| Findings | Evidence-backed findings and exports | empty, populated, filters, raw views | Split list/detail |
| History | Cases, runs, archive/reopen, exports | loading, empty, populated, archived included | Consolidate carefully |

## Baseline execution evidence

Latest verified evidence was recovered from CI run `#173` and Release proof run `#119`.

Passing gates:

- backend lint, strict typing and tests on Ubuntu and Windows;
- frontend type checking, tests and production build on Ubuntu and Windows;
- Windows runtime lifecycle proof;
- portable-review safety/integrity/repeatability proof;
- Chromium browser acceptance;
- Ubuntu and Windows release proof.

The browser artifact includes dashboard/history screenshots, dashboard/timeline/comparison/report JSON, frontend/backend logs and a Playwright report. Runtime logs show clean Vite and Uvicorn startup and successful Alembic migrations. A dedicated browser-console export and automated accessibility report are not currently retained and must be added during refurbishment QA.

## Existing identity worth preserving

- TRACE blue accent;
- neutral background;
- explicit redaction warning;
- visible lifecycle, priority and evidence states;
- readable raw JSON/Markdown inspection;
- precise operator terminology.

## Verified visual debt

1. One-page anchor architecture creates excessive scroll and weak orientation.
2. Navigation behaves like a card catalogue rather than an operations shell.
3. The oversized hero consumes prime workspace area.
4. Repeated rounded cards and gradients give unrelated surfaces equal weight.
5. Raw colours, radii, spacing and shadows are embedded across CSS files.
6. Case records are card lists instead of a compact operational table.
7. Separate workspaces have limited shared primitives.
8. Status, priority, severity, reliability and validation lack one semantic system.
9. Narrow layouts stack content but do not provide responsive drawer navigation.
10. Generous padding and fixed maximum width reduce data density.
11. Loading and empty states exist but are not consistently componentised.
12. There is no persistent product/version/local-only shell status.

## Webify comparison

Already aligned:

- light neutral canvas;
- white operational surfaces;
- blue product accent;
- sparse semantic colour;
- accessible focus treatment on core controls.

Main gaps:

- no compact persistent sidebar;
- no consistent page header or active-case context;
- metrics are separate cards rather than a disciplined strip;
- lists are card-oriented instead of table-oriented;
- no shared token/primitive layer;
- workflow composition is vertical rather than task-focused;
- responsive behaviour is stacking rather than intentional adaptation.

## TRACE identity worksheet

- Accent: TRACE operational blue.
- Mark: restrained shield/evidence identity.
- Primary object: persisted investigation case.
- Navigation groups: Overview; Investigations; Active investigation; Reference and safety.
- Key statuses: draft, evidence validated, analyzed, reviewed, exported, archived.
- Key qualifiers: priority, scenario, evidence readiness, reliability, validation, severity, confidence.
- Primary pattern: compact case and evidence tables.
- Specialist patterns: provenance inventory, structured findings, immutable comparison, append-only timeline.
- Anti-patterns: invented investigators, tasks, ownership, progress percentages, trends, SLAs, live scanning, policy controls or remediation buttons.

## Workflow-preservation map

| Capability | Visual change allowed | Constraint |
|---|---|---|
| Case creation | Focused layout/drawer | Same API fields and validation |
| Case metadata | Persistent compact form | Do not change identity or runs |
| Lifecycle | Clear action grouping | Backend-supported transitions only |
| Evidence | Table/detail composition | Preserve provenance/reliability/validation |
| Analysis | Scenario-focused panel | Preserve active-case scenario lock |
| Findings | Split list/detail | Keep supporting/contradicting/missing separate |
| Timeline | Dense record view | Preserve append-only semantics and restrictions |
| Comparison | Better selector/diff layout | Preserve deterministic identity/export |
| Archive/reopen | Consistent confirmation | Preserve lifecycle restoration |
| Reports | Consolidated actions | Preserve report content/audit semantics |

## Recommended pilot

The operational dashboard is the pilot because it exercises shell, navigation, page header, metrics, filters, status system, case records, responsive behaviour and case opening without backend changes.

Pilot composition:

- persistent TRACE/Webify shell;
- compact product header and local/read-only status;
- supported workload metrics only;
- search/filter toolbar;
- compact case table using real fields;
- loading, empty, error and populated states;
- narrow-screen drawer and safe table overflow.

The pilot must not include investigators, tasks, ownership, progress percentages or unsupported charts from the concept mock.

## Proposed shared primitives

- `AppShell`
- `SidebarNavigation`
- `PageHeader`
- `ActiveCaseContext`
- `MetricStrip`
- `OperationalSurface`
- `FilterToolbar`
- `DataTable`
- semantic badge components
- shared loading, empty and error states
- accessible drawer/dialog patterns
- standard controls

No external UI framework or Storybook is justified at this stage.

## Phased implementation

### Phase 1 — Design foundation

- CSS custom-property tokens;
- typography, spacing, neutral, accent and semantic systems;
- focus/reduced-motion defaults;
- controls, badges, surfaces and states;
- shell and responsive navigation.

### Phase 2 — Dashboard pilot

- migrate dashboard into shell;
- convert case cards to compact table;
- preserve filters and workload calculations;
- add deterministic desktop/narrow screenshots;
- validate keyboard, focus, zoom and long data.

### Phase 3 — Case and evidence

- migrate case intake and active metadata;
- persistent active-case context;
- evidence inventory/validation;
- preserve archived/immutable restrictions.

### Phase 4 — Analysis and findings

- migrate scenario forms;
- findings list/detail composition;
- preserve evidence categories, limitations, safe checks and non-actions;
- retain raw views and exports.

### Phase 5 — Timeline, comparison and history

- dense timeline records;
- comparison and export;
- consolidate duplicated history presentation only where behaviour is unchanged.

### Phase 6 — Responsive, accessibility and proof

- desktop, laptop, narrow and 200% zoom;
- keyboard/focus proof;
- console and automated accessibility scan;
- empty/loading/error/partial/long-data fixtures;
- full CI, runtime, browser and release proof;
- before/after package and rollback documentation.

## Risks and controls

- Selector breakage: preserve semantic IDs initially and migrate tests per phase.
- Hidden workflows: maintain reachability matrix and scenario acceptance.
- Unsupported affordances: component APIs accept real domain fields only.
- Narrow tables: test overflow, prioritised columns and detail views.
- CSS regressions: token layer first and workflow-group PRs.
- Sensitive screenshots: public-safe fixtures and existing exclusions only.

## Rollback

- `v0.2.0` remains the immutable pre-refurbishment release.
- Each migration remains focused and revertible.
- No persistence migration or backend-contract change is planned for visual convenience.
- Existing semantic IDs and workflow tests remain until replacement proof is green.

## Remaining evidence questions

1. Explicit browser-console output per scenario.
2. Automated accessibility findings.
3. Focus restoration after opening a case at narrow width.
4. Long-data behaviour for titles, references, summaries, evidence and findings.
5. Whether the missing reference-image directory was intentionally omitted.

## Audit gate

Broad migration does not begin until the design foundation and dashboard pilot are implemented and verified as a focused change. All existing CI and release gates must remain green.