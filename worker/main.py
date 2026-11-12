"""
main.py — Main daemon loop for KAWAL SIBER Security Worker.
Executes single-concurrency authorized port scans and processes findings into SQLite.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

from worker.config import config
from worker.nmap_scanner import get_nmap_version, run_nmap_scan
from worker.queue import (
    claim_next_pending_ai_triage,
    claim_next_pending_job,
    claim_next_pending_report,
    claim_next_pending_web_assessment,
    get_worker_sessionmaker,
    mark_job_completed,
    mark_job_failed,
    recover_stale_running_reports,
)
from worker.scope_validator import (
    ScopeValidationError,
    validate_target_against_scope,
)
from worker.xml_parser import parse_nmap_xml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (worker) %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker")

_shutdown_event = asyncio.Event()


def _handle_shutdown_signal(sig_name: str) -> None:
    logger.info("Received %s signal. Initiating graceful shutdown...", sig_name)
    _shutdown_event.set()


async def process_single_job(job_id: int, db_factory, scanner_version: str) -> None:
    """Process a single claimed scan job through scope re-validation and Nmap execution."""
    with db_factory() as db:
        from app.models import Asset, ScanJob, ScanScope

        job = db.get(ScanJob, job_id)
        if not job:
            return

        asset = db.get(Asset, job.asset_id)
        if not asset:
            mark_job_failed(
                db,
                job.id,
                "ASSET_NOT_FOUND",
                f"Asset id={job.asset_id} no longer exists.",
            )
            return

        # Fetch authorized scan scope
        target_scope: Optional[ScanScope] = None
        if asset.scope_id:
            target_scope = db.get(ScanScope, asset.scope_id)

        if not target_scope:
            # Check if any active scope applies
            from sqlalchemy import select
            active_scopes = db.execute(
                select(ScanScope).where(ScanScope.enabled == True)
            ).scalars().all()

            for s in active_scopes:
                try:
                    validate_target_against_scope(
                        target=asset.target_ip,
                        cidr=s.cidr,
                        enabled=s.enabled,
                        expires_at=s.expires_at,
                    )
                    target_scope = s
                    asset.scope_id = s.id
                    db.commit()
                    break
                except ScopeValidationError:
                    continue

        if not target_scope:
            mark_job_failed(
                db,
                job.id,
                "SCOPE_VIOLATION",
                f"No active authorized scan scope found for target {asset.target_ip}.",
            )
            return

        # Re-verify scope authorization immediately before execution
        resolved_ip: Optional[str] = None
        try:
            resolved_ip = validate_target_against_scope(
                target=asset.target_ip,
                cidr=target_scope.cidr,
                enabled=target_scope.enabled,
                expires_at=target_scope.expires_at,
            )
        except ScopeValidationError as exc:
            mark_job_failed(
                db,
                job.id,
                "SCOPE_VIOLATION",
                f"Authorization rejected: {exc}",
            )
            return

        # Execute fixed Nmap scan
        logger.info(
            "Starting scan for job id=%d asset=%s (%s:%d)",
            job.id,
            asset.name,
            resolved_ip,
            asset.port,
        )

        try:
            xml_raw = await run_nmap_scan(
                resolved_ip=resolved_ip,
                port=asset.port,
                timeout_seconds=config.NMAP_TIMEOUT_SECONDS,
                nmap_bin=config.NMAP_PATH,
                max_bytes=config.MAX_XML_BYTES,
            )
            findings = parse_nmap_xml(xml_raw, max_bytes=config.MAX_XML_BYTES)
            mark_job_completed(
                db=db,
                job_id=job.id,
                findings=findings,
                resolved_ip=resolved_ip,
                scanner_version=findings.get("scanner_version") or scanner_version,
            )
        except TimeoutError as exc:
            mark_job_failed(
                db,
                job.id,
                "TIMEOUT",
                str(exc),
                resolved_ip=resolved_ip,
            )
        except Exception as exc:
            logger.exception("Error scanning job id=%d: %s", job.id, exc)
            mark_job_failed(
                db,
                job.id,
                "NMAP_ERROR",
                str(exc),
                resolved_ip=resolved_ip,
            )


def process_triage_job(run_id: int, db_factory) -> None:
    """Execute AI or rule-based triage analysis for an incident."""
    with db_factory() as db:
        from datetime import datetime, timezone
        from sqlalchemy import select
        from app.models import (
            AITriageRun, Incident, Asset, SecurityEvent, WebFinding, ScanResult,
            IncidentEvidence, IncidentTimelineEvent,
        )

        run = db.get(AITriageRun, run_id)
        if not run:
            return

        incident = db.get(Incident, run.incident_id)
        if not incident:
            run.status = "FAILED"
            run.error_message = f"Incident id={run.incident_id} not found."
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        try:
            from app.services.unified_correlator import UnifiedCorrelationEngine
            from app.services.triage_engine import TriageEngine, IncidentEvidenceAggregator

            # 1. Run or refresh correlation to ensure all evidence is linked
            correlator = UnifiedCorrelationEngine(db)
            correlator.correlate_incident(incident.id)

            # 2. Build aggregator
            asset = db.get(Asset, incident.asset_id) if incident.asset_id else None
            incident_data = {
                "id": incident.id,
                "asset_name": asset.name if asset else "Unknown Asset",
                "asset_ip": asset.target_ip if asset else "0.0.0.0",
                "severity": incident.severity,
                "attack_type": incident.attack_type,
                "lifecycle_status": incident.lifecycle_status,
                "source_ip": incident.source_ip,
                "timestamp": incident.timestamp.isoformat() if incident.timestamp else "",
            }

            aggregator = IncidentEvidenceAggregator(incident_data)

            evidence_rows = db.execute(
                select(IncidentEvidence).where(IncidentEvidence.incident_id == incident.id)
            ).scalars().all()

            for ev in evidence_rows:
                if ev.source_type == "SURICATA_EVENT" and ev.source_record_id:
                    sec_ev = db.get(SecurityEvent, ev.source_record_id)
                    if sec_ev:
                        aggregator.add_suricata_event({
                            "event_id": sec_ev.event_id,
                            "signature": sec_ev.signature,
                            "category": sec_ev.category,
                            "severity": sec_ev.severity,
                            "source_ip": sec_ev.source_ip,
                            "destination_ip": sec_ev.destination_ip,
                            "timestamp": sec_ev.timestamp,
                        })
                elif ev.source_type == "WEB_FINDING" and ev.source_record_id:
                    wf = db.get(WebFinding, ev.source_record_id)
                    if wf:
                        aggregator.add_web_finding({
                            "vulnerability_type": wf.vulnerability_type,
                            "severity": wf.severity,
                            "affected_url": wf.affected_url,
                            "title": wf.title,
                        })
                elif ev.source_type == "NMAP_RESULT" and ev.source_record_id:
                    nr = db.get(ScanResult, ev.source_record_id)
                    if nr:
                        aggregator.add_nmap_result({
                            "port": nr.port,
                            "state": nr.state,
                            "service_name": nr.service_name,
                        })

            # 3. Run triage engine
            engine = TriageEngine()
            result = engine.run_triage(incident_data, aggregator)

            data_blob = aggregator.build_data_blob()
            run.input_fingerprint = aggregator.build_input_fingerprint(data_blob)
            run.result_json = result.model_dump_json()
            run.confidence_score = result.confidence
            run.provider = result.provider
            run.model_name = result.model_name
            run.completed_at = datetime.now(timezone.utc)
            run.status = "REQUIRES_REVIEW" if result.risk_level in ("CRITICAL", "HIGH") else "COMPLETED"

            # Update incident ai_analysis summary (informative only, no auto-mitigation!)
            incident.ai_analysis = (
                f"[{result.provider.upper()}] Risk: {result.risk_level} (Score: {result.priority_score}/100, "
                f"Conf: {int(result.confidence * 100)}%). "
                f"{result.attack_explanation}"
            )

            # Add timeline event
            tl = IncidentTimelineEvent(
                incident_id=incident.id,
                event_type="TRIAGE_COMPLETED",
                description=(
                    f"Triage completed by {result.provider} ({result.model_name}). "
                    f"Risk: {result.risk_level}, Score: {result.priority_score}. "
                    f"Operator review recommended."
                ),
                source_type=None,
                source_record_id=None,
                timestamp=datetime.now(timezone.utc),
            )
            db.add(tl)
            db.commit()
            logger.info("Successfully completed AI triage run id=%d for incident id=%d", run.id, incident.id)
        except Exception as exc:
            logger.exception("Error executing triage run id=%d: %s", run.id, exc)
            run.status = "FAILED"
            run.error_message = str(exc)[:1000]
            run.completed_at = datetime.now(timezone.utc)
            db.commit()


def process_report_job(report_db_id: int, db_factory) -> None:
    """Execute report generation for a claimed GeneratedReport record.

    Wraps the ReportingEngine call. Retry logic is handled inside the engine itself.
    """
    with db_factory() as db:
        from app.models import GeneratedReport

        report = db.get(GeneratedReport, report_db_id)
        if not report:
            logger.error("GeneratedReport id=%d not found", report_db_id)
            return

        try:
            from app.reporting.engine import ReportingEngine
            engine = ReportingEngine(db)
            engine.process_report_job(report.report_id)
            logger.info("Successfully completed report generation for %s (id=%d)", report.report_id, report.id)
        except Exception as exc:
            logger.exception("Failed to generate report id=%d (%s): %s", report.id, report.report_id, exc)
            # Engine already handles retry/failure — only update if engine did not persist
            try:
                db.refresh(report)
                if report.generation_status == "RUNNING":
                    report.generation_status = "FAILED"
                    report.error_message = str(exc)[:1000]
                    from datetime import datetime, timezone
                    report.completed_at = datetime.now(timezone.utc)
                    db.commit()
            except Exception:
                pass


async def run_worker() -> None:
    """Main worker entry point and polling loop."""
    logger.info("Initializing KAWAL SIBER Security Worker...")
    logger.info("Database URL: %s", config.DATABASE_URL)
    logger.info("Scan Enabled: %s", config.SCAN_ENABLED)
    logger.info("Max XML Limit: %d bytes", config.MAX_XML_BYTES)
    logger.info("Nmap Timeout: %ds", config.NMAP_TIMEOUT_SECONDS)

    # Check Nmap installation
    scanner_version = "Unknown"
    try:
        scanner_version = await get_nmap_version(config.NMAP_PATH)
        logger.info("Nmap detected: %s", scanner_version)
    except Exception as exc:
        logger.warning(
            "Nmap binary check failed (%s). If running in unit test or container "
            "without nmap, scans will fail when invoked.",
            exc,
        )

    if not config.SCAN_ENABLED:
        logger.warning(
            "CRITICAL: SCAN_ENABLED is set to FALSE. Worker will not process any scan jobs "
            "until explicitly enabled in environment (SCAN_ENABLED=true)."
        )

    # Validate optional runtime dependencies used by lazy job processors.
    # Missing packages degrade specific job types to FAILED (not crash loops),
    # but operators should see the gap at startup.
    for module_name, job_type in (
        ("reportlab", "PDF report generation"),
        ("pypdf", "PDF report parsing"),
        ("httpx", "web assessments / AI provider HTTP"),
        ("yaml", "Deep Eye safe-config generation"),
    ):
        try:
            __import__(module_name)
        except ImportError:
            logger.error(
                "Missing optional dependency '%s' — %s jobs will fail until installed.",
                module_name, job_type,
            )

    db_factory = get_worker_sessionmaker()

    # Recover any report jobs that were left in RUNNING state from a previous crash
    try:
        with db_factory() as db:
            recovered = recover_stale_running_reports(db, timeout_minutes=15)
            if recovered:
                logger.warning("Recovered %d stale RUNNING report job(s) to PENDING on startup.", recovered)
    except Exception as exc:
        logger.warning("Stale report recovery failed (non-fatal): %s", exc)

    # Register OS signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda s=sig: _handle_shutdown_signal(s.name))
        except (NotImplementedError, AttributeError):
            # Windows signal handlers fall back to signal.signal
            signal.signal(sig, lambda s, f: _shutdown_event.set())

    logger.info("Worker polling loop active. Waiting for authorized jobs...")

    while not _shutdown_event.is_set():
        if not config.SCAN_ENABLED:
            try:
                await asyncio.wait_for(_shutdown_event.wait(), timeout=config.POLL_INTERVAL_SECONDS)
                break
            except asyncio.TimeoutError:
                continue

        # Claim next pending job atomically
        claimed_job_id: Optional[int] = None
        with db_factory() as db:
            job = claim_next_pending_job(db)
            if job:
                claimed_job_id = job.id

        # Claim next pending web assessment if no nmap job
        claimed_assessment_id: Optional[int] = None
        if claimed_job_id is None:
            with db_factory() as db:
                assessment = claim_next_pending_web_assessment(db)
                if assessment:
                    claimed_assessment_id = assessment.id

        # Claim next pending AI triage if no web assessment or nmap job
        claimed_triage_id: Optional[int] = None
        if claimed_job_id is None and claimed_assessment_id is None:
            with db_factory() as db:
                triage_run = claim_next_pending_ai_triage(db)
                if triage_run:
                    claimed_triage_id = triage_run.id

        # Claim next pending report if no triage, web assessment, or nmap job
        claimed_report_id: Optional[int] = None
        if claimed_job_id is None and claimed_assessment_id is None and claimed_triage_id is None:
            with db_factory() as db:
                report = claim_next_pending_report(db)
                if report:
                    claimed_report_id = report.id

        if claimed_job_id is not None:
            await process_single_job(claimed_job_id, db_factory, scanner_version)
        elif claimed_assessment_id is not None:
            try:
                with db_factory() as db:
                    from app.services.web_assessment_service import WebAssessmentService
                    svc = WebAssessmentService(db)
                    svc.execute_assessment_job(claimed_assessment_id)
            except Exception as exc:
                logger.exception("Failed to execute claimed web assessment %d: %s", claimed_assessment_id, exc)
                try:
                    with db_factory() as db:
                        from app.models import WebAssessment
                        from datetime import datetime, timezone
                        a = db.get(WebAssessment, claimed_assessment_id)
                        if a and a.status == "RUNNING":
                            a.status = "FAILED"
                            a.error_message = f"Worker execution error: {type(exc).__name__}"
                            a.completed_at = datetime.now(timezone.utc)
                            db.commit()
                except Exception:
                    pass
        elif claimed_triage_id is not None:
            try:
                process_triage_job(claimed_triage_id, db_factory)
            except Exception as exc:
                logger.exception("Failed to execute claimed AI triage %d: %s", claimed_triage_id, exc)
        elif claimed_report_id is not None:
            try:
                # Run report generation in executor thread with timeout
                # Default timeout: 120 seconds to prevent indefinite blocking
                REPORT_JOB_TIMEOUT_SECONDS = int(os.environ.get("REPORT_JOB_TIMEOUT_SECONDS", "120"))
                loop = asyncio.get_running_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda rid=claimed_report_id: process_report_job(rid, db_factory),
                    ),
                    timeout=REPORT_JOB_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "Report generation job id=%d timed out after %ds. Marking FAILED.",
                    claimed_report_id,
                    REPORT_JOB_TIMEOUT_SECONDS,
                )
                try:
                    with db_factory() as db:
                        from app.models import GeneratedReport
                        from datetime import datetime, timezone
                        r = db.get(GeneratedReport, claimed_report_id)
                        if r and r.generation_status == "RUNNING":
                            r.generation_status = "FAILED"
                            r.error_message = f"Worker timeout after {REPORT_JOB_TIMEOUT_SECONDS}s"
                            r.completed_at = datetime.now(timezone.utc)
                            db.commit()
                except Exception:
                    pass
            except Exception as exc:
                logger.exception("Failed to execute claimed report %d: %s", claimed_report_id, exc)
        else:
            try:
                await asyncio.wait_for(_shutdown_event.wait(), timeout=config.POLL_INTERVAL_SECONDS)
                break
            except asyncio.TimeoutError:
                pass

    logger.info("Worker terminated gracefully.")


def main() -> None:
    try:
        asyncio.run(run_worker())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped.")


if __name__ == "__main__":
    main()

