import os
from functools import lru_cache
from pathlib import Path

from alembic import command
from alembic.config import Config

from .database import sqlite_engine
from .repository import EvidenceRetentionMode, InvestigationRepository
from .timeline import TimelineRepository


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


@lru_cache(maxsize=1)
def get_repository() -> InvestigationRepository:
    path = database_path()
    migrate_database(path)
    return InvestigationRepository(sqlite_engine(path), retention_mode=retention_mode())


@lru_cache(maxsize=1)
def get_timeline_repository() -> TimelineRepository:
    path = database_path()
    migrate_database(path)
    return TimelineRepository(sqlite_engine(path))


def reset_repository_cache() -> None:
    get_repository.cache_clear()
    get_timeline_repository.cache_clear()
