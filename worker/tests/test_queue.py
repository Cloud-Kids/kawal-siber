"""
test_queue.py — Unit tests for SQLite job queue operations and state transitions.
"""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import Asset, ScanJob, ScanResult
from worker.queue import (
    claim_next_pending_job,
    mark_job_completed,
    mark_job_failed,
)


@pytest.fixture
def test_db_session():
    """Create an isolated temporary SQLite database for testing queue operations."""
    tmp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    engine = create_engine(f"sqlite:///{tmp_file.name}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_claim_next_pending_job(test_db_session: Session):
    db = test_db_session

    # Create dummy asset
    asset = Asset(
        name="Queue Asset",
        target_ip="192.168.1.10",
        port=80,
        status="UNKNOWN",
        availability_status="UNKNOWN",
    )
    db.add(asset)
    db.commit()

    # Create PENDING job
    job = ScanJob(asset_id=asset.id, status="PENDING")
    db.add(job)
    db.commit()

    # Claim job
    claimed = claim_next_pending_job(db)
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == "RUNNING"
    assert claimed.attempts == 1
    assert claimed.started_at is not None

    # Next claim should return None (no more PENDING jobs)
    second_claim = claim_next_pending_job(db)
    assert second_claim is None


def test_mark_job_completed_and_availability_evidence(test_db_session: Session):
    db = test_db_session

    asset = Asset(
        name="HTTP Server",
        target_ip="10.0.0.10",
        port=80,
        status="UNKNOWN",
        availability_status="UNKNOWN",
    )
    db.add(asset)
    db.commit()

    job = ScanJob(asset_id=asset.id, status="RUNNING", attempts=1)
    db.add(job)
    db.commit()

    findings = {
        "target_ip": "10.0.0.10",
        "host_status": "up",
        "duration_ms": 120,
        "scanner_version": "7.94",
        "ports": [
            {
                "protocol": "tcp",
                "port": 80,
                "state": "open",
                "reason": "syn-ack",
                "service_name": "http",
                "product": "Apache",
                "version": "2.4.52",
                "extra_info": "Debian",
            }
        ],
    }

    mark_job_completed(
        db=db,
        job_id=job.id,
        findings=findings,
        resolved_ip="10.0.0.10",
        scanner_version="7.94",
    )

    db.refresh(job)
    db.refresh(asset)

    assert job.status == "COMPLETED"
    assert job.resolved_ip == "10.0.0.10"
    assert job.duration_ms == 120
    assert len(job.results) == 1

    r = job.results[0]
    assert r.port == 80
    assert r.state == "open"
    assert r.service_name == "http"
    assert r.product == "Apache"

    # Availability MUST be updated based on verified port responsiveness
    assert asset.availability_status == "UP"
    assert asset.response_time_ms == 120.0
    assert asset.last_scanned is not None

    # CRITICAL: Security status MUST remain UNKNOWN (never automatically made SAFE by Nmap)
    assert asset.status == "UNKNOWN"


def test_mark_job_failed(test_db_session: Session):
    db = test_db_session

    asset = Asset(
        name="Failing Asset",
        target_ip="10.0.0.20",
        port=22,
        status="UNKNOWN",
        availability_status="UNKNOWN",
    )
    db.add(asset)
    db.commit()

    job = ScanJob(asset_id=asset.id, status="RUNNING", attempts=1)
    db.add(job)
    db.commit()

    mark_job_failed(
        db=db,
        job_id=job.id,
        error_code="TIMEOUT",
        error_message="Host unreachable after 60s timeout",
        resolved_ip="10.0.0.20",
    )

    db.refresh(job)
    assert job.status == "FAILED"
    assert job.error_code == "TIMEOUT"
    assert "Host unreachable" in job.error_message
    assert job.finished_at is not None

