# TRACE IAM Evidence

TRACE IAM Evidence is a local-first, read-only IAM and access-support investigation workbench. It structures redacted evidence, evaluates deterministic versioned rules, records uncertainty and limitations, generates reviewable Markdown and JSON reports, and preserves immutable local investigation history.

## Verified release scope

The portfolio release supports three public-safe investigation scenarios:

1. **Conditional Access** — structured manual evidence and a documented redacted Entra sign-in CSV contract.
2. **Resource assignment** — evidence-supported review of a missing subject-to-resource assignment.
3. **Guest and B2B lifecycle** — distinct invitation, redemption, tenant-restriction, and resource-assignment evidence.

The browser workflow currently demonstrates Conditional Access analysis, persisted history, report export, archive, and reopen. Resource-assignment and guest/B2B workflows are available through the tested backend contracts and API.

## What TRACE proves

- Shared source-independent investigation and evidence contracts.
- Scenario-specific adapters and deterministic rules using one rule interface.
- Supporting, contradicting, and missing evidence in findings.
- Safe recommended checks and explicit non-actions.
- Alembic-managed SQLite persistence and immutable analysis runs.
- JSON and Markdown report generation and export.
- Ubuntu and Windows lint, strict type checking, tests, and frontend builds.
- Chromium browser acceptance proof with generated reports, logs, and screenshots.
- Reproducible public-safe release proof with SHA-256 manifest.

## Safety boundary

- Local-first and read-only.
- Redacted or public-safe sample evidence only.
- No credentials, tenant-wide scanning, or Microsoft Graph connection.
- No automatic access, identity, invitation, policy, licensing, or remediation changes.
- No recommendation to disable Conditional Access globally or weaken cross-tenant controls.
- No root-cause claim without sufficient supporting evidence.
- Every finding exposes its rule identity, evidence basis, limitations, and uncertainty.

## Quick start

Prerequisites: Python 3.12 and Node.js 22.

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
- [Setup and demo](docs/setup-and-demo.md)
- [Known limitations](docs/known-limitations.md)
- [Roadmap](docs/roadmap.md)
- [Release notes](CHANGELOG.md)

## Development method

No feature is considered complete because code exists. Every milestone is developed in a focused branch, validated through GitHub Actions, inspected at job and artifact level, and merged only after its automatic proof is green.
