"""
dependencies.py — Shared FastAPI dependency functions for KAWAL SIBER.
"""
from __future__ import annotations

from typing import Generator

from fastapi import Query
from sqlalchemy.orm import Session

from app.database import SessionLocal


# ---------------------------------------------------------------------------
# Database session dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy Session; always close on exit."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Common pagination query parameters
# ---------------------------------------------------------------------------

class CommonQueryParams:
    """
    Reusable pagination dependency.

    Usage::

        @router.get("/items")
        def list_items(params: CommonQueryParams = Depends()):
            ...
    """

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number (1-based)"),
        page_size: int = Query(
            default=20,
            ge=1,
            le=100,
            description="Number of items per page (max 100)",
        ),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        """Zero-based row offset derived from page and page_size."""
        return (self.page - 1) * self.page_size
