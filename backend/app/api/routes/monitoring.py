"""
monitoring.py — PCAP File Import, Suricata Offline Analysis, and Threat Telemetry Statistics.
"""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Asset, Incident, PcapAnalysis, SecurityEvent
from app.schemas import (
    MonitoringStatisticsResponse,
    PcapAnalysisCreate,
    PcapAnalysisResponse,
)
from app.services.eve_processor import stream_eve_json_file
from app.services.incident_correlator import correlate_event_with_assets
from app.services.retention import enforce_event_retention
from app.services.suricata_engine import (
    ALLOWED_PCAP_EXTENSIONS,
    MAX_PCAP_FILE_SIZE,
    PcapValidationError,
    SuricataEngineError,
    execute_suricata_pcap,
    validate_pcap_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring & Threat Detection"])

from app.paths import PCAP_DIR as _PCAP_DIR, SURICATA_LOGS_DIR as _LOGS_DIR


def _process_pcap_job(analysis_id: int, pcap_path: Path, db_session_factory) -> None:
    """Background task to run Suricata and ingest EVE JSON events into SQLite."""
    with db_session_factory() as db:
        analysis = db.get(PcapAnalysis, analysis_id)
        if not analysis:
            return

        analysis.status = "RUNNING"
        analysis.started_at = datetime.now(timezone.utc)
        db.commit()

        run_output_dir = _LOGS_DIR / f"run_{analysis_id}"

        try:
            eve_file = execute_suricata_pcap(
                pcap_path=pcap_path,
                output_dir=run_output_dir,
                timeout_seconds=120,
            )

            # Ingest events from EVE JSON
            event_count = 0
            alert_count = 0
            # Fingerprints are second-precision — distinct EVE records can
            # legitimately share one. Track IDs seen in THIS run as well as
            # the DB, or the second identical record violates the UNIQUE
            # constraint on security_events.event_id and fails the analysis.
            seen_event_ids = set()

            for raw_evt in stream_eve_json_file(eve_file):
                event_id = raw_evt["event_id"]
                if event_id in seen_event_ids:
                    continue
                seen_event_ids.add(event_id)

                # Check for existing event_id to prevent duplicates
                existing = db.execute(
                    select(SecurityEvent.id).where(SecurityEvent.event_id == event_id)
                ).scalar_one_or_none()
                if existing:
                    continue

                event = SecurityEvent(
                    event_id=raw_evt["event_id"],
                    pcap_analysis_id=analysis.id,
                    timestamp=raw_evt["timestamp"],
                    event_type=raw_evt["event_type"],
                    source_ip=raw_evt["source_ip"],
                    destination_ip=raw_evt["destination_ip"],
                    source_port=raw_evt["source_port"],
                    destination_port=raw_evt["destination_port"],
                    protocol=raw_evt["protocol"],
                    signature_id=raw_evt["signature_id"],
                    signature=raw_evt["signature"],
                    category=raw_evt["category"],
                    severity=raw_evt["severity"],
                    confidence=raw_evt["confidence"],
                    raw_event=raw_evt["raw_event"],
                )
                db.add(event)
                event_count += 1
                if event.event_type == "alert":
                    alert_count += 1

                # Incident correlation
                correlate_event_with_assets(event, db)

            analysis.status = "COMPLETED"
            analysis.completed_at = datetime.now(timezone.utc)
            analysis.event_count = event_count
            analysis.alert_count = alert_count
            db.commit()

            # Enforce retention policy periodically
            enforce_event_retention(db)

            logger.info(
                "PCAP analysis %d completed. Ingested %d events (%d alerts).",
                analysis.id,
                event_count,
                alert_count,
            )

        except Exception as exc:
            logger.exception("Failed processing PCAP analysis %d: %s", analysis_id, exc)
            analysis.status = "FAILED"
            analysis.completed_at = datetime.now(timezone.utc)
            analysis.error_message = str(exc)[:1000]
            db.commit()


@router.post(
    "/pcap",
    response_model=PcapAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a PCAP file for offline Suricata analysis",
)
async def create_pcap_analysis(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> PcapAnalysis:
    """
    Submit a PCAP file for offline IDS analysis.
    Supports both:
      1. JSON payload: {"filename": "test.pcap"} (from storage/pcaps/)
      2. Multipart form data: file upload with 'file' field.
    """
    _PCAP_DIR.mkdir(parents=True, exist_ok=True)
    target_path: Path
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded_file = form.get("file")
        if not uploaded_file or not hasattr(uploaded_file, "filename") or not uploaded_file.filename:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Must provide a valid file upload with 'file' form field.",
            )
        clean_name = Path(uploaded_file.filename).name
        ext = Path(clean_name).suffix.lower()
        if ext not in ALLOWED_PCAP_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported file format '{ext}'. Allowed: {sorted(ALLOWED_PCAP_EXTENSIONS)}",
            )
        target_path = _PCAP_DIR / clean_name
        try:
            with open(target_path, "wb") as buffer:
                shutil.copyfileobj(uploaded_file.file, buffer)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save uploaded PCAP: {exc}",
            )
    else:
        # Expect JSON
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid JSON payload.",
            )
        filename_val = body.get("filename") if isinstance(body, dict) else None
        if not filename_val or not isinstance(filename_val, str) or not filename_val.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Field 'filename' is required in JSON payload.",
            )
        clean_name = Path(filename_val.strip()).name
        target_path = _PCAP_DIR / clean_name

    # Validate file security and constraints
    try:
        file_hash, file_size = validate_pcap_file(target_path, allowed_dir=_PCAP_DIR)
    except PcapValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # Create DB entry
    analysis = PcapAnalysis(
        filename=target_path.name,
        file_hash=file_hash,
        file_size_bytes=file_size,
        status="PENDING",
        event_count=0,
        alert_count=0,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Trigger analysis in background
    from app.database import SessionLocal
    background_tasks.add_task(_process_pcap_job, analysis.id, target_path, SessionLocal)

    return analysis


@router.get(
    "/pcap",
    response_model=List[PcapAnalysisResponse],
    summary="List PCAP analysis jobs",
)
def list_pcap_analyses(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[PcapAnalysis]:
    """Retrieve history of all submitted PCAP analyses."""
    stmt = (
        select(PcapAnalysis)
        .order_by(desc(PcapAnalysis.created_at))
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


@router.get(
    "/pcap/{analysis_id}",
    response_model=PcapAnalysisResponse,
    summary="Get details of a specific PCAP analysis",
)
def get_pcap_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
) -> PcapAnalysis:
    """Retrieve execution status and findings count for a PCAP analysis."""
    analysis = db.get(PcapAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PCAP analysis with id={analysis_id} not found.",
        )
    return analysis


@router.get(
    "/statistics",
    response_model=MonitoringStatisticsResponse,
    summary="Get aggregated network threat detection metrics",
)
def get_monitoring_statistics(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve aggregated KPIs, threat distributions, and protocol metrics."""
    total_events = db.execute(select(func.count(SecurityEvent.id))).scalar() or 0
    total_alerts = db.execute(
        select(func.count(SecurityEvent.id)).where(SecurityEvent.event_type == "alert")
    ).scalar() or 0
    total_analyses = db.execute(select(func.count(PcapAnalysis.id))).scalar() or 0

    # Severity distribution
    sev_rows = db.execute(
        select(SecurityEvent.severity, func.count(SecurityEvent.id))
        .group_by(SecurityEvent.severity)
    ).all()

    sev_map_labels = {1: "CRITICAL", 2: "HIGH", 3: "MEDIUM", 4: "LOW"}
    sev_dist = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for s_val, count in sev_rows:
        label = sev_map_labels.get(s_val, "LOW")
        sev_dist[label] = sev_dist.get(label, 0) + count

    # Protocol distribution
    proto_rows = db.execute(
        select(SecurityEvent.protocol, func.count(SecurityEvent.id))
        .where(SecurityEvent.protocol.isnot(None))
        .group_by(SecurityEvent.protocol)
    ).all()
    proto_dist = {str(proto): count for proto, count in proto_rows if proto}

    # Event type distribution
    type_rows = db.execute(
        select(SecurityEvent.event_type, func.count(SecurityEvent.id))
        .group_by(SecurityEvent.event_type)
    ).all()
    type_dist = {str(etype): count for etype, count in type_rows}

    # Top alert signatures
    sig_rows = db.execute(
        select(SecurityEvent.signature, SecurityEvent.category, func.count(SecurityEvent.id))
        .where(SecurityEvent.signature.isnot(None))
        .group_by(SecurityEvent.signature, SecurityEvent.category)
        .order_by(desc(func.count(SecurityEvent.id)))
        .limit(10)
    ).all()

    top_signatures = [
        {"signature": sig, "category": cat, "count": cnt}
        for sig, cat, cnt in sig_rows
    ]

    # Correlated incidents count
    correlated_incidents = db.execute(
        select(func.count(Incident.id)).where(Incident.ai_analysis.ilike("%Suricata%"))
    ).scalar() or 0

    return {
        "total_events": total_events,
        "total_alerts": total_alerts,
        "total_pcap_analyses": total_analyses,
        "severity_distribution": sev_dist,
        "protocol_distribution": proto_dist,
        "event_type_distribution": type_dist,
        "top_signatures": top_signatures,
        "correlated_incidents_count": correlated_incidents,
    }

