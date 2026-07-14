import sqlite3
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "trace_database.py"


def run_utility(*arguments: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(argument) for argument in arguments)],
        check=True,
        capture_output=True,
        text=True,
    )


def test_backup_and_restore_preserve_a_valid_database(tmp_path: Path) -> None:
    database = tmp_path / "trace.db"
    backup = tmp_path / "backups" / "trace-backup.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO evidence(value) VALUES ('original')")
        connection.commit()

    run_utility("backup", database, backup)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE evidence SET value = 'changed'")
        connection.commit()

    run_utility("restore", backup, database)
    verification = run_utility("verify", database)

    assert '"integrity": "ok"' in verification.stdout
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT value FROM evidence").fetchone() == ("original",)


def test_restore_rejects_an_invalid_source(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.db"
    database = tmp_path / "trace.db"
    invalid.write_text("not sqlite", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "restore", str(invalid), str(database)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert not database.exists()
