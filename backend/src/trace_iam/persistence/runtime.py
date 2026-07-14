import os
from functools import lru_cache
from pathlib import Path
from threading import Lock

from alembic import command
from alembic.config import Config

from .database import sqlite_engine
from .repository import EvidenceRetentionMode, InvestigationRepository
from .timeline import TimelineRepository
from .timeline_hooks import install_timeline_hooks

install_timeline_hooks()

_migration_lock = Lock()
_migrated_paths: set[Path] = set()


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def database_path() -> Path:
    configured = os.getenv("TRACE_DB_PATH")
    return Path(configured) if configured else _backend_root() / "trace_iam.db"


def retention_mode() -> EvidenceRetentionMode:
    configured = os.getenv("TRACE_EVIDENCE_RETENTION", EvidenceRetentionMode.FULL_REDACTED.value)
    try:
        return EvidenceRetentionMode(configured)
    except ValueError as exc:
        allowed = ", ".join(mode.value for mode in EvidenceRetentionMode)
        raise RuntimeError(
            f"Unsupported TRACE_EVIDENCE_RETENTION {configured!r}; expected one of {allowed}"
        ) from exc


def migrate_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    config = Config(str(_backend_root() / "alembic.ini"))
    config.set_main_option("script_location", str(_backend_root() / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(config, "head")


def ensure_database(path: Path) -> Path:
    resolved = path.resolve()
    if resolved in _migrated_paths:
        return resolved
    with _migration_lock:
        if resolved not in _migrated_paths:
            migrate_database(resolved)
            _migrated_paths.add(resolved)
    return resolved


@lru_cache(maxsize=1)
def get_repository() -> InvestigationRepository:
    path = ensure_database(database_path())
    return InvestigationRepository(sqlite_engine(path), retention_mode=retention_mode())


@lru_cache(maxsize=1)
def get_timeline_repository() -> TimelineRepository:
    path = ensure_database(database_path())
    return TimelineRepository(sqlite_engine(path))


def reset_repository_cache() -> None:
    get_repository.cache_clear()
    get_timeline_repository.cache_clear()
    with _migration_lock:
        _migrated_paths.clear()
