"""
assets.py — CRUD routes for monitored assets in KAWAL SIBER (Phase 2).
"""
from __future__ import annotations

import ipaddress
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Asset, Incident, ScanJob, ScanScope
from app.schemas import (
    AssetCreate,
    AssetResponse,
    AssetStatus,
    AssetUpdate,
    AvailabilityStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["Assets"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_asset_or_404(asset_id: int, db: Session) -> Asset:
    """Return the Asset row or raise HTTP 404."""
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with id={asset_id} not found.",
        )
    return asset


def _is_ip_address(val: str) -> bool:
    """Check whether string is a raw IP address."""
    try:
        ipaddress.ip_address(val.strip())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=List[AssetResponse], include_in_schema=False)
@router.get(
    "/",
    response_model=List[AssetResponse],
    summary="List assets",
)
def list_assets(
    asset_status: Optional[AssetStatus] = Query(
        default=None,
        alias="status",
        description="Filter by asset security status.",
    ),
    availability_status: Optional[AvailabilityStatus] = Query(
        default=None,
        description="Filter by asset network availability status.",
    ),
    scope_id: Optional[int] = Query(
        default=None,
        description="Filter by assigned scan scope ID.",
    ),
    target_type: Optional[str] = Query(
        default=None,
        pattern="^(ip|hostname)$",
        description="Filter by target type: 'ip' or 'hostname'.",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Search term matching asset name or target IP/host.",
    ),
    skip: int = Query(default=0, ge=0, description="Rows to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max rows to return"),
    db: Session = Depends(get_db),
) -> List[Asset]:
    """Return a list of assets with optional multi-criteria filtering and pagination."""
    stmt = select(Asset)

    if asset_status is not None:
        stmt = stmt.where(Asset.status == asset_status.value)

    if availability_status is not None:
        stmt = stmt.where(Asset.availability_status == availability_status.value)

    if scope_id is not None:
        stmt = stmt.where(Asset.scope_id == scope_id)

    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(Asset.name.ilike(term), Asset.target_ip.ilike(term))
        )

    stmt = stmt.order_by(Asset.id.asc()).offset(skip).limit(limit)
    assets = list(db.execute(stmt).scalars().all())

    # Client-side target_type filter if requested
    if target_type == "ip":
        assets = [a for a in assets if _is_ip_address(a.target_ip)]
    elif target_type == "hostname":
        assets = [a for a in assets if not _is_ip_address(a.target_ip)]

    return assets


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post(
    "/",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create asset",
)
def create_asset(
    payload: AssetCreate,
    db: Session = Depends(get_db),
) -> Asset:
    """Create and persist a new monitored asset."""
    # If scope_id is provided, verify scope exists
    if payload.scope_id is not None:
        scope = db.get(ScanScope, payload.scope_id)
        if not scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scan scope id={payload.scope_id} does not exist.",
            )

    asset = Asset(
        name=payload.name,
        target_ip=payload.target_ip,
        port=payload.port,
        status=payload.status.value,
        availability_status=payload.availability_status.value,
        scope_id=payload.scope_id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    logger.info("Created asset id=%d name=%r target=%s:%d", asset.id, asset.name, asset.target_ip, asset.port)
    return asset


@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Get asset by ID",
)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
) -> Asset:
    """Retrieve a single asset by its primary key."""
    return _get_asset_or_404(asset_id, db)


@router.patch(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Partial update of an asset",
)
def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
) -> Asset:
    """
    Partially update an asset.
    Only fields explicitly set in the request body are modified.
    """
    asset = _get_asset_or_404(asset_id, db)

    update_data = payload.model_dump(exclude_unset=True)

    # Validate scope_id if modified
    if "scope_id" in update_data and update_data["scope_id"] is not None:
        scope = db.get(ScanScope, update_data["scope_id"])
        if not scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scan scope id={update_data['scope_id']} does not exist.",
            )

    for field, value in update_data.items():
        if field in ("status", "availability_status") and value is not None:
            value = value.value if hasattr(value, "value") else value
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)
    logger.info("Updated asset id=%d fields=%s", asset.id, list(update_data.keys()))
    return asset


@router.delete(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Delete an asset",
)
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
) -> Asset:
    """
    Delete an asset.
    Returns HTTP 409 Conflict if the asset has associated incidents or scan jobs
    (to preserve audit history).
    """
    asset = _get_asset_or_404(asset_id, db)

    # Count incidents linked to this asset
    incident_count: int = db.execute(
        select(func.count()).select_from(Incident).where(
            Incident.asset_id == asset_id
        )
    ).scalar_one()

    if incident_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete asset id={asset_id}: it has {incident_count} "
                "associated incident(s). Remove the incidents first or archive "
                "the asset instead."
            ),
        )

    # Count scan jobs linked to this asset
    job_count: int = db.execute(
        select(func.count()).select_from(ScanJob).where(
            ScanJob.asset_id == asset_id
        )
    ).scalar_one()

    if job_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete asset id={asset_id}: it has {job_count} "
                "associated scan job(s). Retain scan history for audit compliance."
            ),
        )

    db.delete(asset)
    db.commit()
    logger.info("Deleted asset id=%d", asset_id)
    return asset
