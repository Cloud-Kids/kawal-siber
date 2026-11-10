"""
database.py — SQLAlchemy 2.x engine and session configuration for KAWAL SIBER.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, text
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
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "storage" / "kawal_siber.db"
_DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{_DEFAULT_DB_PATH.as_posix()}",
)

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
