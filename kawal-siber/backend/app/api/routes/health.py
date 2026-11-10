"""
health.py — Health-check endpoint for KAWAL SIBER API.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

_API_VERSION = "1.0.0"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the operational status of the API and its database connection.",
)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Ping the database with a cheap query.
    Returns ``status=healthy`` when the database is reachable,
    ``status=degraded`` otherwise.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
        api_status = "healthy"
    except Exception:
        logger.exception("Database health check failed")
        db_status = "error"
        api_status = "degraded"

    return HealthResponse(
        status=api_status,
        database=db_status,
        version=_API_VERSION,
    )
