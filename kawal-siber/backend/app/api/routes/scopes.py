"""
scopes.py — Routes for Scan Scope Management in KAWAL SIBER.
Enforces authorized boundaries and testing windows for network scanning.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import ScanScope
from app.schemas import ScanScopeCreate, ScanScopeResponse, ScanScopeUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan-scopes", tags=["Scan Scopes"])


def _get_scope_or_404(scope_id: int, db: Session) -> ScanScope:
    """Return the ScanScope row or raise HTTP 404."""
    scope = db.get(ScanScope, scope_id)
    if scope is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan scope with id={scope_id} not found.",
        )
    return scope


@router.get("", response_model=List[ScanScopeResponse], include_in_schema=False)
@router.get(
    "/",
    response_model=List[ScanScopeResponse],
    summary="List scan scopes",
)
def list_scopes(
    enabled: Optional[bool] = Query(
        default=None,
        description="Filter by enabled status.",
    ),
    skip: int = Query(default=0, ge=0, description="Rows to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max rows to return"),
    db: Session = Depends(get_db),
) -> List[ScanScope]:
    """List registered scan scopes."""
    stmt = select(ScanScope)
    if enabled is not None:
        stmt = stmt.where(ScanScope.enabled == enabled)
    stmt = stmt.order_by(ScanScope.id.asc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=ScanScopeResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post(
    "/",
    response_model=ScanScopeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a scan scope",
)
def create_scope(
    payload: ScanScopeCreate,
    db: Session = Depends(get_db),
) -> ScanScope:
    """
    Register a new authorized scan scope.
    Target must have valid CIDR, authorization reference, and future expiry.
    """
    scope = ScanScope(
        name=payload.name,
        cidr=payload.cidr,
        description=payload.description,
        authorization_reference=payload.authorization_reference,
        enabled=payload.enabled,
        expires_at=payload.expires_at,
    )
    db.add(scope)
    db.commit()
    db.refresh(scope)
    logger.info("Registered scan scope id=%d name=%r cidr=%s", scope.id, scope.name, scope.cidr)
    return scope


@router.get(
    "/{scope_id}",
    response_model=ScanScopeResponse,
    summary="Get scan scope by ID",
)
def get_scope(
    scope_id: int,
    db: Session = Depends(get_db),
) -> ScanScope:
    """Retrieve scan scope details."""
    return _get_scope_or_404(scope_id, db)


@router.patch(
    "/{scope_id}",
    response_model=ScanScopeResponse,
    summary="Update scan scope",
)
def update_scope(
    scope_id: int,
    payload: ScanScopeUpdate,
    db: Session = Depends(get_db),
) -> ScanScope:
    """Update or disable/enable a scan scope."""
    scope = _get_scope_or_404(scope_id, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scope, field, value)

    db.commit()
    db.refresh(scope)
    logger.info("Updated scan scope id=%d fields=%s", scope.id, list(update_data.keys()))
    return scope

