"""
API routes for Web Security Assessment & Deep Eye Integration.
Exposes endpoints for web targets, assessments, findings, and telemetry statistics.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.integrations.deep_eye.validator import (
    WebValidationError,
    TargetOutOfScopeError,
    InvalidTargetURLError,
)
from app.models import WebTarget, WebAssessment, WebFinding
from app.schemas import (
    WebTargetCreate,
    WebTargetUpdate,
    WebTargetResponse,
    WebAssessmentCreate,
    WebAssessmentResponse,
    WebFindingResponse,
    WebFindingUpdate,
    WebSecurityStatisticsResponse,
)
from app.services.web_assessment_service import WebAssessmentService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Web Security & Deep Eye"])


# ---------------------------------------------------------------------------
# Web Targets Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/web-targets",
    response_model=List[WebTargetResponse],
    summary="List all registered web targets",
)
def list_web_targets(
    enabled: Optional[bool] = Query(None, description="Filter by enabled state"),
    asset_id: Optional[int] = Query(None, description="Filter by linked asset ID"),
    db: Session = Depends(get_db),
) -> List[WebTarget]:
    stmt = select(WebTarget).order_by(WebTarget.id.desc())
    if enabled is not None:
        stmt = stmt.where(WebTarget.enabled == enabled)
    if asset_id is not None:
        stmt = stmt.where(WebTarget.asset_id == asset_id)
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/web-targets",
    response_model=WebTargetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new authorized web target",
)
def create_web_target(
    payload: WebTargetCreate,
    db: Session = Depends(get_db),
) -> WebTarget:
    service = WebAssessmentService(db)
    try:
        return service.create_web_target(
            name=payload.name,
            target_url=payload.target_url,
            asset_id=payload.asset_id,
            scope_id=payload.scope_id,
            allowed_paths=payload.allowed_paths,
            authorization_reference=payload.authorization_reference,
            enabled=payload.enabled,
        )
    except (TargetOutOfScopeError, InvalidTargetURLError, WebValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/web-targets/{id}",
    response_model=WebTargetResponse,
    summary="Get details of a specific web target",
)
def get_web_target(id: int, db: Session = Depends(get_db)) -> WebTarget:
    target = db.get(WebTarget, id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"WebTarget {id} not found.")
    return target


@router.patch(
    "/web-targets/{id}",
    response_model=WebTargetResponse,
    summary="Update a web target configuration",
)
def update_web_target(
    id: int,
    payload: WebTargetUpdate,
    db: Session = Depends(get_db),
) -> WebTarget:
    target = db.get(WebTarget, id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"WebTarget {id} not found.")

    if payload.name is not None:
        target.name = payload.name.strip()
    if payload.allowed_paths is not None:
        target.allowed_paths = payload.allowed_paths.strip()
    if payload.authorization_reference is not None:
        target.authorization_reference = payload.authorization_reference.strip()
    if payload.enabled is not None:
        target.enabled = payload.enabled

    db.commit()
    db.refresh(target)
    return target


@router.delete(
    "/web-targets/{id}",
    response_model=WebTargetResponse,
    summary="Delete a web target and cascade assessments",
)
def delete_web_target(id: int, db: Session = Depends(get_db)) -> WebTarget:
    target = db.get(WebTarget, id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"WebTarget {id} not found.")
    db.delete(target)
    db.commit()
    return target


# ---------------------------------------------------------------------------
# Web Assessments Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/web-assessments",
    response_model=WebAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enqueue a new web application security assessment",
)
def create_web_assessment(
    payload: WebAssessmentCreate,
    run_immediate: bool = Query(True, description="Execute assessment synchronously (dev/local default)"),
    db: Session = Depends(get_db),
) -> WebAssessment:
    service = WebAssessmentService(db)
    try:
        assessment = service.enqueue_assessment(
            web_target_id=payload.web_target_id,
            assessment_profile=payload.assessment_profile,
        )
        if run_immediate:
            assessment = service.execute_assessment_job(assessment.id)
        return assessment
    except (TargetOutOfScopeError, InvalidTargetURLError, WebValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/web-assessments",
    response_model=List[WebAssessmentResponse],
    summary="List web assessments",
)
def list_web_assessments(
    web_target_id: Optional[int] = Query(None, description="Filter by web target ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
) -> List[WebAssessment]:
    stmt = select(WebAssessment).order_by(WebAssessment.id.desc())
    if web_target_id is not None:
        stmt = stmt.where(WebAssessment.web_target_id == web_target_id)
    if status_filter:
        stmt = stmt.where(WebAssessment.status == status_filter.upper().strip())
    return list(db.execute(stmt).scalars().all())


@router.get(
    "/web-assessments/{id}",
    response_model=WebAssessmentResponse,
    summary="Get assessment details",
)
def get_web_assessment(id: int, db: Session = Depends(get_db)) -> WebAssessment:
    assessment = db.get(WebAssessment, id)
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"WebAssessment {id} not found.")
    return assessment


@router.get(
    "/web-assessments/{id}/findings",
    response_model=List[WebFindingResponse],
    summary="List findings for a specific assessment",
)
def get_assessment_findings(
    id: int,
    db: Session = Depends(get_db),
) -> List[WebFinding]:
    assessment = db.get(WebAssessment, id)
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"WebAssessment {id} not found.")

    stmt = select(WebFinding).where(WebFinding.assessment_id == id).order_by(
        desc(WebFinding.id)
    )
    return list(db.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# Web Findings Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/web-findings",
    response_model=List[WebFindingResponse],
    summary="List all web vulnerability findings with filtering",
)
def list_web_findings(
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, etc.)"),
    finding_status: Optional[str] = Query(None, description="Filter by status (UNVERIFIED, CONFIRMED, etc.)"),
    web_target_id: Optional[int] = Query(None, description="Filter by target ID"),
    vulnerability_type: Optional[str] = Query(None, description="Filter by vulnerability type"),
    search: Optional[str] = Query(None, description="Search keyword in title or description"),
    db: Session = Depends(get_db),
) -> List[WebFinding]:
    stmt = select(WebFinding).order_by(desc(WebFinding.id))

    if severity:
        stmt = stmt.where(WebFinding.severity == severity.upper().strip())
    if finding_status:
        stmt = stmt.where(WebFinding.finding_status == finding_status.upper().strip())
    if web_target_id is not None:
        stmt = stmt.where(WebFinding.web_target_id == web_target_id)
    if vulnerability_type:
        stmt = stmt.where(WebFinding.vulnerability_type == vulnerability_type.upper().strip())
    if search:
        kw = f"%{search.strip()}%"
        stmt = stmt.where((WebFinding.title.ilike(kw)) | (WebFinding.description.ilike(kw)))

    return list(db.execute(stmt).scalars().all())


@router.get(
    "/web-findings/{id}",
    response_model=WebFindingResponse,
    summary="Get details of an individual finding",
)
def get_web_finding(id: int, db: Session = Depends(get_db)) -> WebFinding:
    finding = db.get(WebFinding, id)
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"WebFinding {id} not found.")
    return finding


@router.patch(
    "/web-findings/{id}",
    response_model=WebFindingResponse,
    summary="Update finding triage status",
)
def update_web_finding_status(
    id: int,
    payload: WebFindingUpdate,
    db: Session = Depends(get_db),
) -> WebFinding:
    finding = db.get(WebFinding, id)
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"WebFinding {id} not found.")

    valid_statuses = ("UNVERIFIED", "NEEDS_REVIEW", "CONFIRMED", "FALSE_POSITIVE", "ACCEPTED_RISK")
    st = payload.finding_status.upper().strip()
    if st not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{payload.finding_status}'. Must be one of {valid_statuses}.",
        )

    finding.finding_status = st
    db.commit()
    db.refresh(finding)
    return finding


# ---------------------------------------------------------------------------
# Statistics Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/web-security/statistics",
    response_model=WebSecurityStatisticsResponse,
    summary="Get aggregated web security assessment statistics and metrics",
)
def get_web_security_statistics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    total_targets = db.scalar(select(func.count(WebTarget.id))) or 0
    total_assessments = db.scalar(select(func.count(WebAssessment.id))) or 0
    total_findings = db.scalar(select(func.count(WebFinding.id))) or 0

    crit_cnt = db.scalar(select(func.count(WebFinding.id)).where(WebFinding.severity == "CRITICAL")) or 0
    high_cnt = db.scalar(select(func.count(WebFinding.id)).where(WebFinding.severity == "HIGH")) or 0
    med_cnt = db.scalar(select(func.count(WebFinding.id)).where(WebFinding.severity == "MEDIUM")) or 0
    low_cnt = db.scalar(select(func.count(WebFinding.id)).where(WebFinding.severity == "LOW")) or 0
    info_cnt = db.scalar(select(func.count(WebFinding.id)).where(WebFinding.severity == "INFORMATIONAL")) or 0

    severity_dist = {
        "CRITICAL": crit_cnt,
        "HIGH": high_cnt,
        "MEDIUM": med_cnt,
        "LOW": low_cnt,
        "INFORMATIONAL": info_cnt,
    }

    status_rows = db.execute(
        select(WebFinding.finding_status, func.count(WebFinding.id)).group_by(WebFinding.finding_status)
    ).all()
    status_dist = {row[0]: row[1] for row in status_rows}

    # Top vulnerabilities
    top_vuln_rows = db.execute(
        select(WebFinding.vulnerability_type, func.count(WebFinding.id))
        .group_by(WebFinding.vulnerability_type)
        .order_by(desc(func.count(WebFinding.id)))
        .limit(10)
    ).all()
    top_vulns = [{"type": row[0], "count": row[1]} for row in top_vuln_rows]

    return {
        "total_targets": total_targets,
        "total_assessments": total_assessments,
        "total_findings": total_findings,
        "critical_findings": crit_cnt,
        "high_findings": high_cnt,
        "medium_findings": med_cnt,
        "low_findings": low_cnt,
        "informational_findings": info_cnt,
        "severity_distribution": severity_dist,
        "status_distribution": status_dist,
        "top_vulnerabilities": top_vulns,
    }
