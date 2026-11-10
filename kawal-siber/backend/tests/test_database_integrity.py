"""
test_database_integrity.py — Tests for database-level constraints,
foreign key enforcement, response_time validation, and persistence.
"""
from __future__ import annotations

import os
import tempfile
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import Asset, Incident


class TestDatabaseIntegrity:
    """Verify DB-level constraints, foreign keys, and persistence."""

    def test_invalid_status_enum_rejected_by_api(self, client) -> None:
        """API rejects invalid asset status."""
        resp = client.post(
            "/api/v1/assets/",
            json={"name": "Bad Status", "target_ip": "10.0.0.1", "port": 80, "status": "COMPROMISED"},
        )
        assert resp.status_code == 422

    def test_negative_response_time_rejected_by_api(self, client) -> None:
        """API rejects negative response_time_ms."""
        # Create asset first
        resp = client.post(
            "/api/v1/assets/",
            json={"name": "Response Time Test", "target_ip": "10.0.0.2", "port": 80},
        )
        assert resp.status_code == 201
        asset_id = resp.json()["id"]

        # Patch with negative response time
        patch_resp = client.patch(
            f"/api/v1/assets/{asset_id}",
            json={"response_time_ms": -5.0},
        )
        assert patch_resp.status_code == 422

    def test_db_check_constraint_negative_response_time(self, db_session: Session) -> None:
        """Database CheckConstraint rejects negative response_time_ms."""
        asset = Asset(
            name="DB Constraint Test",
            target_ip="10.0.0.3",
            port=80,
            status="UNKNOWN",
            response_time_ms=-1.0,
        )
        db_session.add(asset)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_db_foreign_key_violation_rejected(self, db_session: Session) -> None:
        """Database rejects inserting an incident referencing a non-existent asset_id."""
        incident = Incident(
            asset_id=9999999,
            source_ip="192.168.1.100",
            attack_type="SQL_INJECTION",
            severity="CRITICAL",
        )
        db_session.add(incident)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_database_persistence_across_connections(self) -> None:
        """Data written to SQLite remains persistent when a new connection opens."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db_file = f.name

        try:
            db_url = f"sqlite:///{temp_db_file}"
            engine1 = create_engine(db_url, connect_args={"check_same_thread": False})

            @event.listens_for(engine1, "connect")
            def set_pragmas(dbapi_conn, record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

            Base.metadata.create_all(bind=engine1)

            # Insert an asset in session 1
            with Session(engine1) as s1:
                asset = Asset(name="Persistent Server", target_ip="192.168.10.5", port=443, status="SAFE")
                s1.add(asset)
                s1.commit()
                created_id = asset.id

            engine1.dispose()

            # Open completely new engine and connection to same file
            engine2 = create_engine(db_url, connect_args={"check_same_thread": False})
            with Session(engine2) as s2:
                persisted_asset = s2.get(Asset, created_id)
                assert persisted_asset is not None
                assert persisted_asset.name == "Persistent Server"
                assert persisted_asset.status == "SAFE"
                assert persisted_asset.port == 443
            engine2.dispose()

        finally:
            if os.path.exists(temp_db_file):
                try:
                    os.remove(temp_db_file)
                except OSError:
                    pass

