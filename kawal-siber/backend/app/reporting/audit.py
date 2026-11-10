"""
audit.py — Audit trail infrastructure for the KAWAL SIBER Reporting Engine.

Phase 6 Final Refinement:
- Append-only transactional event recording into dedicated `report_audit_events` table.
- Cryptographic hash chaining: event_hash = SHA-256(prev_hash | report_id | event_type | actor | timestamp | details).
- Chronological event tracking.
- Chain integrity verification helper (`verify_audit_chain`).
- Synchronizes with `report.audit_log_json` for backward compatibility.

SECURITY & IMMUTABILITY DISCLAIMER:
This module enforces an application-level append-only policy with hash chaining.
It detects and exposes any retroactive tampering with historical records.
However, it does NOT provide absolute physical immutability without dedicated
operating system write-once-read-many (WORM) storage or hardware security modules (HSM).
Furthermore, the platform runs on localhost only with no user authentication system.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ReportAuditEvent

logger = logging.getLogger(__name__)

# Recognised event types — keep this list canonical
AUDIT_EVENT_TYPES = frozenset({
    "CREATED",       # Report record inserted
    "STARTED",       # Worker began generation
    "COMPLETED",     # Generation succeeded
    "FAILED",        # Generation failed
    "DOWNLOADED",    # File served via download endpoint
    "REGENERATED",   # Operator triggered regeneration
    "SKIPPED",       # Generation skipped (already completed + file exists)
})

_AUTH_NOTE = "localhost-only-no-authentication"
GENESIS_HASH = "GENESIS"
SERIALIZATION_VERSION = "v1"

ACTOR_SYSTEM_LOCALHOST = "system:localhost"
ACTOR_OPERATOR_UNAUTHENTICATED = "operator:unauthenticated"
UNTRUSTED_ACTOR_HEADERS = ("X-Operator", "X-Actor", "X-Operator-Identity")


def resolve_http_actor_attribution(
    headers: Optional[Dict[str, str]] = None,
    client_host: Optional[str] = None,
) -> tuple[str, Optional[str]]:
    """
    Resolve audit actor identity and untrusted metadata for HTTP operator requests.
    Enforces the security trust boundary:
    - HTTP requests are attributed to 'operator:unauthenticated' (localhost, unauthenticated).
    - Client-supplied headers (X-Operator, X-Actor, X-Operator-Identity) are NEVER trusted as verified identities.
    - If supplied, they are sanitized and returned as untrusted metadata for event details.

    Returns:
        (canonical_actor, untrusted_claimed_metadata)
    """
    canonical_actor = ACTOR_OPERATOR_UNAUTHENTICATED
    claimed: Optional[str] = None
    if headers:
        for header_name in UNTRUSTED_ACTOR_HEADERS:
            val = headers.get(header_name) or headers.get(header_name.lower())
            if val and str(val).strip():
                cleaned = str(val).strip().replace("\r", "").replace("\n", "").replace("|", "_")[:64]
                claimed = f"claimed_actor='{cleaned}' (untrusted)"
                break
    return canonical_actor, claimed


def canonicalize_details(details: Any) -> str:
    """Deterministic canonical serialization for audit event details."""
    if details is None:
        return ""
    if isinstance(details, (dict, list)):
        return json.dumps(details, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if isinstance(details, str):
        s = details.strip()
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                parsed = json.loads(s)
                return json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            except Exception:
                pass
        return s
    return str(details)


def escape_v1_field(val: Any) -> str:
    """
    Escape backslashes and pipe delimiters for v1 serialization to ensure unambiguous field boundaries:
    - Backslash is escaped first: '\\' -> '\\\\'
    - Delimiter is escaped: '|' -> '\\|'
    Consecutive backslashes are preserved unambiguously (e.g. '\\\\' -> '\\\\\\\\'),
    and an escaped delimiter ('\\|') cannot be confused with an unescaped delimiter ('|').
    """
    s = str(val)
    return s.replace("\\", "\\\\").replace("|", "\\|")


def compute_canonical_json_envelope(
    previous_hash: str,
    report_id: str,
    event_type: str,
    actor: str,
    timestamp_iso: str,
    details: Any,
) -> str:
    """
    Versioned application-specific canonical JSON envelope eliminating delimiter boundary ambiguity.
    Note: This is an application-level canonical JSON envelope (deterministic key sorting,
    compact separators, UTF-8), distinct from full RFC 8785 (JCS) compliance.
    """
    envelope = {
        "algorithm": "sha256",
        "version": "v2",
        "previous_event_hash": str(previous_hash),
        "report_id": str(report_id),
        "event_type": str(event_type),
        "actor": str(actor),
        "timestamp_iso": str(timestamp_iso),
        "details": canonicalize_details(details),
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_event_hash(
    previous_hash: str,
    report_id: str,
    event_type: str,
    actor: str,
    timestamp_iso: str,
    details: str,
    version: str = SERIALIZATION_VERSION,
) -> str:
    """Calculate deterministic SHA-256 hash for an audit event block linking to the previous hash."""
    canonical_det = canonicalize_details(details)
    if version == "v2":
        payload = compute_canonical_json_envelope(
            previous_hash=previous_hash,
            report_id=report_id,
            event_type=event_type,
            actor=actor,
            timestamp_iso=timestamp_iso,
            details=canonical_det,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
    elif version == "v1":
        # Strict delimiter and backslash escaping to ensure unambiguous field boundaries
        safe_actor = escape_v1_field(actor)
        safe_rep = escape_v1_field(report_id)
        safe_type = escape_v1_field(event_type)
        payload = f"v1:sha256|{previous_hash}|{safe_rep}|{safe_type}|{safe_actor}|{timestamp_iso}|{canonical_det}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
    else:
        # Legacy unversioned serialization for backward compatibility
        payload = f"{previous_hash}|{report_id}|{event_type}|{actor}|{timestamp_iso}|{details}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def append_audit_event(
    report,  # GeneratedReport ORM object (avoids circular import)
    db: Session,
    event_type: str,
    detail: str = "",
    operator: str = ACTOR_SYSTEM_LOCALHOST,
    commit: bool = True,
    version: str = SERIALIZATION_VERSION,
) -> ReportAuditEvent:
    """
    Append an immutable, hash-chained audit event to `report_audit_events`.
    Also updates `report.audit_log_json` for backward compatibility.
    """
    if event_type not in AUDIT_EVENT_TYPES:
        logger.warning(
            "Unknown audit event_type=%r for report %s",
            event_type,
            getattr(report, "report_id", "?"),
        )

    report_id = str(getattr(report, "report_id", "UNKNOWN"))
    actor = str(operator)[:100]
    detail_str = canonicalize_details(detail)[:1000]
    now_utc = datetime.now(timezone.utc)
    timestamp_iso = now_utc.isoformat()

    # 1. Fetch previous event hash for this report_id to maintain the chain
    stmt = (
        select(ReportAuditEvent)
        .where(ReportAuditEvent.report_id == report_id)
        .order_by(ReportAuditEvent.id.desc())
        .limit(1)
    )
    last_event = db.execute(stmt).scalar_one_or_none()
    previous_hash = last_event.event_hash if last_event else GENESIS_HASH

    # 2. Compute current event hash using requested serialization version
    current_hash = compute_event_hash(
        previous_hash=previous_hash,
        report_id=report_id,
        event_type=event_type,
        actor=actor,
        timestamp_iso=timestamp_iso,
        details=detail_str,
        version=version,
    )

    # 3. Create persistent audit event record
    audit_event = ReportAuditEvent(
        report_id=report_id,
        event_type=event_type,
        actor=actor,
        timestamp=now_utc,
        event_details=detail_str,
        previous_event_hash=previous_hash,
        event_hash=current_hash,
    )
    db.add(audit_event)

    # 4. Sync with report.audit_log_json for backward compatibility
    try:
        events: list = json.loads(report.audit_log_json or "[]")
    except (json.JSONDecodeError, TypeError):
        events = []

    events.append({
        "event_type": event_type,
        "timestamp_utc": timestamp_iso,
        "operator": actor,
        "detail": detail_str,
        "previous_event_hash": previous_hash,
        "event_hash": current_hash,
        "serialization_version": version,
        "auth": _AUTH_NOTE,
    })
    report.audit_log_json = json.dumps(events)

    if commit:
        try:
            db.commit()
        except Exception:
            logger.exception("Failed to commit audit event for report %s", report_id)
            db.rollback()
            raise

    return audit_event


def get_audit_log(report) -> list:
    """Return parsed audit event list from a report record. Returns [] on error."""
    try:
        return json.loads(report.audit_log_json or "[]")
    except (json.JSONDecodeError, TypeError):
        return []


def determine_event_version(
    ev: ReportAuditEvent,
    idx: int,
    audit_log: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Determine the serialization version of an audit event for strict verification dispatch.
    Returns: 'legacy', 'v1', 'v2', or an unknown version string.
    """
    if audit_log and idx < len(audit_log):
        entry = audit_log[idx]
        if entry.get("previous_event_hash") == ev.previous_event_hash:
            v = entry.get("serialization_version")
            return v if v is not None else "legacy"

    # Check event_details for explicit version tag if details is a JSON string
    if ev.event_details:
        try:
            parsed = json.loads(ev.event_details)
            if isinstance(parsed, dict):
                for k in ("serialization_version", "version", "_audit_version"):
                    if k in parsed:
                        return str(parsed[k])
        except Exception:
            pass

    return "v1"


def verify_audit_chain(
    report_id: str,
    db: Session,
    expected_latest_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verify the cryptographic hash chain of all audit events for a report with strict version dispatch.

    Validates:
    - Chronological sequencing (id and timestamp order)
    - Hash linkage (each event's previous_event_hash matches the prior event's event_hash; starts at GENESIS)
    - Strict versioned hash recomputation:
      - 'v1': verified ONLY with v1 serialization (escaped delimiters)
      - 'v2': verified ONLY with v2 canonical JSON envelope
      - 'legacy': verified ONLY with legacy unversioned format
      - unknown: rejected with UNSUPPORTED_VERSION status
    - No silent cross-version fallback.
    - Optional external checkpoint verification.

    Returns a verification summary dict.
    """
    from app.models import GeneratedReport

    stmt = (
        select(ReportAuditEvent)
        .where(ReportAuditEvent.report_id == report_id)
        .order_by(ReportAuditEvent.id.asc())
    )
    events = list(db.execute(stmt).scalars().all())

    if not events:
        return {
            "report_id": report_id,
            "verified": True,
            "event_count": 0,
            "status": "EMPTY_CHAIN",
            "message": "No audit events recorded for this report ID.",
        }

    # Fetch report to obtain audit_log_json version metadata if present
    rep_stmt = select(GeneratedReport).where(GeneratedReport.report_id == report_id)
    report_obj = db.execute(rep_stmt).scalar_one_or_none()
    audit_log: List[Dict[str, Any]] = []
    if report_obj and report_obj.audit_log_json:
        try:
            audit_log = json.loads(report_obj.audit_log_json)
        except Exception:
            audit_log = []

    expected_prev_hash = GENESIS_HASH
    last_id = -1
    last_ts: Optional[datetime] = None

    for idx, ev in enumerate(events):
        # 1. Check sequence and timestamp monotonicity
        if ev.id <= last_id:
            return {
                "report_id": report_id,
                "verified": False,
                "event_count": len(events),
                "broken_at_event_id": ev.id,
                "status": "SEQUENCE_ORDER_INVALID",
                "message": f"Non-monotonic event ID sequence at index {idx} (id={ev.id} <= last_id={last_id}).",
            }
        last_id = ev.id

        ev_ts = ev.timestamp if ev.timestamp.tzinfo else ev.timestamp.replace(tzinfo=timezone.utc)
        if last_ts and ev_ts < last_ts:
            return {
                "report_id": report_id,
                "verified": False,
                "event_count": len(events),
                "broken_at_event_id": ev.id,
                "status": "TIMESTAMP_ORDER_INVALID",
                "message": f"Non-monotonic timestamp order at event index {idx} (id={ev.id}).",
            }
        last_ts = ev_ts

        # 2. Check previous hash linkage (Anchor is GENESIS)
        if ev.previous_event_hash != expected_prev_hash:
            logger.error(
                "Audit chain broken for report %s at event id=%d: "
                "expected previous_hash=%s, found=%s",
                report_id,
                ev.id,
                expected_prev_hash,
                ev.previous_event_hash,
            )
            return {
                "report_id": report_id,
                "verified": False,
                "event_count": len(events),
                "broken_at_event_id": ev.id,
                "status": "HASH_CHAIN_MISMATCH",
                "message": f"Previous hash linkage mismatch at event index {idx} (id={ev.id}).",
            }

        # 3. Determine explicit version and recompute hash strictly under that version
        iso_str = ev_ts.isoformat()
        version = determine_event_version(ev, idx, audit_log)

        if version == "v1":
            recomputed = compute_event_hash(
                previous_hash=ev.previous_event_hash,
                report_id=ev.report_id,
                event_type=ev.event_type,
                actor=ev.actor,
                timestamp_iso=iso_str,
                details=ev.event_details or "",
                version="v1",
            )
            if recomputed != ev.event_hash:
                # Strict: NO fallback to v2 or legacy
                logger.error(
                    "Audit event v1 tampering detected for report %s at event id=%d: stored=%s, recomputed=%s",
                    report_id,
                    ev.id,
                    ev.event_hash,
                    recomputed,
                )
                return {
                    "report_id": report_id,
                    "verified": False,
                    "event_count": len(events),
                    "broken_at_event_id": ev.id,
                    "status": "EVENT_HASH_TAMPERED",
                    "message": f"Recomputed v1 hash mismatch at event index {idx} (id={ev.id}). Record content may have been altered.",
                }
        elif version == "v2":
            recomputed = compute_event_hash(
                previous_hash=ev.previous_event_hash,
                report_id=ev.report_id,
                event_type=ev.event_type,
                actor=ev.actor,
                timestamp_iso=iso_str,
                details=ev.event_details or "",
                version="v2",
            )
            if recomputed != ev.event_hash:
                # Strict: NO fallback to v1 or legacy
                logger.error(
                    "Audit event v2 tampering detected for report %s at event id=%d: stored=%s, recomputed=%s",
                    report_id,
                    ev.id,
                    ev.event_hash,
                    recomputed,
                )
                return {
                    "report_id": report_id,
                    "verified": False,
                    "event_count": len(events),
                    "broken_at_event_id": ev.id,
                    "status": "EVENT_HASH_TAMPERED",
                    "message": f"Recomputed v2 hash mismatch at event index {idx} (id={ev.id}). Record content may have been altered.",
                }
        elif version == "legacy":
            recomputed = compute_event_hash(
                previous_hash=ev.previous_event_hash,
                report_id=ev.report_id,
                event_type=ev.event_type,
                actor=ev.actor,
                timestamp_iso=iso_str,
                details=ev.event_details or "",
                version="legacy",
            )
            if recomputed != ev.event_hash:
                # Strict: NO fallback to v1 or v2
                logger.error(
                    "Audit event legacy tampering detected for report %s at event id=%d: stored=%s, recomputed=%s",
                    report_id,
                    ev.id,
                    ev.event_hash,
                    recomputed,
                )
                return {
                    "report_id": report_id,
                    "verified": False,
                    "event_count": len(events),
                    "broken_at_event_id": ev.id,
                    "status": "EVENT_HASH_TAMPERED",
                    "message": f"Recomputed legacy hash mismatch at event index {idx} (id={ev.id}). Record content may have been altered.",
                }
        else:
            logger.error(
                "Audit event unsupported version '%s' for report %s at event id=%d",
                version,
                report_id,
                ev.id,
            )
            return {
                "report_id": report_id,
                "verified": False,
                "event_count": len(events),
                "broken_at_event_id": ev.id,
                "status": "UNSUPPORTED_VERSION",
                "message": f"Unsupported or unknown audit serialization version '{version}' at event index {idx} (id={ev.id}).",
            }

        expected_prev_hash = ev.event_hash

    # 4. Optional external trusted anchor check (detects final-event deletion / complete chain replacement)
    if expected_latest_hash is not None and expected_prev_hash != expected_latest_hash:
        logger.error(
            "Audit chain anchor mismatch for report %s: chain tip=%s, expected anchor=%s",
            report_id,
            expected_prev_hash,
            expected_latest_hash,
        )
        return {
            "report_id": report_id,
            "verified": False,
            "event_count": len(events),
            "status": "FINAL_EVENT_TRUNCATED_OR_CHAIN_REPLACED",
            "message": "Chain is internally valid, but latest hash does not match the external trusted checkpoint.",
        }

    return {
        "report_id": report_id,
        "verified": True,
        "event_count": len(events),
        "status": "CHAIN_VALID",
        "latest_hash": expected_prev_hash,
        "message": f"Cryptographic audit chain verified across {len(events)} event(s).",
    }
