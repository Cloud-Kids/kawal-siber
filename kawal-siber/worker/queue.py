"""
queue.py — SQLite-backed atomic job queue for KAWAL SIBER Security Worker.
Manages atomic state transitions and stores scan results.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

# Ensure app package is importable whether running standalone or inside Docker
_backend_dir = Path(__file__).resolve().parent.parent / "backend"
if _backend_dir.exists() and str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.models import Asset, ScanJob, ScanResult, ScanScope
from worker.config import config

logger = logging.getLogger(__name__)


def create_worker_engine(database_url: Optional[str] = None):
    """Create SQLAlchemy engine with WAL mode and busy timeout for concurrent SQLite access."""
    url = database_url or config.DATABASE_URL
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()

    return engine


def get_worker_sessionmaker(database_url: Optional[str] = None) -> sessionmaker[Session]:
    """Return a sessionmaker bound to worker engine."""
    engine = create_worker_engine(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def claim_next_pending_job(db: Session) -> Optional[ScanJob]:
    """
    Atomically query and claim the oldest PENDING scan job.
    Transitions status to RUNNING in the same transaction.
    """
    stmt = (
        select(ScanJob)
        .where(ScanJob.status == "PENDING")
        .order_by(ScanJob.created_at.asc())
        .limit(1)
        .with_for_update() if db.bind and db.bind.dialect.name != "sqlite" else
        select(ScanJob)
        .where(ScanJob.status == "PENDING")
        .order_by(ScanJob.created_at.asc())
        .limit(1)
    )

    job = db.execute(stmt).scalar_one_or_none()
    if job is None:
        return None

    job.status = "RUNNING"
    job.started_at = datetime.now(timezone.utc)
    job.attempts += 1
    db.commit()
    db.refresh(job)

    logger.info("Claimed scan job id=%d for asset_id=%d", job.id, job.asset_id)
    return job


def mark_job_completed(
    db: Session,
    job_id: int,
    findings: Dict[str, Any],
    resolved_ip: str,
    scanner_version: Optional[str] = None,
) -> None:
    """
    Record scan findings and mark job as COMPLETED.
    Updates asset availability status based on verifiable evidence.
    CRITICAL: Never modifies asset security status (SAFE/UNDER_ATTACK).
    """
    job = db.get(ScanJob, job_id)
    if not job:
        logger.error("Cannot mark non-existent job id=%d as completed", job_id)
        return

    now = datetime.now(timezone.utc)
    job.status = "COMPLETED"
    job.finished_at = now
    job.resolved_ip = resolved_ip
    job.scanner_version = scanner_version

    # Calculate duration
    if findings.get("duration_ms") is not None:
        job.duration_ms = findings["duration_ms"]
    elif job.started_at:
        started = job.started_at if job.started_at.tzinfo else job.started_at.replace(tzinfo=timezone.utc)
        job.duration_ms = int((now - started).total_seconds() * 1000)

    # Persist findings
    ports = findings.get("ports", [])
    has_open_port = False
    has_closed_port = False

    for p in ports:
        result = ScanResult(
            scan_job_id=job.id,
            protocol=p.get("protocol", "tcp"),
            port=p.get("port"),
            state=p.get("state", "unknown"),
            service_name=p.get("service_name"),
            product=p.get("product"),
            version=p.get("version"),
            extra_info=p.get("extra_info"),
            reason=p.get("reason"),
        )
        db.add(result)

        if result.state == "open":
            has_open_port = True
        elif result.state == "closed":
            has_closed_port = True

    # Update asset network availability evidence
    asset = db.get(Asset, job.asset_id)
    if asset:
        asset.last_scanned = now
        if job.duration_ms is not None:
            asset.response_time_ms = float(job.duration_ms)

        if has_open_port or has_closed_port:
            # Active response received over TCP (SYN-ACK or RST) -> Host is UP
            asset.availability_status = "UP"
        # If filtered or timeout: do not mark DOWN automatically
        # Keep asset availability_status as is to avoid false DOWN classifications

    db.commit()
    logger.info("Marked scan job id=%d COMPLETED with %d port findings", job.id, len(ports))


def mark_job_failed(
    db: Session,
    job_id: int,
    error_code: str,
    error_message: str,
    resolved_ip: Optional[str] = None,
) -> None:
    """Record job failure with error code and sanitized detail."""
    job = db.get(ScanJob, job_id)
    if not job:
        logger.error("Cannot mark non-existent job id=%d as failed", job_id)
        return

    now = datetime.now(timezone.utc)
    job.status = "FAILED"
    job.finished_at = now
    job.error_code = error_code
    job.error_message = error_message[:1000]
    if resolved_ip:
        job.resolved_ip = resolved_ip

    if job.started_at:
        started = job.started_at if job.started_at.tzinfo else job.started_at.replace(tzinfo=timezone.utc)
        job.duration_ms = int((now - started).total_seconds() * 1000)

    db.commit()
    logger.warning("Marked scan job id=%d FAILED [%s]: %s", job.id, error_code, error_message)


def claim_next_pending_web_assessment(db: Session):
    """
    Atomically query and claim the oldest PENDING WebAssessment.
    Transitions status to RUNNING in the same transaction.
    """
    from app.models import WebAssessment
    stmt = (
        select(WebAssessment)
        .where(WebAssessment.status == "PENDING")
        .order_by(WebAssessment.created_at.asc())
        .limit(1)
    )
    assessment = db.execute(stmt).scalar_one_or_none()
    if assessment is None:
        return None

    assessment.status = "RUNNING"
    assessment.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assessment)
    logger.info("Claimed WebAssessment id=%d (target_id=%d, profile=%s)", assessment.id, assessment.web_target_id, assessment.assessment_profile)
    return assessment


def claim_next_pending_ai_triage(db: Session):
    """
    Atomically query and claim the oldest PENDING AITriageRun.
    Transitions status to RUNNING in the same transaction.
    """
    from app.models import AITriageRun
    stmt = (
        select(AITriageRun)
        .where(AITriageRun.status == "PENDING")
        .order_by(AITriageRun.created_at.asc())
        .limit(1)
    )
    run = db.execute(stmt).scalar_one_or_none()
    if run is None:
        return None

    run.status = "RUNNING"
    run.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    logger.info("Claimed AITriageRun id=%d for incident_id=%d", run.id, run.incident_id)
    return run


def claim_next_pending_report(db: Session):
    """
    Atomically query and claim the highest-priority PENDING GeneratedReport.
    Orders by job_priority ASC (lower = higher priority) then created_at ASC.
    Transitions status to RUNNING in the same transaction.
    """
    from app.models import GeneratedReport
    stmt = (
        select(GeneratedReport)
        .where(GeneratedReport.generation_status == "PENDING")
        .order_by(GeneratedReport.job_priority.asc(), GeneratedReport.created_at.asc())
        .limit(1)
    )
    report = db.execute(stmt).scalar_one_or_none()
    if report is None:
        return None

    report.generation_status = "RUNNING"
    db.commit()
    db.refresh(report)
    logger.info(
        "Claimed GeneratedReport id=%d (report_id=%s, type=%s, format=%s, priority=%s)",
        report.id, report.report_id, report.report_type, report.format,
        getattr(report, "job_priority", "?"),
    )
    return report


def recover_stale_running_reports(db: Session, timeout_minutes: int = 15) -> int:
    """
    Recover GeneratedReport records that are stuck in RUNNING status.

    A report is considered stale if it has been in RUNNING state for longer
    than timeout_minutes. This can happen if the worker process crashed or
    was killed mid-generation.

    Queries RUNNING reports and normalizes datetime timezone in Python
    to ensure robust comparison across all SQLite/Postgres configurations.

    Returns the number of reports recovered (reset to PENDING).
    """
    from datetime import timedelta
    from app.models import GeneratedReport
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

    stmt = select(GeneratedReport).where(GeneratedReport.generation_status == "RUNNING")
    running = db.execute(stmt).scalars().all()
    if not running:
        return 0

    stale_count = 0
    for report in running:
        c_at = report.created_at
        if c_at is None:
            continue
        if c_at.tzinfo is None:
            c_at = c_at.replace(tzinfo=timezone.utc)
        if c_at < cutoff:
            logger.warning(
                "Recovering stale RUNNING report id=%d (report_id=%s, created_at=%s) → PENDING",
                report.id,
                report.report_id,
                report.created_at,
            )
            report.generation_status = "PENDING"
            report.error_message = f"Recovered from stale RUNNING state after {timeout_minutes}min timeout."
            stale_count += 1

    if stale_count > 0:
        db.commit()
        logger.info("Recovered %d stale RUNNING report(s) to PENDING.", stale_count)
    return stale_count




