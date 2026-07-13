# Setup and demo

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

## Browser demo

1. Use the preloaded public-safe Conditional Access CSV.
2. Select **Analyze evidence**.
3. Review the rule identity, finding count, safe next check, and explicit non-action.
4. Open the persisted investigation history.
5. Export the stored JSON or Markdown report.
6. Archive the investigation, show archived investigations, and reopen it.

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

GitHub Actions performs these checks on Ubuntu and Windows and retains the generated proof artifacts.
