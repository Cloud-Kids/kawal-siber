"""
incident_intelligence.py — Phase 5 AI Triage & Incident Intelligence API Routes.

Endpoints:
  GET  /api/v1/incident-intelligence/overview    — statistics overview
  GET  /api/v1/ai/health                          — AI subsystem health
  POST /api/v1/incidents/{id}/triage             — enqueue triage run
  GET  /api/v1/incidents/{id}/triage             — get latest triage result
  GET  /api/v1/incidents/{id}/evidence           — list correlated evidence
  GET  /api/v1/incidents/{id}/timeline           — incident timeline events
  POST /api/v1/incidents/{id}/correlate          — run correlation engine
  PATCH /api/v1/incidents/{id}/status            — lifecycle status update

SECURITY INVARIANTS:
  - AI never automatically mitigates — it only recommends.
  - Operator must approve all lifecycle transitions.
  - Triage runs are PENDING until worker processes them.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import (
    AITriageRun,
    Asset,
    Incident,
    IncidentEvidence,
    IncidentTimelineEvent,
    SecurityEvent,
    WebFinding,
)
from app.schemas import (
    AIHealthResponse,
    AITriageRunResponse,
    IncidentDetailResponse,
    IncidentEvidenceResponse,
    IncidentIntelligenceOverview,
    IncidentLifecycleUpdate,
    IncidentTimelineEventResponse,
)

logger = logging.getLogger(__name__)

# Two routers: one for /incident-intelligence, one extends /incidents
intelligence_router = APIRouter(prefix="/incident-intelligence", tags=["Incident Intelligence"])
ai_router = APIRouter(prefix="/ai", tags=["AI Health"])
incident_ext_router = APIRouter(prefix="/incidents", tags=["Incident Intelligence"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_incident_or_404(incident_id: int, db: Session) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident id={incident_id} not found.",
        )
    return incident


# ---------------------------------------------------------------------------
# AI Health
# ---------------------------------------------------------------------------

@ai_router.get(
    "/health",
    response_model=AIHealthResponse,
    summary="AI subsystem health check",
)
def get_ai_health() -> AIHealthResponse:
    """Check whether Ollama is running and what AI provider is active."""
    from app.services.ai_provider import get_ai_health
    health = get_ai_health()
    return AIHealthResponse(**health)


# ---------------------------------------------------------------------------
# Intelligence Overview
# ---------------------------------------------------------------------------

@intelligence_router.get(
    "/overview",
    response_model=IncidentIntelligenceOverview,
    summary="Get incident intelligence statistics overview",
)
def get_intelligence_overview(db: Session = Depends(get_db)) -> IncidentIntelligenceOverview:
    """Return aggregated statistics for the AI Intelligence Center dashboard."""
    from app.services.ai_provider import get_ai_health

    # Incident counts
    total_incidents = db.execute(select(func.count()).select_from(Incident)).scalar_one()
    open_incidents = db.execute(
        select(func.count()).select_from(Incident).where(
            Incident.lifecycle_status.in_(["OPEN", "ACKNOWLEDGED", "INVESTIGATING"])
        )
    ).scalar_one()
    critical_incidents = db.execute(
        select(func.count()).select_from(Incident).where(Incident.severity == "CRITICAL")
    ).scalar_one()
    high_incidents = db.execute(
        select(func.count()).select_from(Incident).where(Incident.severity == "HIGH")
    ).scalar_one()

    # Triage stats
    incidents_with_triage = db.execute(
        select(func.count(func.distinct(AITriageRun.incident_id))).select_from(AITriageRun)
    ).scalar_one()
    pending_triage = db.execute(
        select(func.count()).select_from(AITriageRun).where(
            AITriageRun.status.in_(["PENDING", "RUNNING"])
        )
    ).scalar_one()
    completed_triage = db.execute(
        select(func.count()).select_from(AITriageRun).where(AITriageRun.status == "COMPLETED")
    ).scalar_one()
    failed_triage = db.execute(
        select(func.count()).select_from(AITriageRun).where(AITriageRun.status == "FAILED")
    ).scalar_one()

    # Evidence stats
    total_evidence = db.execute(select(func.count()).select_from(IncidentEvidence)).scalar_one()
    suricata_ev = db.execute(
        select(func.count()).select_from(IncidentEvidence).where(
            IncidentEvidence.source_type == "SURICATA_EVENT"
        )
    ).scalar_one()
    web_ev = db.execute(
        select(func.count()).select_from(IncidentEvidence).where(
            IncidentEvidence.source_type == "WEB_FINDING"
        )
    ).scalar_one()
    nmap_ev = db.execute(
        select(func.count()).select_from(IncidentEvidence).where(
            IncidentEvidence.source_type == "NMAP_RESULT"
        )
    ).scalar_one()

    # Distributions
    from sqlalchemy import case

    lifecycle_rows = db.execute(
        select(Incident.lifecycle_status, func.count().label("cnt"))
        .group_by(Incident.lifecycle_status)
    ).all()
    lifecycle_dist = {r.lifecycle_status: r.cnt for r in lifecycle_rows}

    severity_rows = db.execute(
        select(Incident.severity, func.count().label("cnt"))
        .group_by(Incident.severity)
    ).all()
    severity_dist = {r.severity: r.cnt for r in severity_rows}

    attack_rows = db.execute(
        select(Incident.attack_type, func.count().label("cnt"))
        .group_by(Incident.attack_type)
    ).all()
    attack_dist = {r.attack_type: r.cnt for r in attack_rows}

    health = get_ai_health()

    return IncidentIntelligenceOverview(
        total_incidents=total_incidents,
        open_incidents=open_incidents,
        critical_incidents=critical_incidents,
        high_incidents=high_incidents,
        incidents_with_triage=incidents_with_triage,
        pending_triage=pending_triage,
        completed_triage=completed_triage,
        failed_triage=failed_triage,
        total_evidence_items=total_evidence,
        suricata_evidence=suricata_ev,
        web_finding_evidence=web_ev,
        nmap_evidence=nmap_ev,
        ai_provider_status=health["active_provider"],
        lifecycle_distribution=lifecycle_dist,
        severity_distribution=severity_dist,
        attack_type_distribution=attack_dist,
    )


# ---------------------------------------------------------------------------
# Incident Detail (extended)
# ---------------------------------------------------------------------------

@incident_ext_router.get(
    "/{incident_id}/detail",
    response_model=IncidentDetailResponse,
    summary="Get extended incident detail with triage, evidence, and timeline",
)
def get_incident_detail(
    incident_id: int,
    db: Session = Depends(get_db),
) -> IncidentDetailResponse:
    """Return full incident detail including triage runs, evidence, and timeline."""
    incident = _get_incident_or_404(incident_id, db)

    triage_runs = list(
        db.execute(
            select(AITriageRun)
            .where(AITriageRun.incident_id == incident_id)
            .order_by(AITriageRun.created_at.desc())
        ).scalars().all()
    )
    evidence_items = list(
        db.execute(
            select(IncidentEvidence)
            .where(IncidentEvidence.incident_id == incident_id)
            .order_by(IncidentEvidence.created_at.desc())
        ).scalars().all()
    )
    timeline = list(
        db.execute(
            select(IncidentTimelineEvent)
            .where(IncidentTimelineEvent.incident_id == incident_id)
            .order_by(IncidentTimelineEvent.timestamp.asc())
        ).scalars().all()
    )

    return IncidentDetailResponse(
        id=incident.id,
        asset_id=incident.asset_id,
        timestamp=incident.timestamp,
        source_ip=incident.source_ip,
        attack_type=incident.attack_type,
        payload=incident.payload,
        severity=incident.severity,
        ai_analysis=incident.ai_analysis,
        is_mitigated=incident.is_mitigated,
        lifecycle_status=incident.lifecycle_status,
        acknowledged_at=incident.acknowledged_at,
        investigated_at=incident.investigated_at,
        resolved_at=incident.resolved_at,
        resolution_notes=incident.resolution_notes,
        triage_runs=[AITriageRunResponse.model_validate(tr) for tr in triage_runs],
        evidence_items=[IncidentEvidenceResponse.model_validate(ev) for ev in evidence_items],
        timeline_events=[IncidentTimelineEventResponse.model_validate(te) for te in timeline],
    )


# ---------------------------------------------------------------------------
# Triage Routes
# ---------------------------------------------------------------------------

@incident_ext_router.post(
    "/{incident_id}/triage",
    response_model=AITriageRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request AI triage analysis for an incident",
)
def request_triage(
    incident_id: int,
    db: Session = Depends(get_db),
) -> AITriageRunResponse:
    """
    Enqueue a new AI triage run for the incident.
    The worker will pick it up and run deterministic + AI analysis.
    Operator must review and approve any recommendations.
    """
    incident = _get_incident_or_404(incident_id, db)

    # Check for already-pending or running triage
    existing = db.execute(
        select(AITriageRun).where(
            AITriageRun.incident_id == incident_id,
            AITriageRun.status.in_(["PENDING", "RUNNING"]),
        )
    ).scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A triage run (id={existing.id}) is already PENDING or RUNNING for this incident.",
        )

    from app.services.ai_provider import get_ai_provider
    provider = get_ai_provider()

    triage_run = AITriageRun(
        incident_id=incident_id,
        provider=provider.provider_name,
        model_name=provider.model_name,
        prompt_version="v1",
        status="PENDING",
    )
    db.add(triage_run)
    db.commit()
    db.refresh(triage_run)

    # Add timeline event
    timeline_event = IncidentTimelineEvent(
        incident_id=incident_id,
        event_type="TRIAGE_REQUESTED",
        description=f"AI triage run requested (provider={provider.provider_name}).",
        source_type=None,
        source_record_id=None,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(timeline_event)
    db.commit()

    logger.info("Triage run id=%d created for incident id=%d", triage_run.id, incident_id)
    return AITriageRunResponse.model_validate(triage_run)


@incident_ext_router.get(
    "/{incident_id}/triage",
    response_model=List[AITriageRunResponse],
    summary="Get all triage runs for an incident",
)
def get_triage_runs(
    incident_id: int,
    db: Session = Depends(get_db),
) -> List[AITriageRunResponse]:
    """Return all triage runs for the incident, most recent first."""
    _get_incident_or_404(incident_id, db)
    runs = list(
        db.execute(
            select(AITriageRun)
            .where(AITriageRun.incident_id == incident_id)
            .order_by(AITriageRun.created_at.desc())
        ).scalars().all()
    )
    return [AITriageRunResponse.model_validate(r) for r in runs]


# ---------------------------------------------------------------------------
# Evidence Routes
# ---------------------------------------------------------------------------

@incident_ext_router.get(
    "/{incident_id}/evidence",
    response_model=List[IncidentEvidenceResponse],
    summary="Get correlated evidence for an incident",
)
def get_incident_evidence(
    incident_id: int,
    db: Session = Depends(get_db),
) -> List[IncidentEvidenceResponse]:
    """Return all correlated evidence items for the incident."""
    _get_incident_or_404(incident_id, db)
    items = list(
        db.execute(
            select(IncidentEvidence)
            .where(IncidentEvidence.incident_id == incident_id)
            .order_by(IncidentEvidence.created_at.desc())
        ).scalars().all()
    )
    return [IncidentEvidenceResponse.model_validate(ev) for ev in items]


# ---------------------------------------------------------------------------
# Timeline Routes
# ---------------------------------------------------------------------------

@incident_ext_router.get(
    "/{incident_id}/timeline",
    response_model=List[IncidentTimelineEventResponse],
    summary="Get incident timeline events",
)
def get_incident_timeline(
    incident_id: int,
    db: Session = Depends(get_db),
) -> List[IncidentTimelineEventResponse]:
    """Return the ordered timeline of events for the incident."""
    _get_incident_or_404(incident_id, db)
    events = list(
        db.execute(
            select(IncidentTimelineEvent)
            .where(IncidentTimelineEvent.incident_id == incident_id)
            .order_by(IncidentTimelineEvent.timestamp.asc())
        ).scalars().all()
    )
    return [IncidentTimelineEventResponse.model_validate(ev) for ev in events]


# ---------------------------------------------------------------------------
# Correlation Route
# ---------------------------------------------------------------------------

@incident_ext_router.post(
    "/{incident_id}/correlate",
    summary="Run unified correlation engine for an incident",
)
def correlate_incident(
    incident_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Run the unified correlation engine to find related evidence from
    Suricata, Deep Eye, and Nmap data sources.
    """
    _get_incident_or_404(incident_id, db)

    from app.services.unified_correlator import UnifiedCorrelationEngine
    engine = UnifiedCorrelationEngine(db)
    try:
        result = engine.correlate_incident(incident_id)
        db.commit()
        return {
            "incident_id": result.incident_id,
            "suricata_matches": result.suricata_matches,
            "web_finding_matches": result.web_finding_matches,
            "nmap_matches": result.nmap_matches,
            "evidence_created": result.evidence_created,
            "repeated_occurrences": result.repeated_occurrences,
            "timeline_events_created": result.timeline_events_created,
            "threat_severity": result.threat_severity,
            "correlation_strength": result.correlation_strength,
            "ai_confidence": result.ai_confidence,
            "confidence_score": result.confidence_score,
            "correlation_notes": result.correlation_notes,
        }
    except Exception as exc:
        logger.exception("Correlation failed for incident id=%d: %s", incident_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Correlation engine failed. See server logs.",
        )


# ---------------------------------------------------------------------------
# Lifecycle Status Update (Operator-driven only — AI never calls this)
# ---------------------------------------------------------------------------

_VALID_TRANSITIONS = {
    "OPEN": {"ACKNOWLEDGED", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"},
    "ACKNOWLEDGED": {"INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"},
    "INVESTIGATING": {"MITIGATED", "RESOLVED", "FALSE_POSITIVE"},
    "MITIGATED": {"RESOLVED", "FALSE_POSITIVE"},
    "RESOLVED": {"OPEN"},  # allow re-open
    "FALSE_POSITIVE": {"OPEN"},  # allow re-open
}


@incident_ext_router.patch(
    "/{incident_id}/status",
    response_model=dict,
    summary="Update incident lifecycle status (operator approval required)",
)
def update_incident_status(
    incident_id: int,
    payload: IncidentLifecycleUpdate,
    db: Session = Depends(get_db),
) -> dict:
    """
    Operator-driven lifecycle status transition.
    AI recommendations must be approved here by a human operator.
    Invalid transitions are rejected.
    """
    incident = _get_incident_or_404(incident_id, db)

    current = incident.lifecycle_status
    new_status = payload.new_status.value

    allowed = _VALID_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Cannot transition from {current!r} to {new_status!r}. "
                f"Allowed transitions: {sorted(allowed)}"
            ),
        )

    now = datetime.now(timezone.utc)
    incident.lifecycle_status = new_status

    if new_status == "ACKNOWLEDGED":
        incident.acknowledged_at = now
    elif new_status == "INVESTIGATING":
        incident.investigated_at = now
    elif new_status in ("RESOLVED", "FALSE_POSITIVE", "MITIGATED"):
        incident.resolved_at = now
        if payload.resolution_notes:
            incident.resolution_notes = payload.resolution_notes
        if new_status in ("RESOLVED", "FALSE_POSITIVE"):
            incident.is_mitigated = True

    # Record in timeline
    description = (
        f"Lifecycle status changed: {current} → {new_status}."
        + (f" Reason: {payload.reason}" if payload.reason else "")
    )
    timeline_event = IncidentTimelineEvent(
        incident_id=incident_id,
        event_type="STATUS_CHANGED",
        description=description[:2000],
        source_type=None,
        source_record_id=None,
        timestamp=now,
    )
    db.add(timeline_event)
    db.commit()
    db.refresh(incident)

    logger.info(
        "Incident id=%d lifecycle: %s → %s",
        incident_id,
        current,
        new_status,
    )
    return {
        "incident_id": incident.id,
        "previous_status": current,
        "new_status": new_status,
        "timestamp": now.isoformat(),
    }

