"""
test_suricata_phase3.py — Comprehensive Unit & Integration Tests for Suricata Phase 3.
Covers executable detection, config validation, PCAP validation/generation, EVE JSON ingestion,
payload sanitization, threat classification, incident correlation, retention, and API endpoints.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine, SessionLocal
from app.main import app
from app.models import Asset, Incident, PcapAnalysis, SecurityEvent
from app.services.eve_processor import (
    compute_event_fingerprint,
    extract_event_fields,
    map_suricata_severity,
    sanitize_sensitive_data,
    stream_eve_json_file,
)
from app.services.incident_correlator import (
    classify_attack_type,
    correlate_event_with_assets,
)
from app.services.pcap_builder import (
    build_http_get_packet,
    build_icmp_echo_packet,
    build_tcp_scan_packet,
    write_pcap,
)
from app.services.retention import enforce_event_retention
from app.services.suricata_engine import (
    PcapValidationError,
    execute_suricata_pcap,
    get_default_config_path,
    get_suricata_version,
    resolve_suricata_executable,
    validate_pcap_file,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ---------------------------------------------------------------------------
# 1. Suricata Engine & Environment Tests
# ---------------------------------------------------------------------------
def _suricata_binary_available() -> bool:
    try:
        return resolve_suricata_executable().is_file()
    except Exception:
        return False


@pytest.mark.skipif(
    not _suricata_binary_available(),
    reason="Suricata binary not installed on this host",
)
def test_suricata_executable_detected():
    """Verify Suricata binary is discoverable on Windows host."""
    exe = resolve_suricata_executable()
    assert exe.is_file(), f"Suricata binary not found at {exe}"
    version = get_suricata_version(exe)
    assert "Suricata" in version, f"Unexpected version string: {version}"


def test_suricata_config_validity():
    """Verify dedicated suricata.yaml exists and is accessible."""
    conf = get_default_config_path()
    assert conf.is_file(), f"Suricata config not found at {conf}"
    content = conf.read_text(encoding="utf-8")
    assert "eve-log" in content
    assert "suricata-version" in content


# ---------------------------------------------------------------------------
# 2. PCAP Validation & Generation Tests
# ---------------------------------------------------------------------------
def test_pcap_validation_security(tmp_path):
    """Test validation blocks invalid extensions, empty files, and path traversal."""
    allowed_dir = tmp_path / "allowed_pcaps"
    allowed_dir.mkdir()

    # 1. Invalid extension
    bad_file = allowed_dir / "malicious.exe"
    bad_file.write_text("dummy")
    with pytest.raises(PcapValidationError, match="Unsupported file extension"):
        validate_pcap_file(bad_file, allowed_dir=allowed_dir)

    # 2. Empty file
    empty_pcap = allowed_dir / "empty.pcap"
    empty_pcap.touch()
    with pytest.raises(PcapValidationError, match="empty"):
        validate_pcap_file(empty_pcap, allowed_dir=allowed_dir)

    # 3. Path traversal outside authorized directory
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    traversal_file = outside_dir / "traversal.pcap"
    traversal_file.write_bytes(b"dummy-bytes")
    with pytest.raises(PcapValidationError, match="Access denied"):
        validate_pcap_file(traversal_file, allowed_dir=allowed_dir)

    # 4. Valid PCAP
    valid_pcap = allowed_dir / "test.pcap"
    pkts = [build_icmp_echo_packet("192.168.1.1", "10.0.0.1")]
    write_pcap(valid_pcap, pkts)
    fhash, fsize = validate_pcap_file(valid_pcap, allowed_dir=allowed_dir)
    assert len(fhash) == 64
    assert fsize > 0


# ---------------------------------------------------------------------------
# 3. EVE JSON Processing & Sanitization Tests
# ---------------------------------------------------------------------------
def test_sensitive_data_sanitization():
    """Verify passwords, authorization tokens, and excessive payloads are masked."""
    raw_event = {
        "event_type": "http",
        "payload_printable": "POST /login HTTP/1.1\r\nAuthorization: Bearer secret-jwt-token-12345\r\n\r\nusername=admin&password=SuperSecretPassword123",
        "http": {
            "http_headers": [
                {"name": "Authorization", "value": "Bearer secret-jwt-token-12345"},
                {"name": "Host", "value": "127.0.0.1:8000"}
            ]
        },
        "packet": "A" * 1000  # large packet dump
    }
    sanitized = sanitize_sensitive_data(raw_event)
    san_payload = sanitized["payload_printable"]
    assert "SuperSecretPassword123" not in san_payload
    assert "[REDACTED]" in san_payload
    assert sanitized["http"]["http_headers"][0]["value"] == "[REDACTED]"
    assert "[TRUNCATED]" in sanitized["packet"]


def test_malformed_eve_json_handling(tmp_path):
    """Verify eve_processor skips corrupt JSON lines without crashing."""
    eve_file = tmp_path / "corrupt_eve.json"
    content = (
        '{"timestamp": "2026-11-07T06:00:00.000000+0000", "event_type": "flow", "src_ip": "1.1.1.1"}\n'
        'CORRUPT_NON_JSON_LINE_HERE\n'
        '{"timestamp": "2026-11-07T06:00:01.000000+0000", "event_type": "alert", "alert": {"signature": "Test Alert", "severity": 1}}\n'
    )
    eve_file.write_text(content, encoding="utf-8")

    records = list(stream_eve_json_file(eve_file))
    assert len(records) == 2
    assert records[0]["event_type"] == "flow"
    assert records[1]["event_type"] == "alert"
    assert records[1]["severity"] == 1


def test_event_deduplication_fingerprint():
    """Verify identical events receive matching deterministic fingerprints."""
    ts = datetime(2026, 11, 7, 10, 0, 0, tzinfo=timezone.utc)
    fp1 = compute_event_fingerprint("alert", "1.2.3.4", "5.6.7.8", 1000, 80, 1001, ts)
    fp2 = compute_event_fingerprint("alert", "1.2.3.4", "5.6.7.8", 1000, 80, 1001, ts)
    fp3 = compute_event_fingerprint("alert", "1.2.3.4", "5.6.7.8", 1000, 80, 1002, ts)
    assert fp1 == fp2
    assert fp1 != fp3


# ---------------------------------------------------------------------------
# 4. Incident Correlation & Invariant Tests
# ---------------------------------------------------------------------------
def test_incident_correlation_and_invariant(db):
    """
    Test that alert correlated with registered asset generates Incident,
    sets UNDER_ATTACK only for Critical/High, and informational events are ignored.
    """
    # Create test asset
    asset = Asset(
        name="Suricata Test Target",
        target_ip="10.200.50.25",
        port=80,
        status="UNKNOWN",
        availability_status="UP",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    try:
        # 1. Informational event (flow) — MUST NOT create incident and MUST NOT alter status
        info_event = SecurityEvent(
            event_id="test-fp-flow-001",
            timestamp=datetime.now(timezone.utc),
            event_type="flow",
            source_ip="192.168.10.5",
            destination_ip="10.200.50.25",
            severity=4,
        )
        db.add(info_event)
        correlate_event_with_assets(info_event, db)
        assert info_event.asset_id == asset.id
        db.refresh(asset)
        assert asset.status == "UNKNOWN", "Info event must not change asset status"

        # 2. Critical Alert (SQL Injection) — MUST create Incident and set status UNDER_ATTACK
        crit_event = SecurityEvent(
            event_id="test-fp-sqli-001",
            timestamp=datetime.now(timezone.utc),
            event_type="alert",
            source_ip="192.168.10.99",
            destination_ip="10.200.50.25",
            signature="KAWAL-SIBER Possible SQL Injection in URI",
            category="web-application-attack",
            severity=1,
        )
        db.add(crit_event)
        inc = correlate_event_with_assets(crit_event, db)
        assert inc is not None
        assert inc.attack_type == "SQL_INJECTION"
        assert inc.severity == "CRITICAL"
        db.commit()
        db.refresh(asset)
        assert asset.status == "UNDER_ATTACK", "Critical alert must set status to UNDER_ATTACK"

        # 3. Deduplication check — immediate duplicate attack must not create second incident
        dup_event = SecurityEvent(
            event_id="test-fp-sqli-002",
            timestamp=datetime.now(timezone.utc),
            event_type="alert",
            source_ip="192.168.10.99",
            destination_ip="10.200.50.25",
            signature="KAWAL-SIBER Possible SQL Injection in URI",
            category="web-application-attack",
            severity=1,
        )
        db.add(dup_event)
        dup_inc = correlate_event_with_assets(dup_event, db)
        assert dup_inc is None, "Duplicate active incident must be deduplicated"

    finally:
        # Cleanup test records safely
        try:
            db.rollback()
            db.query(Incident).filter(Incident.asset_id == asset.id).delete()
            db.query(SecurityEvent).filter(SecurityEvent.asset_id == asset.id).delete()
            db.delete(asset)
            db.commit()
        except Exception:
            db.rollback()


# ---------------------------------------------------------------------------
# 5. Event Retention Policy Tests
# ---------------------------------------------------------------------------
def test_event_retention_policy(db):
    """Verify aged informational events are pruned while alerts are retained."""
    old_time = datetime.now(timezone.utc) - timedelta(days=45)
    recent_time = datetime.now(timezone.utc)

    # Old flow event (should be deleted)
    evt_old_flow = SecurityEvent(
        event_id="ret-old-flow-1",
        timestamp=old_time,
        event_type="flow",
    )
    # Old alert event (should be preserved)
    evt_old_alert = SecurityEvent(
        event_id="ret-old-alert-1",
        timestamp=old_time,
        event_type="alert",
        signature="Preserved Critical Alert",
        severity=1,
    )
    # Recent flow event (should be preserved)
    evt_rec_flow = SecurityEvent(
        event_id="ret-rec-flow-1",
        timestamp=recent_time,
        event_type="flow",
    )
    db.add_all([evt_old_flow, evt_old_alert, evt_rec_flow])
    db.commit()

    pruned = enforce_event_retention(db, max_age_days=30)
    assert pruned >= 1

    check_old_flow = db.query(SecurityEvent).filter(SecurityEvent.event_id == "ret-old-flow-1").first()
    check_old_alert = db.query(SecurityEvent).filter(SecurityEvent.event_id == "ret-old-alert-1").first()
    check_rec_flow = db.query(SecurityEvent).filter(SecurityEvent.event_id == "ret-rec-flow-1").first()

    assert check_old_flow is None, "Aged flow event should have been deleted"
    assert check_old_alert is not None, "Aged alert event should be preserved"
    assert check_rec_flow is not None, "Recent flow event should be preserved"

    # Cleanup
    db.query(SecurityEvent).filter(SecurityEvent.event_id.in_(["ret-old-alert-1", "ret-rec-flow-1"])).delete()
    db.commit()


# ---------------------------------------------------------------------------
# 6. REST API Endpoints Tests
# ---------------------------------------------------------------------------
def test_monitoring_statistics_api(client):
    """Test GET /api/v1/monitoring/statistics."""
    resp = client.get("/api/v1/monitoring/statistics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_events" in data
    assert "total_alerts" in data
    assert "severity_distribution" in data
    assert "protocol_distribution" in data
    assert "top_signatures" in data


def test_security_events_and_alerts_api(client):
    """Test GET /api/v1/security-events and /api/v1/security-alerts."""
    resp_evts = client.get("/api/v1/security-events?page=1&page_size=10")
    assert resp_evts.status_code == 200
    data_evts = resp_evts.json()
    assert "items" in data_evts
    assert "total" in data_evts

    resp_alerts = client.get("/api/v1/security-alerts?page=1&page_size=10")
    assert resp_alerts.status_code == 200
    data_alerts = resp_alerts.json()
    assert "items" in data_alerts
    # All items returned by security-alerts must be alert type
    for item in data_alerts["items"]:
        assert item["event_type"] == "alert"


def test_pcap_analysis_api_validation(client):
    """Test POST /api/v1/monitoring/pcap validation."""
    # 1. Non-existent file
    resp = client.post("/api/v1/monitoring/pcap", json={"filename": "non_existent_file.pcap"})
    assert resp.status_code == 422

    # 2. Invalid extension
    resp2 = client.post("/api/v1/monitoring/pcap", json={"filename": "malicious.sh"})
    assert resp2.status_code == 422
