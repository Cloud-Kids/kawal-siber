"""
incident_correlator.py — Suricata Alert to Asset Incident Correlation Engine.
Maps network threat detections to registered territorial assets with thresholding,
deduplication, directional context (target vs source), and status updates.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Asset, Incident, SecurityEvent

logger = logging.getLogger(__name__)

# Severity mapping from Suricata integer (1-4) to Incident severity enum
_SEVERITY_MAP = {
    1: "CRITICAL",
    2: "HIGH",
    3: "MEDIUM",
    4: "LOW",
}


def classify_attack_type(signature: Optional[str], category: Optional[str], event_type: str) -> str:
    """Classify incident attack_type based on Suricata signature and category metadata."""
    sig_lower = (signature or "").lower()
    cat_lower = (category or "").lower()

    if any(k in sig_lower for k in ("sql injection", "union select", "sqlmap", "sqli")):
        return "SQL_INJECTION"
    if any(k in sig_lower for k in ("xss", "cross-site scripting", "<script")):
        return "XSS"
    if any(k in sig_lower for k in ("brute force", "bruteforce", "login failed", "ssh auth", "password")):
        return "BRUTE_FORCE"
    if any(k in sig_lower for k in ("scan", "nmap", "masscan", "xmas", "null scan", "recon", "reconnaissance")):
        return "PORT_SCAN"

    if "web-application-attack" in cat_lower:
        return "SQL_INJECTION"
    if "attempted-recon" in cat_lower:
        return "PORT_SCAN"

    return "ANOMALY_TRAFFIC"


def correlate_event_with_assets(
    event: SecurityEvent,
    db: Session,
    dedup_window_minutes: int = 60,
) -> Optional[Incident]:
    """
    Correlate a SecurityEvent with monitored territorial assets.
    If the event is an alert and matches a registered asset:
      - Assign asset_id to the SecurityEvent
      - Create an Incident if threshold is met and not an unmitigated duplicate
      - Conditionally update asset security status (UNDER_ATTACK only for High/Critical)

    Returns:
      Created Incident instance, or None if no correlation/incident generated.
    """
    if not event.destination_ip and not event.source_ip:
        return None

    # Step 1: Find matching registered asset
    # Priority: destination_ip (asset is target of attack), then source_ip (asset compromised/scanning)
    matched_asset: Optional[Asset] = None
    attacker_ip: Optional[str] = None
    is_target = True

    if event.destination_ip:
        query = select(Asset).where(Asset.target_ip == event.destination_ip)
        if event.destination_port:
            exact = db.execute(query.where(Asset.port == event.destination_port)).scalars().first()
            if exact:
                matched_asset = exact
        if not matched_asset:
            matched_asset = db.execute(query).scalars().first()

        if matched_asset:
            attacker_ip = event.source_ip or "UNKNOWN"
            is_target = True

    if not matched_asset and event.source_ip:
        query = select(Asset).where(Asset.target_ip == event.source_ip)
        if event.source_port:
            exact = db.execute(query.where(Asset.port == event.source_port)).scalars().first()
            if exact:
                matched_asset = exact
        if not matched_asset:
            matched_asset = db.execute(query).scalars().first()

        if matched_asset:
            attacker_ip = event.destination_ip or "UNKNOWN"
            is_target = False

    if not matched_asset:
        return None

    # Link asset to security event record
    event.asset_id = matched_asset.id

    # Step 2: Determine if this event qualifies for Incident creation
    # Invariant: Only 'alert' events with actionable signature qualify
    if event.event_type != "alert" or not event.signature:
        return None

    severity_str = _SEVERITY_MAP.get(event.severity or 3, "LOW")
    attack_type = classify_attack_type(event.signature, event.category, event.event_type)

    # Step 3: Deduplication check against open incidents for this asset
    window_start = datetime.now(timezone.utc) - timedelta(minutes=dedup_window_minutes)
    existing_incident = db.execute(
        select(Incident).where(
            Incident.asset_id == matched_asset.id,
            Incident.attack_type == attack_type,
            Incident.is_mitigated == False,
            Incident.timestamp >= window_start,
        )
    ).scalars().first()

    if existing_incident:
        logger.debug(
            "Deduplicating alert %s for asset id=%d — matching open incident %d exists",
            event.signature,
            matched_asset.id,
            existing_incident.id,
        )
        return None

    # Step 4: Create new correlated Incident
    role_note = "Target (Inbound Attack)" if is_target else "Source (Possible Outbound Compromise)"
    ai_stub = (
        f"Automated Suricata Correlation: Alert '{event.signature}' (SID: {event.signature_id or 'N/A'}) "
        f"detected on asset {matched_asset.name!r} [{role_note}]. Category: {event.category or 'Unclassified'}."
    )

    incident = Incident(
        asset_id=matched_asset.id,
        source_ip=attacker_ip or "0.0.0.0",
        attack_type=attack_type,
        severity=severity_str,
        payload=event.signature,
        ai_analysis=ai_stub,
        is_mitigated=False,
    )
    db.add(incident)

    # Step 5: Update asset security status based on severity
    # Invariant: UNDER_ATTACK only for CRITICAL or HIGH, WARNING for MEDIUM
    if severity_str in ("CRITICAL", "HIGH"):
        matched_asset.status = "UNDER_ATTACK"
        logger.warning(
            "Asset id=%d (%s) set to UNDER_ATTACK due to %s alert '%s'",
            matched_asset.id,
            matched_asset.name,
            severity_str,
            event.signature,
        )
    elif severity_str == "MEDIUM" and matched_asset.status != "UNDER_ATTACK":
        matched_asset.status = "WARNING"

    db.flush()
    return incident
