"""
retention.py — Database Event Retention Policy Management.
Prevents unbounded storage growth by pruning aged telemetry events
while preserving critical security alerts and audit history.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import SecurityEvent

logger = logging.getLogger(__name__)

DEFAULT_MAX_EVENT_AGE_DAYS = 30
DEFAULT_MAX_EVENT_RECORDS = 50000


def enforce_event_retention(
    db: Session,
    max_age_days: int = DEFAULT_MAX_EVENT_AGE_DAYS,
    max_records: int = DEFAULT_MAX_EVENT_RECORDS,
) -> int:
    """
    Enforce event retention policy:
      1. Delete non-alert events (flow, stats, dns, http) older than max_age_days.
      2. If total events still exceed max_records, prune oldest non-critical events.
    Returns:
      Total number of deleted event rows.
    """
    deleted_count = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    # 1. Prune aged informational events
    stmt_age = (
        delete(SecurityEvent)
        .where(
            SecurityEvent.timestamp < cutoff,
            SecurityEvent.event_type.notin_(["alert"]),
        )
    )
    result = db.execute(stmt_age)
    deleted_count += result.rowcount or 0

    # 2. Check total count cap
    total_count = db.execute(select(func.count(SecurityEvent.id))).scalar() or 0
    if total_count > max_records:
        overflow = total_count - max_records
        # Select IDs of oldest non-alert events to remove
        oldest_ids = db.execute(
            select(SecurityEvent.id)
            .where(SecurityEvent.event_type != "alert")
            .order_by(SecurityEvent.timestamp.asc())
            .limit(overflow)
        ).scalars().all()

        if oldest_ids:
            stmt_cap = delete(SecurityEvent).where(SecurityEvent.id.in_(oldest_ids))
            res_cap = db.execute(stmt_cap)
            deleted_count += res_cap.rowcount or 0

    if deleted_count > 0:
        db.commit()
        logger.info("Event retention: pruned %d aged/overflow security events.", deleted_count)

    return deleted_count

