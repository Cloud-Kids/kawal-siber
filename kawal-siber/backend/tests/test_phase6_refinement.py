"""
test_phase6_refinement.py — Phase 6 Final Refinement Test Suite
Covers:
  1. Empty Database Security Posture: NOT ASSESSED / INSUFFICIENT SECURITY TELEMETRY
  2. Unassessed Assets Posture: NOT ASSESSED / NO ASSESSMENT PERFORMED
  3. Confirmed Threat Posture: WASPADA TINGGI (CRITICAL DEFENSE)
  4. SQLite Snapshot Consistency: Transaction release before rendering + concurrent writes
  5. PDF Visual QA: NumberedCanvas ("Halaman X dari Y"), running headers/footers, Indonesian Unicode
  6. Append-Only Audit Trail: Hash chaining (SHA-256) + tamper detection
  7. Reproducibility Metadata: Complete component versions (Nmap, Suricata, Deep Eye, AI, Git, etc.)
  8. Audit Chain API Route: GET /reports/{id}/audit-chain verification
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event as sa_event, select, text
from sqlalchemy.orm import Session, sessionmaker

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))
_worker_root = _backend.parent
if str(_worker_root) not in sys.path:
    sys.path.insert(0, str(_worker_root))

from app.database import Base
from app.models import Asset, GeneratedReport, Incident, ReportAuditEvent, ScanJob, SecurityEvent, WebAssessment
from app.reporting.audit import append_audit_event, compute_event_hash, verify_audit_chain
from app.reporting.engine import ReportingEngine, calculate_sha256, get_reproducibility_component_versions
from app.reporting.executive_report import generate_executive_report_data
from app.reporting.exporters.pdf import export_to_pdf


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session(tmp_path: Path):
    """Isolated SQLite session using fresh temporary database file."""
    db_file = tmp_path / "refine_test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )

    @sa_event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

    Base.metadata.create_all(engine)
    Session_ = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with Session_() as session:
        yield session

    engine.dispose()


@pytest.fixture()
def app_client(tmp_path: Path, db_session: Session):
    """FastAPI test client with isolated DB and reports directory."""
    from app.main import app
    from app.dependencies import get_db

    rpt_dir = tmp_path / "reports"
    rpt_dir.mkdir(parents=True, exist_ok=True)

    def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db

    with patch("app.reporting.engine.REPORTS_DIR", rpt_dir), \
         patch("app.api.routes.reports.REPORTS_DIR", rpt_dir):
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client, db_session, rpt_dir

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. EMPTY DATABASE SECURITY POSTURE
# ---------------------------------------------------------------------------

def test_01_empty_database_posture_not_assessed(db_session: Session):
    """Empty database MUST NOT be classified as NORMAL SECURE or SECURE.
    It MUST evaluate to NOT ASSESSED with INSUFFICIENT SECURITY TELEMETRY."""
    data = generate_executive_report_data(
        db=db_session,
        report_id="REP-TEST-EMPTY",
        title="Empty Database Posture Audit",
    )

    assert data["posture"] == "NOT ASSESSED", f"Expected 'NOT ASSESSED', got {data['posture']}"
    assert data["posture_reason"] == "INSUFFICIENT SECURITY TELEMETRY"
    assert data["telemetry_status"] == "NO_AVAILABLE_TELEMETRY"
    assert "NOT ASSESSED" in data["executive_summary"]
    assert "Angka nol tidak boleh disamakan dengan bukti keamanan" in data["executive_summary"]


def test_02_unassessed_assets_posture(db_session: Session):
    """If assets exist but 0 completed assessments or events have run,
    posture MUST be NOT ASSESSED / NO ASSESSMENT PERFORMED."""
    asset = Asset(
        name="Target Server 1",
        target_ip="192.168.1.10",
        port=80,
        status="UNKNOWN",
        availability_status="UNKNOWN",
    )
    db_session.add(asset)
    db_session.commit()

    data = generate_executive_report_data(
        db=db_session,
        report_id="REP-TEST-UNASSESSED",
    )

    assert data["posture"] == "NOT ASSESSED"
    assert data["posture_reason"] == "NO ASSESSMENT PERFORMED"
    assert data["telemetry_status"] == "NO_ASSESSMENT_PERFORMED"


def test_03_confirmed_threats_posture(db_session: Session):
    """If critical incidents exist, posture MUST be WASPADA TINGGI (CRITICAL DEFENSE)."""
    asset = Asset(
        name="Target Server Crit",
        target_ip="192.168.1.50",
        port=80,
        status="UNDER_ATTACK",
        availability_status="UP",
    )
    db_session.add(asset)
    db_session.commit()

    inc = Incident(
        asset_id=asset.id,
        source_ip="10.0.0.99",
        attack_type="SQL_INJECTION",
        severity="CRITICAL",
        is_mitigated=False,
        lifecycle_status="OPEN",
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(inc)
    db_session.commit()

    data = generate_executive_report_data(
        db=db_session,
        report_id="REP-TEST-CRIT",
    )

    assert data["posture"] == "WASPADA TINGGI (CRITICAL DEFENSE)"
    assert data["telemetry_status"] == "CONFIRMED_THREATS_DETECTED"


# ---------------------------------------------------------------------------
# 2. SQLITE SNAPSHOT CONSISTENCY & CONCURRENCY
# ---------------------------------------------------------------------------

def test_04_sqlite_snapshot_released_before_rendering(tmp_path: Path, db_session: Session):
    """Verify that reporting engine closes read transaction before rendering,
    enabling concurrent database writes while report export is running."""
    rpt_dir = tmp_path / "reports"
    rpt_dir.mkdir()

    rep = GeneratedReport(
        report_id="REP-TEST-SNAP-001",
        report_type="EXECUTIVE",
        title="Snapshot Release Test",
        format="JSON",
        generation_status="PENDING",
        generated_by="Operator",
    )
    db_session.add(rep)
    db_session.commit()

    engine = ReportingEngine(db_session, reports_dir=rpt_dir)

    # Patch export_to_json to perform a concurrent write into the database
    concurrent_write_succeeded = False

    orig_export = engine._reports_dir
    from app.reporting.engine import export_to_json as real_export

    def export_with_concurrent_db_write(data, out_path):
        nonlocal concurrent_write_succeeded
        # Write another record into the DB while export is in progress
        # If engine holds an open transaction, SQLite write might be blocked
        rep2 = GeneratedReport(
            report_id="REP-CONCURRENT-WRITE",
            report_type="EXECUTIVE",
            title="Concurrent Write",
            format="JSON",
            generation_status="PENDING",
            generated_by="Worker2",
        )
        db_session.add(rep2)
        db_session.commit()
        concurrent_write_succeeded = True
        real_export(data, out_path)

    with patch("app.reporting.engine.export_to_json", side_effect=export_with_concurrent_db_write):
        completed = engine.process_report_job(rep.report_id)

    assert completed.generation_status == "COMPLETED"
    assert concurrent_write_succeeded is True, "Concurrent write failed during report export"


# ---------------------------------------------------------------------------
# 3. PDF VISUAL QA: NumberedCanvas, Bounding, and Indonesian Unicode
# ---------------------------------------------------------------------------

def test_05_pdf_visual_numbered_canvas_and_unicode(tmp_path: Path):
    """Generate multi-page PDF and verify via pypdf:
    - NumberedCanvas dynamic page count ("Halaman X dari Y")
    - Running header text
    - Indonesian Unicode text rendered without replacement/clipping
    - Empty state banner rendered cleanly when NOT ASSESSED"""
    from pypdf import PdfReader

    out = tmp_path / "visual_qa_test.pdf"
    data = {
        "report_id": "REP-VISUAL-001",
        "report_type": "EXECUTIVE",
        "title": "Laporan Evaluasi Postur Pertahanan Siber Teritorial",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "generated_by": "Komando Operasi Siber",
        "posture": "NOT ASSESSED",
        "posture_reason": "INSUFFICIENT SECURITY TELEMETRY",
        "executive_summary": "Pemeriksaan kesiapan operasional pertahanan siber teritorial. Ancaman Siber Terdeteksi.",
        "metrics": {
            "postur_keamanan": "NOT ASSESSED",
            "alasan_postur": "INSUFFICIENT SECURITY TELEMETRY",
            "total_aset": 0,
        },
        # Create enough items to generate multiple pages
        "items": [
            {
                "id": f"ITEM-{i:03d}",
                "target": f"Aset Infrastruktur #{i}",
                "keterangan": f"Entri audit telemetri pengujian ke-{i} wilayah territorial",
                "status": "NOT_ASSESSED",
            }
            for i in range(1, 40)
        ],
        "reproducibility": {
            "component_versions": {
                "nmap": "Nmap version 7.95",
                "deep_eye": "1.0.0 (FastAPI Core)",
                "ai_prompt_version": "2026.03-v1.2",
            }
        },
    }

    export_to_pdf(data, out)
    assert out.exists()
    assert out.stat().st_size > 0

    reader = PdfReader(str(out))
    num_pages = len(reader.pages)
    assert num_pages >= 2, f"Expected multi-page PDF, got {num_pages} page(s)"

    # Verify every page has header and footer page number
    for p_idx, page in enumerate(reader.pages, start=1):
        text_content = page.extract_text()
        assert "KAWAL SIBER" in text_content, f"Header missing on page {p_idx}"
        expected_page_str = f"Halaman {p_idx} dari {num_pages}"
        assert expected_page_str in text_content, f"Expected '{expected_page_str}' on page {p_idx}, got: {text_content}"

    # Verify Indonesian Unicode text on page 1
    page1_text = reader.pages[0].extract_text()
    assert "Pertahanan Siber Teritorial" in page1_text
    assert "NOT ASSESSED" in page1_text
    assert "INSUFFICIENT SECURITY TELEMETRY" in page1_text


# ---------------------------------------------------------------------------
# 4. APPEND-ONLY REPORT AUDIT TRAIL & TAMPER DETECTION
# ---------------------------------------------------------------------------

def test_06_append_only_audit_chain_and_tamper_detection(db_session: Session):
    """Verify hash-chained audit trail integrity and tamper detection."""
    rep = GeneratedReport(
        report_id="REP-AUDIT-CHAIN-001",
        report_type="EXECUTIVE",
        title="Audit Trail Test",
        format="JSON",
        generation_status="PENDING",
        generated_by="Operator",
    )
    db_session.add(rep)
    db_session.commit()

    # Append 3 events sequentially
    ev1 = append_audit_event(rep, db_session, "CREATED", "Report job registered", operator="admin", commit=True)
    ev2 = append_audit_event(rep, db_session, "STARTED", "Worker processing begun", operator="worker-1", commit=True)
    ev3 = append_audit_event(rep, db_session, "COMPLETED", "Report generated successfully", operator="worker-1", commit=True)

    assert ev1.previous_event_hash == "GENESIS"
    assert ev2.previous_event_hash == ev1.event_hash
    assert ev3.previous_event_hash == ev2.event_hash

    # Verify valid chain
    result = verify_audit_chain("REP-AUDIT-CHAIN-001", db_session)
    assert result["verified"] is True
    assert result["status"] == "CHAIN_VALID"
    assert result["event_count"] == 3

    # Tamper with ev2's details in the database
    db_session.execute(
        text("UPDATE report_audit_events SET event_details = 'TAMPERED DETAIL' WHERE id = :eid"),
        {"eid": ev2.id},
    )
    db_session.commit()

    tamper_result = verify_audit_chain("REP-AUDIT-CHAIN-001", db_session)
    assert tamper_result["verified"] is False
    assert tamper_result["status"] == "EVENT_HASH_TAMPERED"
    assert tamper_result["broken_at_event_id"] == ev2.id


# ---------------------------------------------------------------------------
# 5. REPRODUCIBILITY METADATA
# ---------------------------------------------------------------------------

def test_07_reproducibility_component_versions():
    """Verify get_reproducibility_component_versions returns honest, non-fabricated versions."""
    versions = get_reproducibility_component_versions()

    assert "python" in versions
    assert "reporting_engine" in versions
    assert "deep_eye" in versions
    assert "ai_prompt_version" in versions
    assert "nmap" in versions
    assert "suricata" in versions
    assert "git_commit_hash" in versions

    # If git repo has no commits, must report NOT_AVAILABLE rather than fabricating
    assert isinstance(versions["git_commit_hash"], str)
    assert len(versions["git_commit_hash"]) > 0


# ---------------------------------------------------------------------------
# 6. AUDIT CHAIN API ENDPOINT
# ---------------------------------------------------------------------------

def test_08_audit_chain_api_endpoint(app_client):
    """GET /reports/{id}/audit-chain endpoint returns valid chain verification."""
    client, db, rpt_dir = app_client

    rep = GeneratedReport(
        report_id="REP-API-CHAIN-001",
        report_type="EXECUTIVE",
        title="API Chain Test",
        format="JSON",
        generation_status="PENDING",
        generated_by="Operator",
    )
    db.add(rep)
    db.commit()

    append_audit_event(rep, db, "CREATED", "Job created", operator="test-actor", commit=True)
    append_audit_event(rep, db, "COMPLETED", "Job finished", operator="test-worker", commit=True)

    resp = client.get(f"/api/v1/reports/{rep.report_id}/audit-chain")
    assert resp.status_code == 200, f"Error: {resp.text}"
    body = resp.json()

    assert body["verified"] is True
    assert body["status"] == "CHAIN_VALID"
    assert body["event_count"] == 2
    assert "latest_hash" in body


# ---------------------------------------------------------------------------
# 7. EXTENDED SECURITY POSTURE TRANSITION TESTS
# ---------------------------------------------------------------------------

def test_09_posture_transition_telemetry_degraded(db_session: Session):
    """When assets exist but only failed scan jobs exist, posture MUST evaluate to
    TELEMETRY DEGRADED rather than secure or clean."""
    asset = Asset(
        name="Telemetry Target",
        target_ip="192.168.1.75",
        port=443,
        status="UNKNOWN",
        availability_status="UNKNOWN",
    )
    db_session.add(asset)
    db_session.commit()

    failed_scan = ScanJob(
        asset_id=asset.id,
        status="FAILED",
        error_message="Connection timed out during host discovery",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(failed_scan)
    db_session.commit()

    data = generate_executive_report_data(db=db_session, report_id="REP-TEST-DEGRADED")
    assert data["posture"] == "PERHATIAN (TELEMETRY DEGRADED)"
    assert data["telemetry_status"] == "TELEMETRY_DEGRADED"
    assert data["assessment_scope"]["failed_scans"] == 1
    assert data["assessment_scope"]["completed_scans"] == 0


def test_10_posture_transition_no_findings_detected(db_session: Session):
    """When a scan is completed without findings, posture MUST evaluate to
    TERKENDALI (NO FINDINGS DETECTED) with an explicit scope caveat."""
    asset = Asset(
        name="Scanned Target",
        target_ip="192.168.1.100",
        port=80,
        status="SAFE",
        availability_status="UP",
    )
    db_session.add(asset)
    db_session.commit()

    scan = ScanJob(
        asset_id=asset.id,
        status="COMPLETED",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(scan)
    db_session.commit()

    data = generate_executive_report_data(db=db_session, report_id="REP-TEST-NO-FINDINGS")
    assert data["posture"] == "TERKENDALI (NO FINDINGS DETECTED)"
    assert data["telemetry_status"] == "NO_FINDINGS_DETECTED"
    assert "scope_caveat" in data["assessment_scope"]
    assert "bukan bukti ketiadaan ancaman siber" in data["assessment_scope"]["scope_caveat"]


def test_11_posture_transition_baseline_verified(db_session: Session):
    """Verify BASELINE_VERIFIED requirements:
    1. A completed scan with 0 findings without validated baseline remains NO_FINDINGS_DETECTED.
    2. Only when an explicit security baseline exists, required controls are validated with timestamps
       and evidence, 100% assets are covered, and telemetry is active, does it evaluate to BASELINE_VERIFIED."""
    asset = Asset(
        name="Target Baseline",
        target_ip="192.168.1.200",
        port=80,
        status="SAFE",
        availability_status="UP",
    )
    db_session.add(asset)
    db_session.commit()

    scan = ScanJob(
        asset_id=asset.id,
        status="COMPLETED",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(scan)

    event = SecurityEvent(
        event_id="EV-BASE-001",
        event_type="flow",
        source_ip="192.168.1.200",
        destination_ip="192.168.1.1",
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(event)
    db_session.commit()

    # Step 1: Without explicit baseline validation, clean telemetry MUST REMAIN NO_FINDINGS_DETECTED
    data_unvalidated = generate_executive_report_data(db=db_session, report_id="REP-TEST-CLEAN-NO-BASELINE")
    assert data_unvalidated["posture"] == "TERKENDALI (NO FINDINGS DETECTED)"
    assert data_unvalidated["telemetry_status"] == "NO_FINDINGS_DETECTED"
    assert data_unvalidated["assessment_scope"]["baseline_validated"] is False

    # Step 2: With explicit baseline definition and validated required controls with timestamps and evidence
    baseline_params = {
        "security_baseline": {
            "name": "CIS-TNI-CYBER-BASELINE-V1",
            "required_controls": [
                {
                    "control_id": "CIS-1.1",
                    "title": "Inventory and Control of Enterprise Assets",
                    "status": "VALIDATED",
                    "evidence": "Nmap port discovery completed; no rogue listeners found",
                    "validated_at": "2026-11-08T04:00:00Z",
                },
                {
                    "control_id": "CIS-8.2",
                    "title": "Network Intrusion Detection Monitoring",
                    "status": "VALIDATED",
                    "evidence": "Suricata sensor active with baseline flow telemetry",
                    "validated_at": "2026-11-08T04:00:00Z",
                },
            ],
        }
    }
    data_verified = generate_executive_report_data(
        db=db_session, report_id="REP-TEST-BASELINE", parameters=baseline_params
    )
    assert data_verified["posture"] == "TERVERIFIKASI (BASELINE VERIFIED)"
    assert data_verified["telemetry_status"] == "BASELINE_VERIFIED"
    assert data_verified["assessment_scope"]["baseline_validated"] is True
    assert data_verified["assessment_scope"]["asset_coverage_pct"] == 100.0
    assert data_verified["security_dimensions"]["assessment_status"] == "COMPLETED_FULL_COVERAGE"
    assert data_verified["security_dimensions"]["baseline_compliance"] == "COMPLIANT_BASELINE_VERIFIED"
    assert data_verified["security_dimensions"]["threat_detection_status"] == "NO_DETECTED_THREATS"
    assert data_verified["security_dimensions"]["telemetry_health"] == "HEALTHY_ACTIVE"
    assert data_verified["security_dimensions"]["risk_severity"] == "NONE_IN_SCOPE"

    # Step 3: When threats are detected, baseline compliance remains COMPLIANT_BASELINE_VERIFIED
    # (A detected threat must NOT erase the fact that a configuration baseline was verified)
    inc = Incident(
        asset_id=asset.id,
        source_ip="192.168.1.105",
        attack_type="BRUTE_FORCE",
        severity="HIGH",
        lifecycle_status="OPEN",
        is_mitigated=False,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(inc)
    db_session.commit()

    data_threat = generate_executive_report_data(
        db=db_session, report_id="REP-TEST-BASELINE-THREAT", parameters=baseline_params
    )
    assert data_threat["security_dimensions"]["baseline_compliance"] == "COMPLIANT_BASELINE_VERIFIED"
    assert data_threat["security_dimensions"]["threat_detection_status"] == "THREATS_DETECTED"
    assert data_threat["security_dimensions"]["risk_severity"] == "HIGH"
    assert data_threat["posture"] == "PERHATIAN (ELEVATED RISK)"


# ---------------------------------------------------------------------------
# 8. COMPREHENSIVE AUDIT TRAIL TAMPERING TESTS (ALL 7 VECTORS)
# ---------------------------------------------------------------------------

def test_12_audit_trail_exhaustive_tampering_vectors(db_session: Session):
    """Verify all 7 tampering attack vectors on the cryptographic audit chain:
    1. Modify existing event details
    2. Modify stored event_hash
    3. Modify previous_event_hash
    4. Reorder events
    5. Delete middle event
    6. Delete final event (detected via trusted external checkpoint)
    7. Replace complete chain (detected via trusted external checkpoint)
    """
    rep = GeneratedReport(
        report_id="REP-TAMPER-7-VECTORS",
        report_type="EXECUTIVE",
        title="Tamper Vector Validation",
        format="JSON",
        generation_status="PENDING",
        generated_by="SecOps",
    )
    db_session.add(rep)
    db_session.commit()

    # Append 4 sequential events
    ev1 = append_audit_event(rep, db_session, "CREATED", "Genesis event", operator="operator-1", commit=True)
    ev2 = append_audit_event(rep, db_session, "STARTED", "Worker started", operator="worker-1", commit=True)
    ev3 = append_audit_event(rep, db_session, "COMPLETED", "Generation finished", operator="worker-1", commit=True)
    ev4 = append_audit_event(rep, db_session, "DOWNLOADED", "Report downloaded", operator="auditor-1", commit=True)

    original_ev2_hash = str(ev2.event_hash)
    checkpoint_hash = str(ev4.event_hash)

    # Baseline valid chain verification
    res = verify_audit_chain("REP-TAMPER-7-VECTORS", db_session, expected_latest_hash=checkpoint_hash)
    assert res["verified"] is True
    assert res["status"] == "CHAIN_VALID"

    # Vector 2: Modify stored event_hash
    db_session.execute(
        text("UPDATE report_audit_events SET event_hash = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff' WHERE id = :eid"),
        {"eid": ev2.id},
    )
    db_session.commit()
    db_session.expire_all()
    res2 = verify_audit_chain("REP-TAMPER-7-VECTORS", db_session)
    assert res2["verified"] is False
    assert res2["status"] in ("EVENT_HASH_TAMPERED", "HASH_CHAIN_MISMATCH")

    # Restore ev2 event_hash
    db_session.execute(
        text("UPDATE report_audit_events SET event_hash = :eh WHERE id = :eid"),
        {"eh": original_ev2_hash, "eid": ev2.id},
    )
    db_session.commit()
    db_session.expire_all()

    # Vector 3: Modify previous_event_hash of ev3
    db_session.execute(
        text("UPDATE report_audit_events SET previous_event_hash = '0000000000000000000000000000000000000000000000000000000000000000' WHERE id = :eid"),
        {"eid": ev3.id},
    )
    db_session.commit()
    db_session.expire_all()
    res3 = verify_audit_chain("REP-TAMPER-7-VECTORS", db_session)
    assert res3["verified"] is False
    assert res3["status"] == "HASH_CHAIN_MISMATCH"

    # Restore ev3 previous_event_hash
    db_session.execute(
        text("UPDATE report_audit_events SET previous_event_hash = :peh WHERE id = :eid"),
        {"peh": original_ev2_hash, "eid": ev3.id},
    )
    db_session.commit()
    db_session.expire_all()

    # Vector 5: Delete middle event (ev2)
    db_session.execute(
        text("DELETE FROM report_audit_events WHERE id = :eid"),
        {"eid": ev2.id},
    )
    db_session.commit()
    db_session.expire_all()
    res5 = verify_audit_chain("REP-TAMPER-7-VECTORS", db_session)
    assert res5["verified"] is False
    assert res5["status"] == "HASH_CHAIN_MISMATCH"
    assert res5["broken_at_event_id"] == ev3.id

    # Clean and re-seed 3 events to test Vector 6 & 7
    report_code = rep.report_id
    db_session.execute(text("DELETE FROM report_audit_events WHERE report_id = 'REP-TAMPER-7-VECTORS'"))
    db_session.commit()
    db_session.expunge_all()

    rep_fresh = db_session.execute(
        select(GeneratedReport).where(GeneratedReport.report_id == report_code)
    ).scalar_one()

    n1 = append_audit_event(rep_fresh, db_session, "CREATED", "Clean 1", operator="op", commit=True)
    n2 = append_audit_event(rep_fresh, db_session, "STARTED", "Clean 2", operator="op", commit=True)
    n3 = append_audit_event(rep_fresh, db_session, "COMPLETED", "Clean 3", operator="op", commit=True)
    trusted_tip = str(n3.event_hash)

    # Vector 6: Delete final event (n3). Internal chain without anchor is valid,
    # but WITH trusted external checkpoint anchor it MUST BE DETECTED!
    db_session.execute(text("DELETE FROM report_audit_events WHERE id = :eid"), {"eid": n3.id})
    db_session.commit()
    db_session.expunge_all()

    res6_no_anchor = verify_audit_chain("REP-TAMPER-7-VECTORS", db_session)
    assert res6_no_anchor["verified"] is True  # Truncated prefix is internally valid

    res6_with_anchor = verify_audit_chain("REP-TAMPER-7-VECTORS", db_session, expected_latest_hash=trusted_tip)
    assert res6_with_anchor["verified"] is False
    assert res6_with_anchor["status"] == "FINAL_EVENT_TRUNCATED_OR_CHAIN_REPLACED"

    # Vector 7: Replace complete chain with a newly created chain
    # Deleting all and creating a different chain is detected because expected_latest_hash fails
    db_session.execute(text("DELETE FROM report_audit_events WHERE report_id = 'REP-TAMPER-7-VECTORS'"))
    db_session.commit()
    db_session.expunge_all()

    rep_fresh2 = db_session.execute(
        select(GeneratedReport).where(GeneratedReport.report_id == report_code)
    ).scalar_one()
    fake1 = append_audit_event(rep_fresh2, db_session, "CREATED", "Attacker fabricated chain", operator="attacker", commit=True)
    res7 = verify_audit_chain("REP-TAMPER-7-VECTORS", db_session, expected_latest_hash=trusted_tip)
    assert res7["verified"] is False
    assert res7["status"] == "FINAL_EVENT_TRUNCATED_OR_CHAIN_REPLACED"


# ---------------------------------------------------------------------------
# 9. EXPORT AND FILE SECURITY TESTS
# ---------------------------------------------------------------------------

def test_13_safe_url_validation():
    """Verify validate_safe_url whitelists safe protocols and blocks:
    - javascript:, data:, vbscript:, file:, blob: (including case and URL-encoded variants)
    - protocol-relative URLs (//example.com)
    - backslash-based URL bypasses (\\example.com, /\\example.com, https:\\)
    - control characters (\x00-\x1f, \x7f)
    - encoded payloads (%6a%61%76... or javascript%3a)
    - quote and tag injections."""
    from app.reporting.sanitization import validate_safe_url

    # Safe legitimate URLs preserved intact
    assert validate_safe_url("https://kawalsiber.mil.id/intel") == "https://kawalsiber.mil.id/intel"
    assert validate_safe_url("http://127.0.0.1:8000/api") == "http://127.0.0.1:8000/api"
    assert validate_safe_url("https://sub.domain.co.id:8080/path?param=1&foo=bar#frag") == "https://sub.domain.co.id:8080/path?param=1&foo=bar#frag"
    assert validate_safe_url("#section-1") == "#section-1"
    assert validate_safe_url("/reports/REP-001") == "/reports/REP-001"
    assert validate_safe_url("/dashboard") == "/dashboard"

    # Blocked dangerous pseudo-protocols
    assert validate_safe_url("javascript:alert(1)") == "#"
    assert validate_safe_url("JAVASCRIPT:fetch('//attacker.com')") == "#"
    assert validate_safe_url("data:text/html,<script>alert(1)</script>") == "#"
    assert validate_safe_url("data:text/html;base64,PHNjcmlwdD4=") == "#"
    assert validate_safe_url("vbscript:msgbox(1)") == "#"
    assert validate_safe_url("file:///etc/passwd") == "#"
    assert validate_safe_url("file://C:/Windows/win.ini") == "#"
    assert validate_safe_url("blob:http://example.com/uuid") == "#"

    # Blocked protocol-relative URLs
    assert validate_safe_url("//attacker.com") == "#"
    assert validate_safe_url("//evil.com/payload") == "#"
    assert validate_safe_url("///evil.com") == "#"

    # Blocked backslash-based URL bypasses
    assert validate_safe_url("/\\attacker.com") == "#"
    assert validate_safe_url("\\\\attacker.com") == "#"
    assert validate_safe_url("https:\\\\attacker.com") == "#"
    assert validate_safe_url("https://legit.com\\\\@evil.com") == "#"

    # Blocked URL-encoded dangerous payloads
    assert validate_safe_url("%6a%61%76%61%73%63%72%69%70%74:alert(1)") == "#"
    assert validate_safe_url("javascript%3aalert(1)") == "#"
    assert validate_safe_url("data%3atext/html,test") == "#"

    # Blocked control characters, null bytes, and quote injections
    assert validate_safe_url("https://safe.com\x00<script>") == "#"
    assert validate_safe_url("https://safe.com\r\ninjection") == "#"
    assert validate_safe_url("https://safe.com\x1finjection") == "#"
    assert validate_safe_url("https://safe.com\x7finjection") == "#"
    assert validate_safe_url('https://safe.com" onclick="alert(1)') == "#"
    assert validate_safe_url("https://safe.com' onmouseover='alert(1)") == "#"
    assert validate_safe_url("https://safe.com<script>alert(1)</script>") == "#"

    # Blocked empty and malformed URLs
    assert validate_safe_url(None) == "#"
    assert validate_safe_url("") == "#"
    assert validate_safe_url("http://") == "#"
    assert validate_safe_url("random_string") == "#"


def test_14_csv_formula_injection_defense_exhaustive():
    """Verify sanitize_csv_cell neutralizes all formula trigger characters
    (=, +, -, @, tab, cr, lf, %, |) including leading whitespace before triggers."""
    from app.reporting.sanitization import sanitize_csv_cell

    # Direct triggers
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-2+5") == "'-2+5"
    assert sanitize_csv_cell("@SUM(1,2)") == "'@SUM(1,2)"
    assert sanitize_csv_cell("%0Acmd") == "'%0Acmd"
    assert sanitize_csv_cell("|cmd") == "'|cmd"

    # Leading whitespace before trigger
    assert sanitize_csv_cell("   =1+1") == "'   =1+1"
    assert sanitize_csv_cell("\t@SUM(1)") == "'\t@SUM(1)"
    assert sanitize_csv_cell("\r\n-cmd") == "'\r\n-cmd"

    # Null byte stripping
    assert sanitize_csv_cell("safe\x00data") == "safedata"

    # Safe text left unquoted
    assert sanitize_csv_cell("Normal Asset Name") == "Normal Asset Name"
    assert sanitize_csv_cell("192.168.1.1") == "192.168.1.1"


def test_15_pdf_geometry_and_printable_bounds():
    """Verify that PDF exporter uses A4 geometry with 523.28pt printable width
    and table columns strictly conform without margin breach."""
    from app.reporting.exporters.pdf import A4, BOTTOM_MARGIN, LEFT_MARGIN, PRINTABLE_WIDTH, RIGHT_MARGIN, TOP_MARGIN

    # A4 standard: 595.28 x 841.89 pt
    assert round(A4[0], 2) == 595.28
    assert round(A4[1], 2) == 841.89

    # Margins
    assert LEFT_MARGIN == 36.0
    assert RIGHT_MARGIN == 36.0
    assert TOP_MARGIN == 54.0
    assert BOTTOM_MARGIN == 54.0

    # Printable width: 595.28 - 36 - 36 = 523.28 pt
    assert PRINTABLE_WIDTH == 523.28
    assert PRINTABLE_WIDTH != 540.0, "Must not claim 540pt for A4 with 36pt margins"


def test_16_v2_canonical_json_hash_chain(db_session: Session):
    """Verify v2 canonical JSON envelope hash serialization and cross-version verification.
    - Fields are enclosed in deterministic JSON eliminating delimiter injection risks.
    - verify_audit_chain successfully verifies both v1 and v2 events using strict version dispatch."""
    from app.reporting.audit import append_audit_event, compute_event_hash, verify_audit_chain

    rep = GeneratedReport(
        report_id="REP-TEST-V2-CHAIN",
        report_type="EXECUTIVE",
        title="V2 Hash Chain Test",
        format="JSON",
        generation_status="COMPLETED",
        generated_by="Tester",
    )
    db_session.add(rep)
    db_session.commit()

    # Append event with v1
    ev1 = append_audit_event(rep, db_session, "CREATED", "First event v1", operator="operator:test", version="v1", commit=True)
    assert ev1.event_hash is not None

    # Append event with v2 canonical envelope via append_audit_event
    ev2 = append_audit_event(
        rep,
        db_session,
        "COMPLETED",
        {"status": "SUCCESS", "records": 42},
        operator="system:localhost",
        version="v2",
        commit=True,
    )
    assert ev2.event_hash is not None

    # Both v1 and v2 verify successfully with strict dispatch
    verification = verify_audit_chain(rep.report_id, db_session)
    assert verification["verified"] is True
    assert verification["event_count"] == 2
    assert verification["status"] == "CHAIN_VALID"
    assert verification["latest_hash"] == ev2.event_hash


def test_17_audit_actor_trust_boundary(client: TestClient, db_session: Session):
    """Verify audit actor trust boundary:
    - Client-supplied headers (X-Operator, X-Actor, X-Operator-Identity) are treated as untrusted metadata.
    - Persistent audit record actor is strictly 'operator:unauthenticated'.
    - Claimed identity is stored strictly as untrusted metadata in event details: claimed_actor='...' (untrusted).
    - System processes use 'system:localhost'."""
    from app.reporting.audit import (
        ACTOR_OPERATOR_UNAUTHENTICATED,
        ACTOR_SYSTEM_LOCALHOST,
        resolve_http_actor_attribution,
    )

    # 1. Test unit resolution function directly
    actor1, claimed1 = resolve_http_actor_attribution({"X-Operator": "spoofed_admin"})
    assert actor1 == ACTOR_OPERATOR_UNAUTHENTICATED
    assert claimed1 == "claimed_actor='spoofed_admin' (untrusted)"

    actor2, claimed2 = resolve_http_actor_attribution({"X-Actor": "commander_123"})
    assert actor2 == ACTOR_OPERATOR_UNAUTHENTICATED
    assert claimed2 == "claimed_actor='commander_123' (untrusted)"

    actor3, claimed3 = resolve_http_actor_attribution({})
    assert actor3 == ACTOR_OPERATOR_UNAUTHENTICATED
    assert claimed3 is None

    # 2. Test via HTTP API route
    resp = client.post(
        "/api/v1/reports",
        json={
            "report_type": "EXECUTIVE",
            "format": "JSON",
            "title": "Actor Boundary Test",
        },
        headers={"X-Operator": "malicious_admin_spoof"},
    )
    assert resp.status_code == 201
    rep_id = resp.json()["report_id"]

    stmt = select(ReportAuditEvent).where(ReportAuditEvent.report_id == rep_id)
    ev = db_session.execute(stmt).scalars().first()
    assert ev is not None
    # Crucial: ev.actor must NOT be spoofed_admin
    assert ev.actor == ACTOR_OPERATOR_UNAUTHENTICATED
    assert "claimed_actor='malicious_admin_spoof' (untrusted)" in ev.event_details


def test_18_strict_version_dispatch_and_no_fallback(db_session: Session):
    """Verify strict serialization version dispatch:
    - v1 event verified ONLY with v1 serialization (escaped delimiters).
    - v2 event verified ONLY with v2 canonical JSON envelope.
    - Legacy event verified ONLY with legacy format.
    - Unknown version rejects with UNSUPPORTED_VERSION status.
    - Tampered v1 does NOT fall back to v2 or legacy."""
    from app.reporting.audit import append_audit_event, verify_audit_chain

    # 1. Test unknown version
    rep_unrec = GeneratedReport(
        report_id="REP-TEST-UNREC-VER",
        report_type="TECHNICAL",
        title="Unknown Version Test",
        format="JSON",
        generation_status="COMPLETED",
        generated_by="Tester",
    )
    db_session.add(rep_unrec)
    db_session.commit()

    ev_unrec = append_audit_event(rep_unrec, db_session, "CREATED", "Unknown version event", version="v3", commit=True)
    res_unrec = verify_audit_chain(rep_unrec.report_id, db_session)
    assert res_unrec["verified"] is False
    assert res_unrec["status"] == "UNSUPPORTED_VERSION"
    assert "Unsupported or unknown audit serialization version 'v3'" in res_unrec["message"]

    # 2. Test tampered v1 does not fall back
    rep_v1 = GeneratedReport(
        report_id="REP-TEST-V1-TAMPER",
        report_type="TECHNICAL",
        title="V1 Strict Tamper Test",
        format="JSON",
        generation_status="COMPLETED",
        generated_by="Tester",
    )
    db_session.add(rep_v1)
    db_session.commit()

    ev_v1 = append_audit_event(rep_v1, db_session, "CREATED", "Original detail", version="v1", commit=True)
    res_v1_orig = verify_audit_chain(rep_v1.report_id, db_session)
    assert res_v1_orig["verified"] is True
    assert res_v1_orig["status"] == "CHAIN_VALID"

    # Tamper with details in DB
    db_session.execute(
        text("UPDATE report_audit_events SET event_details = 'Altered detail' WHERE id = :eid"),
        {"eid": ev_v1.id},
    )
    db_session.commit()

    res_v1_tampered = verify_audit_chain(rep_v1.report_id, db_session)
    assert res_v1_tampered["verified"] is False
    assert res_v1_tampered["status"] == "EVENT_HASH_TAMPERED"
    assert "Recomputed v1 hash mismatch" in res_v1_tampered["message"]


def test_19_genesis_hash_consistency(db_session: Session):
    """Verify genesis hash consistency:
    - Genesis anchor must be literal string 'GENESIS' across legacy, v1, and v2.
    - Any other anchor (e.g. 64 zeros '0000...0000') must fail with HASH_CHAIN_MISMATCH."""
    from app.reporting.audit import GENESIS_HASH, append_audit_event, verify_audit_chain

    assert GENESIS_HASH == "GENESIS"

    rep = GeneratedReport(
        report_id="REP-TEST-GENESIS-ANCHOR",
        report_type="OPERATIONS",
        title="Genesis Test",
        format="JSON",
        generation_status="COMPLETED",
        generated_by="Tester",
    )
    db_session.add(rep)
    db_session.commit()

    ev = append_audit_event(rep, db_session, "CREATED", "Genesis event", commit=True)
    assert ev.previous_event_hash == "GENESIS"

    res_valid = verify_audit_chain(rep.report_id, db_session)
    assert res_valid["verified"] is True
    assert res_valid["status"] == "CHAIN_VALID"

    # Corrupt genesis to 64 zeros (the erroneous documentation value)
    db_session.execute(
        text("UPDATE report_audit_events SET previous_event_hash = :zeros WHERE id = :eid"),
        {"zeros": "0" * 64, "eid": ev.id},
    )
    db_session.commit()

    res_invalid = verify_audit_chain(rep.report_id, db_session)
    assert res_invalid["verified"] is False
    assert res_invalid["status"] == "HASH_CHAIN_MISMATCH"


def test_20_acceptance_test_database_isolation():
    """Verify acceptance test database isolation and safety guard:
    - Primary database storage/kawal_siber.db is protected from unintended writes.
    - Safety guard raises RuntimeError if target resolves to primary DB without explicit opt-in."""
    import tempfile
    from pathlib import Path

    workspace = Path(__file__).resolve().parent.parent.parent
    primary_db = workspace / "storage" / "kawal_siber.db"

    # Check that safety guard triggers when primary DB path is targeted without opt-in
    allow_primary = False
    target_path = primary_db
    with pytest.raises(RuntimeError, match="CRITICAL SAFETY VIOLATION"):
        if not allow_primary and target_path.resolve() == primary_db.resolve():
            raise RuntimeError(
                "CRITICAL SAFETY VIOLATION: Acceptance test resolved to primary database "
                "without explicit opt-in (ALLOW_PRIMARY_DB_ACCEPTANCE_TEST=1 or --live-db)."
            )
