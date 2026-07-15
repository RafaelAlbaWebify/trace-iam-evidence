# Local runtime and portable review

TRACE v0.2 includes a self-locating Windows runtime manager and a separate public-safe review exporter. Both scripts resolve the repository from their own location, so they can be invoked from any working directory.

## Prerequisites

- Windows PowerShell 7 (`pwsh`)
- Python 3.12
- Node.js 22 with npm
- Git for source/version metadata in review packages

## Runtime data location

By default, TRACE stores local runtime data under:

```text
%LOCALAPPDATA%\TRACE-IAM-Evidence
```

Use `-DataDirectory` or the `TRACE_DATA_DIR` environment variable to select another location. The runtime directory contains the SQLite database, process state, logs and backups. It is deliberately separate from the repository.

## Start TRACE

From any directory:

```powershell
pwsh -File C:\path\to\trace-iam-evidence\scripts\trace.ps1 -Action start
```

Use `-NoBrowser` when TRACE should start without opening the browser. The UI is served at `http://127.0.0.1:5173` and the API health endpoint is `http://127.0.0.1:8000/api/health`.

The first start creates a Python 3.12 virtual environment, installs the backend and prepares frontend dependencies. Later starts reuse those dependencies.

## Status, diagnostics and stop

```powershell
pwsh -File C:\path\to\trace-iam-evidence\scripts\trace.ps1 -Action status
pwsh -File C:\path\to\trace-iam-evidence\scripts\trace.ps1 -Action diagnostics
pwsh -File C:\path\to\trace-iam-evidence\scripts\trace.ps1 -Action stop
```

`status` reports the runtime root, database path, state file and process state. `diagnostics` reports prerequisite availability, runtime paths, process state and SQLite integrity when a database exists. `stop` terminates both process trees, removes the transient state file and retains logs.

## Backup and restore

Create a verified SQLite online backup:

```powershell
pwsh -File C:\path\to\trace-iam-evidence\scripts\trace.ps1 -Action backup
```

Use `-BackupPath` to select an exact destination. Restore only while TRACE is stopped:

```powershell
pwsh -File C:\path\to\trace-iam-evidence\scripts\trace.ps1 -Action restore -RestorePath C:\path\to\backup.db
```

The restore utility rejects invalid SQLite sources before replacing the active database.

## Create the portable review ZIP

```powershell
pwsh -File C:\path\to\trace-iam-evidence\scripts\export_portable_review.ps1
```

The exporter creates a timestamped file directly in the current user's Downloads folder:

```text
TRACE_PORTABLE_REVIEW_YYYYMMDDTHHMMSSZ.zip
```

It does not open Downloads. `-DestinationDirectory` and `-OutputName` are available for controlled testing or an explicit alternate destination.

The archive contains:

- public-safe repository source and documentation;
- source commit, branch and repository metadata;
- package-generation diagnostics;
- public-safe scenario and release-workflow evidence inventory;
- review instructions;
- a SHA-256 manifest covering every packaged file.

The archive excludes Git metadata, dependency directories, virtual environments, build output, runtime state, logs, backups, SQLite databases, environment files, credentials, keys, certificates and local evidence. It is a review package, not a live-workspace backup.

## Automatic proof

The Windows CI proof runs the runtime manager from outside the repository and verifies:

- start, backend health and frontend availability;
- correct state paths and live process IDs;
- status output for both processes;
- stop and process-tree termination;
- state-file removal and log retention.

A second acceptance test creates the portable review ZIP twice at the same requested path and verifies required files, exclusions, diagnostics, release evidence and every SHA-256 manifest entry.
