"""
scans.py — Scan job orchestration and result viewing API routes for KAWAL SIBER.
Enforces strict scope verification prior to creating PENDING jobs.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import get_db
from app.models import Asset, ScanJob, ScanResult, ScanScope
from app.schemas import (
    ScanJobResponse,
    ScanJobStatus,
    ScanResultResponse,
)
from app.services.scope_validator import (
    DNSResolutionError,
    OutOfScopeError,
    ScopeDisabledError,
    ScopeExpiredError,
    ScopeValidationError,
    validate_target_against_scope,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scans"])


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _get_asset_or_404(asset_id: int, db: Session) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with id={asset_id} not found.",
        )
    return asset


def _get_scan_job_or_404(scan_id: int, db: Session) -> ScanJob:
    stmt = (
        select(ScanJob)
        .where(ScanJob.id == scan_id)
        .options(selectinload(ScanJob.results))
    )
    job = db.execute(stmt).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan job with id={scan_id} not found.",
        )
    return job


def _verify_asset_scope_authorization(asset: Asset, db: Session) -> ScanScope:
    """
    Verify that the target asset is covered by an active, valid scan scope.
    If asset has an assigned scope_id, validate against that scope.
    Otherwise, search all active scopes for a matching CIDR block.
    """
    target_scope: Optional[ScanScope] = None

    if asset.scope_id is not None:
        target_scope = db.get(ScanScope, asset.scope_id)
        if not target_scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assigned scan scope id={asset.scope_id} does not exist.",
            )
    else:
        # Check if any active scope encompasses this asset
        active_scopes = (
            db.execute(select(ScanScope).where(ScanScope.enabled == True))
            .scalars()
            .all()
        )
        for s in active_scopes:
            try:
                validate_target_against_scope(
                    target=asset.target_ip,
                    cidr=s.cidr,
                    enabled=s.enabled,
                    expires_at=s.expires_at,
                )
                target_scope = s
                # Link asset to matching scope
                asset.scope_id = s.id
                db.commit()
                break
            except ScopeValidationError:
                continue

    if not target_scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Asset {asset.name!r} ({asset.target_ip}) does not have an active "
                "authorized scan scope. Scanning is forbidden."
            ),
        )

    # Perform thorough scope validation
    try:
        validate_target_against_scope(
            target=asset.target_ip,
            cidr=target_scope.cidr,
            enabled=target_scope.enabled,
            expires_at=target_scope.expires_at,
        )
    except ScopeDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Scan scope {target_scope.name!r} is disabled: {exc}",
        ) from exc
    except ScopeExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Scan authorization for scope {target_scope.name!r} has expired: {exc}",
        ) from exc
    except OutOfScopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Asset target is outside authorized scope: {exc}",
        ) from exc
    except DNSResolutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DNS resolution failure during scope verification: {exc}",
        ) from exc
    except ScopeValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Scope authorization rejected: {exc}",
        ) from exc

    return target_scope


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/assets/{asset_id}/scans",
    response_model=ScanJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enqueue a network discovery scan job for an asset",
)
def create_asset_scan_job(
    asset_id: int,
    db: Session = Depends(get_db),
) -> ScanJob:
    """
    Enqueue an authorized Nmap port scan job for a registered asset.
    The job is created in PENDING state and processed asynchronously by the worker.
    """
    asset = _get_asset_or_404(asset_id, db)

    # 1. Authorize against scan scopes
    _verify_asset_scope_authorization(asset, db)

    # 2. Check for existing active job to prevent duplicate queueing
    active_job = db.execute(
        select(ScanJob).where(
            ScanJob.asset_id == asset_id,
            ScanJob.status.in_(["PENDING", "RUNNING"]),
        )
    ).scalar_one_or_none()

    if active_job is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A scan job (id={active_job.id}, status={active_job.status}) "
                f"is already active for asset id={asset_id}."
            ),
        )

    # 3. Create PENDING job
    job = ScanJob(
        asset_id=asset.id,
        status="PENDING",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(
        "Enqueued scan job id=%d for asset id=%d (%s:%d)",
        job.id,
        asset.id,
        asset.target_ip,
        asset.port,
    )
    return job


@router.get(
    "/scans",
    response_model=List[ScanJobResponse],
    summary="List all scan jobs",
)
def list_scans(
    status_filter: Optional[ScanJobStatus] = Query(
        default=None,
        alias="status",
        description="Filter by job status.",
    ),
    asset_id: Optional[int] = Query(
        default=None,
        description="Filter by asset ID.",
    ),
    skip: int = Query(default=0, ge=0, description="Rows to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max rows to return"),
    db: Session = Depends(get_db),
) -> List[ScanJob]:
    """List scan jobs with optional filtering."""
    stmt = (
        select(ScanJob)
        .options(selectinload(ScanJob.results))
        .order_by(ScanJob.created_at.desc())
    )

    if status_filter is not None:
        stmt = stmt.where(ScanJob.status == status_filter.value)
    if asset_id is not None:
        stmt = stmt.where(ScanJob.asset_id == asset_id)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.get(
    "/scans/{scan_id}",
    response_model=ScanJobResponse,
    summary="Get scan job details and findings",
)
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
) -> ScanJob:
    """Retrieve scan job details and associated port findings."""
    return _get_scan_job_or_404(scan_id, db)


@router.get(
    "/scans/{scan_id}/results",
    response_model=List[ScanResultResponse],
    summary="Get scan results for a job",
)
def get_scan_results(
    scan_id: int,
    db: Session = Depends(get_db),
) -> List[ScanResult]:
    """Retrieve raw port scan results for a job."""
    _get_scan_job_or_404(scan_id, db)
    stmt = select(ScanResult).where(ScanResult.scan_job_id == scan_id).order_by(ScanResult.port.asc())
    return list(db.execute(stmt).scalars().all())


@router.get(
    "/assets/{asset_id}/scans",
    response_model=List[ScanJobResponse],
    summary="Get scan history for an asset",
)
def get_asset_scans(
    asset_id: int,
    skip: int = Query(default=0, ge=0, description="Rows to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Max rows to return"),
    db: Session = Depends(get_db),
) -> List[ScanJob]:
    """Retrieve scan history for a specific asset."""
    _get_asset_or_404(asset_id, db)
    stmt = (
        select(ScanJob)
        .where(ScanJob.asset_id == asset_id)
        .options(selectinload(ScanJob.results))
        .order_by(ScanJob.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())

