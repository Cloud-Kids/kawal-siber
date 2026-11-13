"""
Regression tests for D3 (database path init) and D5 (centralized storage paths).
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.engine import make_url


def test_make_url_parses_sqlite_file(tmp_path):
    url = make_url("sqlite:////data/kawal_siber.db")
    assert url.get_backend_name() == "sqlite"
    assert url.database == "/data/kawal_siber.db"


def test_make_url_parses_memory():
    url = make_url("sqlite:///:memory:")
    assert url.database in (None, ":memory:")


def test_make_url_parses_postgres():
    url = make_url("postgresql+psycopg://user:pass@host:5432/db")
    assert url.get_backend_name() == "postgresql"


class TestStoragePaths:
    def test_defaults_under_repo_storage(self):
        from app import paths
        assert paths.STORAGE_ROOT.name == "storage"
        assert paths.REPORTS_DIR.name == "reports"
        assert paths.PCAP_DIR.name == "pcaps"
        assert paths.SURICATA_LOGS_DIR.name == "logs"

    def test_env_override_storage_root(self, monkeypatch, tmp_path):
        monkeypatch.setenv("KAWAL_STORAGE_ROOT", str(tmp_path / "custom"))
        import app.paths as paths
        importlib.reload(paths)
        try:
            assert paths.STORAGE_ROOT == (tmp_path / "custom").resolve()
            assert paths.REPORTS_DIR == paths.STORAGE_ROOT / "reports"
        finally:
            monkeypatch.delenv("KAWAL_STORAGE_ROOT", raising=False)
            importlib.reload(paths)

    def test_reports_path_env_override(self, monkeypatch, tmp_path):
        target = tmp_path / "my_reports"
        monkeypatch.setenv("REPORTS_STORAGE_PATH", str(target))
        import app.paths as paths
        importlib.reload(paths)
        try:
            assert paths.REPORTS_DIR == target.resolve()
        finally:
            monkeypatch.delenv("REPORTS_STORAGE_PATH", raising=False)
            importlib.reload(paths)

    def test_ensure_dirs_creates_only_storage_tree(self, monkeypatch, tmp_path):
        root = tmp_path / "root"
        monkeypatch.setenv("KAWAL_STORAGE_ROOT", str(root))
        import app.paths as paths
        importlib.reload(paths)
        try:
            paths.ensure_storage_dirs()
            assert (root / "reports").is_dir()
            assert (root / "pcaps").is_dir()
            assert (root / "suricata" / "logs").is_dir()
        finally:
            monkeypatch.delenv("KAWAL_STORAGE_ROOT", raising=False)
            importlib.reload(paths)


class TestDatabasePathInit:
    """D3: database.py must not mkdir for non-file or env-configured URLs."""

    def _fresh_database_module(self):
        sys.modules.pop("app.database", None)
        return importlib.import_module("app.database")

    def test_postgres_url_no_mkdir(self, monkeypatch):
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db"
        )
        created = []
        real_mkdir = Path.mkdir

        def spy(self, *a, **kw):
            created.append(str(self))
            return real_mkdir(self, *a, **kw)

        # Avoid needing the psycopg driver just to test path init:
        # substitute a real in-memory engine for whatever URL is requested.
        real_create_engine = __import__("sqlalchemy").create_engine
        with patch(
            "sqlalchemy.create_engine",
            side_effect=lambda *a, **k: real_create_engine("sqlite:///:memory:"),
        ), patch.object(Path, "mkdir", spy):
            self._fresh_database_module()
        assert not any("kawal_siber.db" in p for p in created)

    def test_sqlite_env_path_parent_created(self, monkeypatch, tmp_path):
        db_file = tmp_path / "nested" / "test.db"
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
        self._fresh_database_module()
        assert db_file.parent.is_dir()

    def test_sqlite_memory_no_dir_created(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
        created = []
        real_mkdir = Path.mkdir

        def spy(self, *a, **kw):
            created.append(str(self))
            return real_mkdir(self, *a, **kw)

        with patch.object(Path, "mkdir", spy):
            self._fresh_database_module()
        assert not any("storage" in p for p in created)
