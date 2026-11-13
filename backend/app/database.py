"""
database.py — SQLAlchemy 2.x engine and session configuration for KAWAL SIBER.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Common declarative base for all ORM models."""
    pass

# ---------------------------------------------------------------------------
# URL resolution (Localhost-First default with Docker portability)
# ---------------------------------------------------------------------------
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "storage" / "kawal_siber.db"

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{_DEFAULT_DB_PATH.as_posix()}",
)


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    """Create the parent directory only for file-backed SQLite databases.

    No-op for in-memory SQLite (``:memory:``), remote databases
    (PostgreSQL etc.), and unparseable URLs.
    """
    try:
        url = make_url(database_url)
    except Exception:
        return
    if url.get_backend_name() != "sqlite":
        return
    db_path = url.database
    if not db_path or db_path == ":memory:":
        return
    Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(DATABASE_URL)

# ---------------------------------------------------------------------------
# Engine creation
# ---------------------------------------------------------------------------
_connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=False,
    future=True,
)


# ---------------------------------------------------------------------------
# Post-connect PRAGMAs for SQLite
# ---------------------------------------------------------------------------
@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:  # noqa: ANN001
    """Enable foreign keys, WAL journal mode, and a busy timeout for SQLite."""
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        # Judge mode mounts judge.db read-only: WAL needs -wal/-shm writes,
        # so keep the snapshot's rollback journal mode instead.
        if not os.environ.get("KAWAL_JUDGE_MODE", "").lower() == "true":
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


# ---------------------------------------------------------------------------
# Dependency-injection helper
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed after use."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
