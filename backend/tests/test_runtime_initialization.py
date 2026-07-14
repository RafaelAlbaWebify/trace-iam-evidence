from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock
from time import sleep

from trace_iam.persistence import runtime


def test_concurrent_repository_initialization_migrates_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database = tmp_path / "trace.db"
    barrier = Barrier(2)
    calls: list[Path] = []
    calls_lock = Lock()

    def fake_migrate(path: Path) -> None:
        with calls_lock:
            calls.append(path)
        sleep(0.05)

    runtime.reset_repository_cache()
    monkeypatch.setattr(runtime, "migrate_database", fake_migrate)

    def initialize() -> Path:
        barrier.wait()
        return runtime.ensure_database(database)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(lambda _: initialize(), range(2)))

    assert results == (database.resolve(), database.resolve())
    assert calls == [database.resolve()]
    runtime.reset_repository_cache()
