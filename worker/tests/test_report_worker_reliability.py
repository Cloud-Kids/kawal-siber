"""
test_report_worker_reliability.py — Worker queue reliability and report execution tests.
Tests run against an isolated temporary SQLite database without touching production-dev DB.
"""
from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import GeneratedReport
from app.reporting.engine import ReportingEngine
from worker.queue import claim_next_pending_report, recover_stale_running_reports


@pytest.fixture
def temp_db_session():
    """Isolated temporary SQLite database for testing worker report queue operations."""
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
        try:
            Path(tmp_file.name).unlink(missing_ok=True)
        except Exception:
            pass


def test_report_priority_queue_ordering(temp_db_session: Session):
    """Verify claim_next_pending_report claims jobs by job_priority ASC (lower=higher priority),
    then created_at ASC."""
    db = temp_db_session

    now = datetime.now(timezone.utc)
    rep_low = GeneratedReport(
        report_id="REP-PRIO-LOW",
        report_type="EXECUTIVE",
        title="Low Priority Report",
        format="JSON",
        generation_status="PENDING",
        job_priority=10,
        created_at=now - timedelta(minutes=5),
        generated_by="Tester",
    )
    rep_high = GeneratedReport(
        report_id="REP-PRIO-HIGH",
        report_type="EXECUTIVE",
        title="High Priority Report",
        format="JSON",
        generation_status="PENDING",
        job_priority=1,
        created_at=now - timedelta(minutes=1),
        generated_by="Commander",
    )
    rep_med = GeneratedReport(
        report_id="REP-PRIO-MED",
        report_type="EXECUTIVE",
        title="Medium Priority Report",
        format="JSON",
        generation_status="PENDING",
        job_priority=5,
        created_at=now - timedelta(minutes=3),
        generated_by="Auditor",
    )
    db.add_all([rep_low, rep_high, rep_med])
    db.commit()

    # Claim 1: must be rep_high (priority=1)
    c1 = claim_next_pending_report(db)
    assert c1 is not None
    assert c1.report_id == "REP-PRIO-HIGH"
    assert c1.generation_status == "RUNNING"

    # Claim 2: must be rep_med (priority=5)
    c2 = claim_next_pending_report(db)
    assert c2 is not None
    assert c2.report_id == "REP-PRIO-MED"
    assert c2.generation_status == "RUNNING"

    # Claim 3: must be rep_low (priority=10)
    c3 = claim_next_pending_report(db)
    assert c3 is not None
    assert c3.report_id == "REP-PRIO-LOW"
    assert c3.generation_status == "RUNNING"

    # Claim 4: no pending jobs
    c4 = claim_next_pending_report(db)
    assert c4 is None


def test_stale_job_recovery(temp_db_session: Session):
    """Verify recover_stale_running_reports resets RUNNING reports older than timeout to PENDING."""
    db = temp_db_session

    now = datetime.now(timezone.utc)
    stale_rep = GeneratedReport(
        report_id="REP-STALE-JOB",
        report_type="TECHNICAL",
        title="Stale Report",
        format="JSON",
        generation_status="RUNNING",
        created_at=now - timedelta(minutes=25),  # older than default 15min timeout
        generated_by="Worker1",
    )
    fresh_rep = GeneratedReport(
        report_id="REP-FRESH-JOB",
        report_type="TECHNICAL",
        title="Fresh Report",
        format="JSON",
        generation_status="RUNNING",
        created_at=now - timedelta(minutes=3),  # only 3min old
        generated_by="Worker2",
    )
    db.add_all([stale_rep, fresh_rep])
    db.commit()

    recovered = recover_stale_running_reports(db, timeout_minutes=15)
    assert recovered == 1

    db.refresh(stale_rep)
    db.refresh(fresh_rep)

    assert stale_rep.generation_status == "PENDING"
    assert "timeout" in (stale_rep.error_message or "").lower()
    assert fresh_rep.generation_status == "RUNNING"


def test_report_generation_idempotency(temp_db_session: Session, tmp_path: Path):
    """Verify that if a report is already COMPLETED and its file exists on disk,
    process_report_job does not regenerate or duplicate records."""
    db = temp_db_session
    rpt_dir = tmp_path / "reports"
    rpt_dir.mkdir()

    rep = GeneratedReport(
        report_id="REP-IDEMPOTENT-001",
        report_type="EXECUTIVE",
        title="Idempotency Test",
        format="JSON",
        generation_status="PENDING",
        generated_by="Tester",
    )
    db.add(rep)
    db.commit()

    engine = ReportingEngine(db, reports_dir=rpt_dir)
    first_res = engine.process_report_job(rep.report_id)
    assert first_res.generation_status == "COMPLETED"
    orig_uuid = first_res.file_uuid
    orig_checksum = first_res.sha256_checksum

    # Second execution: should be skipped idempotently
    second_res = engine.process_report_job(rep.report_id)
    assert second_res.generation_status == "COMPLETED"
    assert second_res.file_uuid == orig_uuid
    assert second_res.sha256_checksum == orig_checksum


def test_temp_file_cleanup_on_failure(temp_db_session: Session, tmp_path: Path):
    """Verify that if report rendering throws an exception, the temporary file is unlinked
    and no partial or corrupt file remains in the reports directory."""
    db = temp_db_session
    rpt_dir = tmp_path / "reports"
    rpt_dir.mkdir()

    rep = GeneratedReport(
        report_id="REP-FAIL-CLEANUP",
        report_type="EXECUTIVE",
        title="Failure Cleanup Test",
        format="PDF",
        generation_status="PENDING",
        generated_by="Tester",
    )
    db.add(rep)
    db.commit()

    engine = ReportingEngine(db, reports_dir=rpt_dir)

    def failing_pdf_export(data, out_path):
        out_path.write_text("Partial corrupt content")
        raise RuntimeError("Simulated printer/render crash")

    with patch("app.reporting.engine.export_to_pdf", side_effect=failing_pdf_export):
        result = engine.process_report_job(rep.report_id)

    # Job is marked FAILED or re-queued
    assert result.generation_status in ("FAILED", "PENDING")
    # Verify no .tmp files remain in rpt_dir
    tmp_files = list(rpt_dir.glob("*.tmp*"))
    assert len(tmp_files) == 0, f"Temporary file was not cleaned up: {tmp_files}"

