# TRACE IAM Evidence

> [!NOTE]
> **This is the current maintained TRACE repository and the canonical source for the project.**
>
> It supersedes the earlier [`trace-ops`](https://github.com/RafaelAlbaWebify/trace-ops) prototype, which is retained only as development history.

TRACE IAM Evidence is a local-first, read-only IAM and access-support investigation workbench. It structures redacted evidence, evaluates deterministic versioned rules, records uncertainty and limitations, generates reviewable Markdown and JSON reports, and preserves immutable local investigation history.

## Stable release scope

TRACE supports three public-safe operator workflows in the browser:

1. **Conditional Access** — documented redacted Entra sign-in CSV evidence.
2. **Resource assignment** — evidence-supported review of a missing subject-to-resource assignment.
3. **Guest and B2B lifecycle** — distinct invitation, redemption, tenant-restriction, and resource-assignment evidence.

Every workflow uses the same local persistence, immutable analysis history, JSON and Markdown exports, archive/reopen behavior, and browser acceptance proof.

## What TRACE proves

- Shared source-independent investigation and evidence contracts.
- Scenario-specific adapters and deterministic rules using one rule interface.
- Supporting, contradicting, and missing evidence in findings.
- Safe recommended checks and explicit non-actions.
- Alembic-managed SQLite persistence and immutable analysis runs.
- JSON and Markdown report generation and export.
- Accessible scenario navigation, validation guidance, loading states, and readable API errors.
- Ubuntu and Windows lint, strict type checking, tests, and frontend builds.
- Chromium browser acceptance proof for all three supported scenarios.
- Reproducible public-safe release proof with SHA-256 manifest.
- Self-locating Windows runtime management with verified SQLite backup and restore.
- Portable public-safe review packaging with diagnostics, release evidence and integrity proof.
- A responsive operational interface covering dashboard, cases, evidence, findings, timeline, run comparison, history, and reports.

## Safety boundary

- Local-first and read-only.
- Redacted or public-safe sample evidence only.
- No credentials, tenant-wide scanning, or Microsoft Graph connection.
- No automatic access, identity, invitation, policy, licensing, or remediation changes.
- No recommendation to disable Conditional Access globally or weaken cross-tenant controls.
- No root-cause claim without sufficient supporting evidence.
- Every finding exposes its rule identity, evidence basis, limitations, and uncertainty.

Before using TRACE, replace real names, email addresses, tenant IDs, object IDs, tokens, and confidential resource names with non-identifying placeholders.

## Windows local runtime

Prerequisites: PowerShell 7, Python 3.12 and Node.js 22.

Start TRACE from any working directory:

```powershell
pwsh -File C:\path\to\trace-iam-evidence\scripts\trace.ps1 -Action start
```

The UI is available at `http://127.0.0.1:5173`. Runtime data is stored outside the repository under `%LOCALAPPDATA%\TRACE-IAM-Evidence` by default. Use `-DataDirectory` or `TRACE_DATA_DIR` to select another local path.

Common operations:

```powershell
pwsh -File C:\path\to\trace-iam-evidence\scripts\trace.ps1 -Action status
pwsh -File C:\path\to\trace-iam-evidence\scripts\trace.ps1 -Action diagnostics
pwsh -File C:\path\to\trace-iam-evidence\scripts\trace.ps1 -Action backup
pwsh -File C:\path\to\trace-iam-evidence\scripts\trace.ps1 -Action stop
```

Restore a verified backup only while TRACE is stopped:

```powershell
pwsh -File C:\path\to\trace-iam-evidence\scripts\trace.ps1 -Action restore -RestorePath C:\path\to\backup.db
```

## Portable review ZIP

Create a timestamped, public-safe review archive directly in Downloads:

```powershell
pwsh -File C:\path\to\trace-iam-evidence\scripts\export_portable_review.ps1
```

The exporter does not open the Downloads folder. The archive includes selected public-safe source, documentation, source/version metadata, environment diagnostics, scenario and release-workflow evidence, review instructions and a SHA-256 manifest. It excludes credentials, local evidence, runtime state, databases, logs, backups, virtual environments, dependency directories and build output.

See [Local runtime and portable review](docs/local-runtime-and-portable-review.md) for complete operating instructions and proof boundaries.

## Manual development start

```bash
python -m pip install --upgrade pip
python -m pip install -e "backend[dev]"
npm --prefix frontend install --ignore-scripts
```

Run the API:

```bash
python -m uvicorn trace_iam.main:app --host 127.0.0.1 --port 8000
```

Run the frontend in a second terminal:

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 4173
```

Open `http://127.0.0.1:4173`.

The operator interface includes public-safe defaults for demonstration. Use the scenario guidance before replacing them with your own redacted evidence.

## Rebuild the release proof

From the `backend` directory:

```bash
python scripts/build_release_pack.py \
  --scenarios ../examples/scenarios \
  --output ../release-proof
```

The generated pack contains one JSON report and one Markdown report per scenario plus a cryptographic manifest. GitHub Actions builds the same pack on Ubuntu and Windows and retains downloadable proof artifacts.

## Documentation

- [Architecture diagram](docs/architecture-diagram.md)
- [Setup and three-scenario demo](docs/setup-and-demo.md)
- [Local runtime and portable review](docs/local-runtime-and-portable-review.md)
- [Known limitations](docs/known-limitations.md)
- [v0.2 roadmap](docs/v0.2-roadmap.md)
- [Release notes](CHANGELOG.md)

## Development method

No feature is considered complete because code exists. Every milestone is developed in a focused branch, validated through GitHub Actions, inspected at job and artifact level, and merged only after its automatic proof is green.
