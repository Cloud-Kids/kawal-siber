"""
eve_processor.py — Robust EVE JSON Event Ingestion and Sanitization Engine.
Parses Suricata EVE output line-by-line, sanitizes sensitive payloads, handles
malformed records gracefully, deduplicates events, and maps threat severities.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Maximum allowed single line length in eve.json (1 MB) to prevent memory spikes
MAX_EVE_LINE_BYTES = 1024 * 1024

# Sensitive pattern regexes paired with their replacement strings
_SENSITIVE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(password|passwd|pwd|secret|token|api[_-]?key|bearer)\s*[:=]\s*([^\s;&,\"]+)", re.IGNORECASE), r"\1: [REDACTED]"),
    (re.compile(r"(Authorization:\s*Bearer\s+)[^\r\n]+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"), "[REDACTED]"),
]


class EveRecordValidationError(Exception):
    """Raised when an individual EVE JSON line is irrecoverably corrupt."""
    pass


def sanitize_sensitive_data(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove or mask high-risk sensitive data from EVE event payload
    (passwords, auth headers, private keys) before storing in database.
    """
    sanitized = json.loads(json.dumps(raw_dict))  # deep copy

    # Truncate raw packet hex or massive binary dump if present
    if "packet" in sanitized and isinstance(sanitized["packet"], str):
        if len(sanitized["packet"]) > 512:
            sanitized["packet"] = sanitized["packet"][:512] + "...[TRUNCATED]"

    # Sanitize payload strings
    for field in ("payload", "payload_printable", "http_request_body"):
        val = sanitized.get(field)
        if isinstance(val, str):
            for pat, repl in _SENSITIVE_PATTERNS:
                val = pat.sub(repl, val)
            if len(val) > 1024:
                val = val[:1024] + "...[TRUNCATED]"
            sanitized[field] = val

    # Sanitize HTTP headers
    http = sanitized.get("http")
    if isinstance(http, dict):
        headers = http.get("http_request_headers") or http.get("http_headers")
        if isinstance(headers, list):
            for h in headers:
                if isinstance(h, dict) and "value" in h:
                    name = str(h.get("name", "")).lower()
                    if name in ("authorization", "cookie", "set-cookie", "x-api-key"):
                        h["value"] = "[REDACTED]"

    return sanitized


def parse_iso_timestamp(ts_str: Optional[str]) -> datetime:
    """Parse Suricata ISO timestamp (handles UTC and offsets like +0100)."""
    if not ts_str:
        return datetime.now(timezone.utc)
    try:
        # Normalize +0100 to +01:00 for fromisoformat if needed
        cleaned = ts_str.strip()
        if len(cleaned) >= 5 and (cleaned[-5] in ("+", "-")) and (":" not in cleaned[-4:]):
            cleaned = cleaned[:-2] + ":" + cleaned[-2:]
        dt = datetime.fromisoformat(cleaned)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def compute_event_fingerprint(
    event_type: str,
    src_ip: Optional[str],
    dst_ip: Optional[str],
    src_port: Optional[int],
    dst_port: Optional[int],
    sig_id: Optional[int],
    timestamp: datetime,
) -> str:
    """
    Generate deterministic unique event ID / fingerprint.
    Includes second-precision timestamp to allow distinct events on different seconds
    while preventing exact duplicates from duplicate imports.
    """
    raw_key = (
        f"{event_type}|{src_ip or ''}|{dst_ip or ''}|"
        f"{src_port or 0}|{dst_port or 0}|{sig_id or 0}|"
        f"{int(timestamp.timestamp())}"
    )
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:32]


def map_suricata_severity(event_type: str, alert_obj: Optional[Dict[str, Any]]) -> int:
    """
    Map Suricata severity to standardized integer (1=Critical/High, 2=Medium, 3=Low, 4=Info).
    Suricata native alert.severity:
      1: High / Exploit / Critical
      2: Medium / Policy / Recon
      3: Low / Informational
    Non-alert events are mapped to 3 (anomaly) or 4 (flow/dns/http/tls/stats).
    """
    if event_type == "alert" and alert_obj:
        s = alert_obj.get("severity")
        if isinstance(s, int) and 1 <= s <= 4:
            return s
        return 2  # default medium for unspecified alert
    elif event_type == "anomaly":
        return 3  # Low severity
    return 4  # Informational


def extract_event_fields(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Extract standard fields from a parsed EVE JSON object."""
    event_type = str(raw.get("event_type", "unknown")).lower()
    ts = parse_iso_timestamp(raw.get("timestamp"))

    src_ip = raw.get("src_ip")
    dst_ip = raw.get("dest_ip")
    src_port = raw.get("src_port")
    dst_port = raw.get("dest_port")
    proto = raw.get("proto")

    sig_id: Optional[int] = None
    sig_msg: Optional[str] = None
    category: Optional[str] = None
    confidence: Optional[str] = None
    alert_dict: Optional[Dict[str, Any]] = None

    if event_type == "alert":
        alert_dict = raw.get("alert", {})
        if isinstance(alert_dict, dict):
            sig_id = alert_dict.get("signature_id")
            sig_msg = alert_dict.get("signature")
            category = alert_dict.get("category")
            confidence = "HIGH" if alert_dict.get("severity") == 1 else "MEDIUM"
    elif event_type == "anomaly":
        anomaly = raw.get("anomaly", {})
        if isinstance(anomaly, dict):
            sig_msg = f"Anomaly: {anomaly.get('event', 'generic')}"
            category = f"Anomaly ({anomaly.get('type', 'system')})"
            confidence = "LOW"
    elif event_type in ("http", "dns", "tls", "flow", "stats"):
        confidence = "INFO"

    severity = map_suricata_severity(event_type, alert_dict)
    fingerprint = compute_event_fingerprint(
        event_type=event_type,
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        sig_id=sig_id,
        timestamp=ts,
    )

    # Sanitize payload
    sanitized_raw = sanitize_sensitive_data(raw)

    return {
        "event_id": fingerprint,
        "timestamp": ts,
        "event_type": event_type,
        "source_ip": str(src_ip) if src_ip else None,
        "destination_ip": str(dst_ip) if dst_ip else None,
        "source_port": int(src_port) if src_port is not None else None,
        "destination_port": int(dst_port) if dst_port is not None else None,
        "protocol": str(proto).upper() if proto else None,
        "signature_id": int(sig_id) if sig_id is not None else None,
        "signature": str(sig_msg)[:512] if sig_msg else None,
        "category": str(category)[:128] if category else None,
        "severity": severity,
        "confidence": confidence,
        "raw_event": json.dumps(sanitized_raw, separators=(",", ":")),
    }


def stream_eve_json_file(eve_path: Path) -> Generator[Dict[str, Any], None, None]:
    """
    Stream and yield parsed records from an eve.json file line-by-line.
    Skips invalid JSON or malformed records without halting processing.
    """
    if not eve_path.is_file():
        logger.warning("EVE JSON file not found: %s", eve_path)
        return

    with open(eve_path, "r", encoding="utf-8", errors="replace") as f:
        line_num = 0
        for line in f:
            line_num += 1
            stripped = line.strip()
            if not stripped:
                continue

            if len(line.encode("utf-8")) > MAX_EVE_LINE_BYTES:
                logger.warning("Skipping oversized line %d in %s", line_num, eve_path.name)
                continue

            try:
                data = json.loads(stripped)
                if not isinstance(data, dict):
                    continue
                yield extract_event_fields(data)
            except json.JSONDecodeError as exc:
                logger.debug("Line %d in %s is not valid JSON: %s", line_num, eve_path.name, exc)
                continue
            except Exception as exc:
                logger.warning("Error processing line %d in %s: %s", line_num, eve_path.name, exc)
                continue
