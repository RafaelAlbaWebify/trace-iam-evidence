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

TRACE is local-first and read-only. It does not connect to Microsoft Graph, inspect a live tenant, grant access, change policies, or remediate findings.

## Browser demo

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
