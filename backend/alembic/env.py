"""
alembic/env.py — Alembic migration environment for KAWAL SIBER.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

# Ensure backend root is on sys.path regardless of execution method
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Import application models so Alembic knows what to autogenerate against
# ---------------------------------------------------------------------------
from app.database import Base  # noqa: E402
from app import models  # noqa: F401, E402 — register models on Base.metadata

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for 'autogenerate' support
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Resolve DATABASE_URL from environment (Localhost-First default with Docker portability)
# ---------------------------------------------------------------------------
from pathlib import Path

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "storage" / "kawal_siber.db"
_DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{_DEFAULT_DB_PATH.as_posix()}",
)

# Inject into alembic config so engine_from_config picks it up
config.set_main_option("sqlalchemy.url", DATABASE_URL)


# ---------------------------------------------------------------------------
# SQLite-specific connect args
# ---------------------------------------------------------------------------
def _get_connect_args() -> dict:
    if DATABASE_URL.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


# ---------------------------------------------------------------------------
# Offline migration mode
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations without an active database connection."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        render_as_batch=True,  # required for SQLite ALTER support
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration mode
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """Run migrations with an active database connection."""
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = DATABASE_URL

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_get_connect_args(),
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            render_as_batch=True,  # required for SQLite ALTER support
        )
        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
