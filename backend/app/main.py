"""
main.py — FastAPI application entry point for KAWAL SIBER.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import assets, health, incidents, monitoring, reports, scans, scopes, security_events, web_assessments
from app.api.routes.incident_intelligence import ai_router, incident_ext_router, intelligence_router
from app.database import Base, SessionLocal, engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application configuration
# ---------------------------------------------------------------------------
_FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:3000")
_MAX_REQUEST_BODY_BYTES: int = 50 * 1024 * 1024  # 50 MB (accommodates PCAP uploads)


# ---------------------------------------------------------------------------
# Lifespan: create tables on startup (for non-migration environments)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create all tables at startup (idempotent, safe for dev/test)."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")

    # Reap orphaned background jobs: PCAP analyses stuck in RUNNING/PENDING
    # because the process restarted mid-task would otherwise show "MEMPROSES"
    # forever. Anything older than 15 minutes without completion is failed.
    try:
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import update
        from app.models import PcapAnalysis

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
        with SessionLocal() as db:
            result = db.execute(
                update(PcapAnalysis)
                .where(
                    PcapAnalysis.status.in_(["RUNNING", "PENDING"]),
                    PcapAnalysis.created_at < cutoff,
                )
                .values(
                    status="FAILED",
                    completed_at=datetime.now(timezone.utc),
                    error_message="Analysis interrupted by service restart — please resubmit the PCAP file.",
                )
            )
            db.commit()
            if result.rowcount:
                logger.warning("Reaped %d orphaned PCAP analyses.", result.rowcount)
    except Exception:
        logger.exception("Failed to reap orphaned PCAP analyses.")

    yield
    logger.info("Application shutdown.")


# ---------------------------------------------------------------------------
# FastAPI application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="KAWAL SIBER API",
    version="1.0.0",
    description=(
        "Cybersecurity monitoring platform backend — "
        "asset management and incident tracking."
    ),
    lifespan=lifespan,
    # Disable default /docs and /redoc in production if needed via env;
    # keep enabled for development convenience.
    docs_url=None if os.environ.get("KAWAL_JUDGE_MODE", "").lower() == "true" else "/docs",
    redoc_url=None if os.environ.get("KAWAL_JUDGE_MODE", "").lower() == "true" else "/redoc",
    openapi_url=None if os.environ.get("KAWAL_JUDGE_MODE", "").lower() == "true" else "/openapi.json",
)


# ---------------------------------------------------------------------------
# Middleware: CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Middleware: request body size limit (1 MB)
# ---------------------------------------------------------------------------
@app.middleware("http")
async def judge_mode_guard(request: Request, call_next):  # type: ignore[type-arg]
    """Public judge demo mode: deny-by-default read-only enforcement."""
    from app.judge_mode import JUDGE_MODE, judge_guard
    if JUDGE_MODE:
        blocked = judge_guard(request)
        if blocked is not None:
            return blocked
    return await call_next(request)


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):  # type: ignore[type-arg]
    """Reject requests whose Content-Length exceeds 1 MB."""
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > _MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": "Request body exceeds the 1 MB limit."},
                )
        except ValueError:
            pass  # malformed header — let FastAPI handle it
    return await call_next(request)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return structured 422 errors without leaking internal paths."""
    errors = []
    for err in exc.errors():
        errors.append(
            {
                "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg", "Validation error"),
                "type": err.get("type", "unknown"),
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler that never leaks stack traces or internal paths."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred."},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
_API_PREFIX = "/api/v1"

app.include_router(health.router, prefix=_API_PREFIX)
app.include_router(assets.router, prefix=_API_PREFIX)
app.include_router(incidents.router, prefix=_API_PREFIX)
app.include_router(scopes.router, prefix=_API_PREFIX)
app.include_router(scans.router, prefix=_API_PREFIX)
app.include_router(monitoring.router, prefix=_API_PREFIX)
app.include_router(security_events.router, prefix=_API_PREFIX)
app.include_router(web_assessments.router, prefix=_API_PREFIX)
# Phase 5: AI Triage & Incident Intelligence
app.include_router(intelligence_router, prefix=_API_PREFIX)
app.include_router(ai_router, prefix=_API_PREFIX)
app.include_router(incident_ext_router, prefix=_API_PREFIX)
# Phase 6: Automated Reporting & Platform Analytics
app.include_router(reports.router, prefix=_API_PREFIX)
