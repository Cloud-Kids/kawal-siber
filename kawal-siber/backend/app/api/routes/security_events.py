"""
security_events.py — Security Events and Alerts Retrieval API routes for KAWAL SIBER.
Provides filtered, paginated access to Suricata IDS telemetry and high-priority alerts.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import SecurityEvent
from app.schemas import PaginatedSecurityEvents, SecurityEventResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Security Events & Alerts"])


@router.get(
    "/security-events",
    response_model=PaginatedSecurityEvents,
    summary="List security telemetry events with filtering",
)
def list_security_events(
    event_type: Optional[str] = Query(default=None, description="Filter by event_type (alert, flow, dns, http, tls, anomaly)"),
    asset_id: Optional[int] = Query(default=None, description="Filter by correlated asset ID"),
    severity: Optional[int] = Query(default=None, ge=1, le=4, description="Filter by severity (1=Critical, 2=High, 3=Medium, 4=Low)"),
    protocol: Optional[str] = Query(default=None, description="Filter by protocol (TCP, UDP, ICMP)"),
    pcap_analysis_id: Optional[int] = Query(default=None, description="Filter by originating PCAP analysis ID"),
    search: Optional[str] = Query(default=None, description="Search in signature, IPs, or category"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> PaginatedSecurityEvents:
    """Retrieve paginated security events matching specified telemetry filters."""
    stmt = select(SecurityEvent)

    if isinstance(event_type, str) and event_type:
        stmt = stmt.where(SecurityEvent.event_type == event_type.lower())
    if asset_id is not None:
        stmt = stmt.where(SecurityEvent.asset_id == asset_id)
    if severity is not None:
        stmt = stmt.where(SecurityEvent.severity == severity)
    if isinstance(protocol, str) and protocol:
        stmt = stmt.where(SecurityEvent.protocol == protocol.upper())
    if pcap_analysis_id is not None:
        stmt = stmt.where(SecurityEvent.pcap_analysis_id == pcap_analysis_id)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                SecurityEvent.signature.ilike(term),
                SecurityEvent.category.ilike(term),
                SecurityEvent.source_ip.ilike(term),
                SecurityEvent.destination_ip.ilike(term),
            )
        )

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar() or 0

    # Paginate and order by newest first
    offset = (page - 1) * page_size
    stmt = stmt.order_by(desc(SecurityEvent.timestamp)).offset(offset).limit(page_size)
    items = list(db.execute(stmt).scalars().all())

    return PaginatedSecurityEvents(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/security-alerts",
    response_model=PaginatedSecurityEvents,
    summary="List high-priority security alerts",
)
def list_security_alerts(
    asset_id: Optional[int] = Query(default=None),
    severity: Optional[int] = Query(default=None, ge=1, le=4),
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> PaginatedSecurityEvents:
    """Convenience endpoint dedicated exclusively to actionable IDS alerts."""
    return list_security_events(
        event_type="alert",
        asset_id=asset_id,
        severity=severity,
        protocol=None,
        pcap_analysis_id=None,
        search=search,
        page=page,
        page_size=page_size,
        db=db,
    )


@router.get(
    "/security-events/{event_id}",
    response_model=SecurityEventResponse,
    summary="Get details of a security event",
)
def get_security_event(
    event_id: str,
    db: Session = Depends(get_db),
) -> SecurityEvent:
    """Retrieve full details of a single security event by primary key ID or UUID event_id."""
    stmt = select(SecurityEvent)
    if event_id.isdigit():
        stmt = stmt.where(or_(SecurityEvent.id == int(event_id), SecurityEvent.event_id == event_id))
    else:
        stmt = stmt.where(SecurityEvent.event_id == event_id)

    event = db.execute(stmt).scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security event with ID '{event_id}' not found.",
        )
    return event
