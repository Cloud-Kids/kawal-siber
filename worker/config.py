"""
config.py — Configuration parameters for KAWAL SIBER Security Worker.
Supports Localhost-First development and Docker-Later portability.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

# Resolve default local database path under storage/ if DATABASE_URL is not set
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "storage" / "kawal_siber.db"


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    """Create the parent directory only for file-backed SQLite databases."""
    try:
        from sqlalchemy.engine import make_url
        url = make_url(database_url)
    except Exception:
        return
    if url.get_backend_name() != "sqlite":
        return
    db_path = url.database
    if not db_path or db_path == ":memory:":
        return
    Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _resolve_nmap_path() -> str:
    """
    Intelligently discover Nmap executable:
    1. Check NMAP_PATH environment variable.
    2. Check system PATH.
    3. Check standard Windows Program Files installation paths.
    4. Fall back to "nmap".
    """
    env_path = os.environ.get("NMAP_PATH")
    if env_path and (Path(env_path).exists() or shutil.which(env_path)):
        return env_path

    which_path = shutil.which("nmap")
    if which_path:
        return which_path

    # Common Windows installation locations
    for fallback in [
        r"C:\Program Files (x86)\Nmap\nmap.exe",
        r"C:\Program Files\Nmap\nmap.exe",
    ]:
        if Path(fallback).exists():
            return fallback

    return "nmap"


class WorkerConfig:
    """Worker runtime configuration loaded from environment."""

    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL", f"sqlite:///{_DEFAULT_DB_PATH.as_posix()}"
    )

    def __init__(self) -> None:
        _ensure_sqlite_parent_dir(self.DATABASE_URL)

    # CRITICAL: Scanning is disabled by default until explicitly enabled by operator
    SCAN_ENABLED: bool = (
        os.environ.get("SCAN_ENABLED", "false").lower() in ("true", "1", "yes")
    )

    # Max XML payload allowed from Nmap to prevent memory exhaustion
    MAX_XML_BYTES: int = int(os.environ.get("MAX_XML_BYTES", 1024 * 1024))  # 1MB

    # Subprocess execution timeout
    NMAP_TIMEOUT_SECONDS: int = int(os.environ.get("NMAP_TIMEOUT_SECONDS", 60))

    # Job queue polling interval
    POLL_INTERVAL_SECONDS: float = float(
        os.environ.get("POLL_INTERVAL_SECONDS", 3.0)
    )

    # Path to nmap binary (dynamically discovered on Windows localhost and Linux container)
    NMAP_PATH: str = _resolve_nmap_path()


config = WorkerConfig()
