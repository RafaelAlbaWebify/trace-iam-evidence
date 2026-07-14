from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def verify_database(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False, "path": str(path), "integrity": "missing", "size_bytes": 0}
    with sqlite3.connect(path) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
    return {
        "exists": True,
        "path": str(path),
        "integrity": integrity,
        "size_bytes": path.stat().st_size,
        "tables": tables,
    }


def _sqlite_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(destination) as destination_connection:
            source_connection.backup(destination_connection)


def backup_database(source: Path, destination: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"TRACE database does not exist: {source}")
    destination.unlink(missing_ok=True)
    _sqlite_copy(source, destination)
    result = verify_database(destination)
    if result["integrity"] != "ok":
        destination.unlink(missing_ok=True)
        raise RuntimeError("Backup integrity verification failed")
    return destination


def restore_database(source: Path, destination: Path) -> Path:
    result = verify_database(source)
    if result["integrity"] != "ok":
        raise RuntimeError(f"Restore source is not a valid SQLite database: {source}")

    previous = destination.with_suffix(destination.suffix + ".restore-previous.db")
    previous.unlink(missing_ok=True)
    had_destination = destination.exists()
    if had_destination:
        shutil.copy2(destination, previous)
        if verify_database(previous)["integrity"] != "ok":
            previous.unlink(missing_ok=True)
            raise RuntimeError("Current database rollback copy failed integrity verification")

    try:
        _sqlite_copy(source, destination)
        if verify_database(destination)["integrity"] != "ok":
            raise RuntimeError("Restored database failed integrity verification")
    except Exception:
        if previous.exists():
            shutil.copy2(previous, destination)
        elif not had_destination:
            destination.unlink(missing_ok=True)
        raise
    finally:
        previous.unlink(missing_ok=True)
    return destination


def default_backup_name() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"trace-iam-evidence-{stamp}.db"


def main() -> int:
    parser = argparse.ArgumentParser(description="TRACE SQLite backup, restore, and verification")
    subparsers = parser.add_subparsers(dest="action", required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("database", type=Path)

    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument("database", type=Path)
    backup_parser.add_argument("destination", type=Path)

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("source", type=Path)
    restore_parser.add_argument("database", type=Path)

    args = parser.parse_args()
    if args.action == "verify":
        print(json.dumps(verify_database(args.database), indent=2))
    elif args.action == "backup":
        print(backup_database(args.database, args.destination))
    elif args.action == "restore":
        print(restore_database(args.source, args.database))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
