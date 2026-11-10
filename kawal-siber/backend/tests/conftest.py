"""
conftest.py — Shared pytest fixtures for KAWAL SIBER backend tests.
"""
from __future__ import annotations

import os
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Test database — use a temp-directory SQLite file so tests are isolated
# and don't pollute the project directory.
# ---------------------------------------------------------------------------
_TMP_DIR = tempfile.mkdtemp()
_TEST_DB_PATH = os.path.join(_TMP_DIR, "test_kawal_siber.db")
TEST_DATABASE_URL = f"sqlite:///{_TEST_DB_PATH}"

# Create the test engine before importing app modules that touch the real engine
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)

from app.database import Base  # noqa: E402 — must come after env var is set
from app.dependencies import get_db  # noqa: E402
from app.main import app  # noqa: E402

_test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

@event.listens_for(_test_engine, "connect")
def _set_test_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

_TestingSessionLocal: sessionmaker[Session] = sessionmaker(
    bind=_test_engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


# ---------------------------------------------------------------------------
# Session-scoped setup / teardown
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """Create all tables once per test session; drop them when done."""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


# ---------------------------------------------------------------------------
# Function-scoped DB session with rollback isolation
# ---------------------------------------------------------------------------
@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """
    Yield a database session that is rolled back after each test,
    providing test isolation without needing to recreate the schema.
    """
    connection = _test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


# ---------------------------------------------------------------------------
# TestClient with overridden DB dependency
# ---------------------------------------------------------------------------
@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Return a TestClient that uses the isolated test session."""

    def _override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass  # rollback handled by db_session fixture

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
