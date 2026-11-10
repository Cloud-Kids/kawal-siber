"""
incidents.py — CRUD routes for security incidents in KAWAL SIBER.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dependencies import CommonQueryParams, get_db
from app.models import Asset, Incident
from app.schemas import (
    IncidentCreate,
    IncidentResponse,
    IncidentUpdate,
    PaginatedIncidents,
    Severity,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/incidents", tags=["Incidents"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_incident_or_404(incident_id: int, db: Session) -> Incident:
    """Return the Incident row or raise HTTP 404."""
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with id={incident_id} not found.",
        )
    return incident


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedIncidents, include_in_schema=False)
@router.get(
    "/",
    response_model=PaginatedIncidents,
    summary="List incidents (paginated)",
)
def list_incidents(
    asset_id: Optional[int] = Query(
        default=None, description="Filter by asset ID"
    ),
    severity: Optional[Severity] = Query(
        default=None, description="Filter by severity level"
    ),
    is_mitigated: Optional[bool] = Query(
        default=None, description="Filter by mitigation status"
    ),
    pagination: CommonQueryParams = Depends(),
    db: Session = Depends(get_db),
) -> PaginatedIncidents:
    """Return a paginated list of incidents with optional filters."""
    base_stmt = select(Incident)
    count_stmt = select(func.count()).select_from(Incident)

    if asset_id is not None:
        base_stmt = base_stmt.where(Incident.asset_id == asset_id)
        count_stmt = count_stmt.where(Incident.asset_id == asset_id)
    if severity is not None:
        base_stmt = base_stmt.where(Incident.severity == severity.value)
        count_stmt = count_stmt.where(Incident.severity == severity.value)
    if is_mitigated is not None:
        base_stmt = base_stmt.where(Incident.is_mitigated == is_mitigated)
        count_stmt = count_stmt.where(Incident.is_mitigated == is_mitigated)

    total: int = db.execute(count_stmt).scalar_one()

    items = list(
        db.execute(
            base_stmt
            .order_by(Incident.timestamp.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )

    return PaginatedIncidents(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post(
    "/",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create incident",
)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
) -> Incident:
    """Create a new security incident.  Validates that the referenced asset exists."""
    # Verify asset exists
    asset = db.get(Asset, payload.asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with id={payload.asset_id} not found.",
        )

    incident = Incident(
        asset_id=payload.asset_id,
        source_ip=payload.source_ip,
        attack_type=payload.attack_type.value,
        payload=payload.payload,
        severity=payload.severity.value,
        ai_analysis=payload.ai_analysis,
        is_mitigated=False,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    logger.info(
        "Created incident id=%d asset_id=%d severity=%s",
        incident.id,
        incident.asset_id,
        incident.severity,
    )
    return incident


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get incident by ID",
)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
) -> Incident:
    """Retrieve a single incident by its primary key."""
    return _get_incident_or_404(incident_id, db)


@router.patch(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Update incident mitigation status / AI analysis",
)
def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: Session = Depends(get_db),
) -> Incident:
    """
    Partially update an incident.
    Only ``is_mitigated`` and ``ai_analysis`` may be modified.
    """
    incident = _get_incident_or_404(incident_id, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(incident, field, value)

    db.commit()
    db.refresh(incident)
    logger.info(
        "Updated incident id=%d fields=%s", incident.id, list(update_data.keys())
    )
    return incident
