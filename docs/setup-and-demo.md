# Setup and three-scenario demo

## Prerequisites

- Python 3.12
- Node.js 22
- Git

## Install

```bash
python -m pip install --upgrade pip
python -m pip install -e "backend[dev]"
npm --prefix frontend install --ignore-scripts
```

## Run the application

Terminal 1:

```bash
python -m uvicorn trace_iam.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 4173
```

Open `http://127.0.0.1:4173`.

## Evidence preparation

TRACE accepts redacted or public-safe evidence only. Before replacing the supplied samples, remove or replace:

- real names and email addresses;
- tenant, object, sign-in, and correlation identifiers;
- tokens, secrets, credentials, and session data;
- confidential application, customer, or resource names.

TRACE is local-first and read-only. The default demo uses public-safe synthetic Graph-shaped evidence. Optional live Microsoft Graph acquisition is explicitly configured and read-only; TRACE never grants access, changes policies/compliance, or remediates findings.

## Browser demo

### 0. Recruiter path — Microsoft Graph + Intune

1. Select **Load Graph + Intune demo** in the first viewport.
2. Confirm that the active case is **Managed device blocked by Conditional Access**.
3. Review Graph provenance for Entra sign-ins, Conditional Access policy context and Intune managed-device evidence.
4. Confirm that `CA-002` states correlation with noncompliant-device evidence and explicitly says this does not prove causation.
5. Review the safe device/policy checks and the explicit non-action.

This path requires no tenant or credentials. See [Microsoft Graph live mode](microsoft-graph-live-mode.md) for the optional delegated read-only connection.

### 1. Conditional Access

1. Use the preloaded public-safe four-column CSV.
2. Select **Analyze evidence**.
3. Confirm that the result summary shows run 1, one finding, and `CA-001`.
4. Expand the evidence report and review the safe next check and the explicit instruction not to disable Conditional Access globally.

### 2. Resource assignment

1. Navigate to **Resource assignment**.
2. Keep the redacted subject, resource, and expected assignment sample values.
3. Leave **Assignment is present in supplied evidence** cleared.
4. Select **Analyze resource assignment**.
5. Confirm that `RA-001` is evaluated and that the report prohibits broad or tenant-wide privilege grants.

### 3. Guest/B2B lifecycle

1. Navigate to **Guest / B2B**.
2. Keep invitation sent selected and invitation redeemed cleared.
3. Keep tenant restriction and resource assignment cleared.
4. Select **Analyze Guest B2B evidence**.
5. Confirm that `GB-001` is produced and that the report instructs the operator not to recreate the guest or issue repeated invitations without checking the existing lifecycle.

### 4. History and exports

1. Open **Investigation history**.
2. Select an investigation to view its immutable analysis runs.
3. Export the stored JSON and Markdown reports.
4. Archive an investigation, enable **Show archived investigations**, and reopen it.

The interface distinguishes loading, empty-history, validation, API-connection, and successful-analysis states. FastAPI field validation is rendered as readable operator guidance rather than raw JSON objects.

## Rebuild the portfolio release proof

From the `backend` directory:

```bash
python scripts/build_release_pack.py \
  --scenarios ../examples/scenarios \
  --output ../release-proof
```

The command replaces `release-proof` with:

- `manifest.json` containing scenario identities, evaluated rules, finding counts, and SHA-256 digests;
- one JSON report for each public-safe scenario;
- one Markdown report for each public-safe scenario.

The build fails unless all three documented scenarios are present.

## Verification commands

Backend:

```bash
cd backend
python -m ruff check .
python -m mypy src
python -m pytest -q
```

Frontend:

```bash
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
```

Browser acceptance:

```bash
npm --prefix frontend run e2e
```

GitHub Actions performs these checks on Ubuntu and Windows and retains backend, frontend, browser, report, screenshot, and release-pack proof artifacts.
