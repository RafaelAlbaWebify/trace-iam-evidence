from pathlib import Path

from sqlalchemy import Engine, create_engine


def sqlite_engine(database_path: Path) -> Engine:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{database_path}", future=True)
