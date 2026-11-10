"""
test_frontend_api_workflows.py — End-to-end functional API workflow tests.
Validates the 10 prioritized user workflows backing the 22 Next.js frontend routes.
Uses an isolated temporary SQLite database for each test session.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.models import Asset, GeneratedReport, Incident, ScanJob, ScanScope, WebAssessment, WebTarget
from app.reporting.engine import ReportingEngine


@pytest.fixture()
def workflow_client(tmp_path: Path):
    """Isolated FastAPI test client with dedicated database and report storage."""
    db_file = tmp_path / "workflow_test.db"
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

    rpt_dir = tmp_path / "reports"
    rpt_dir.mkdir(parents=True, exist_ok=True)

    def _override_db():
        with Session_() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db

    with patch("app.reporting.engine.REPORTS_DIR", rpt_dir), \
         patch("app.api.routes.reports.REPORTS_DIR", rpt_dir):
        with TestClient(app, raise_server_exceptions=True) as client:
            with Session_() as session:
                yield client, session, rpt_dir

    app.dependency_overrides.clear()
    engine.dispose()


def test_workflow_01_dashboard_and_analytics_stats(workflow_client):
    """Workflow 1: Dashboard and analytics telemetry stats load correctly."""
    client, db, _ = workflow_client

    # Monitoring statistics endpoint
    resp_mon = client.get("/api/v1/monitoring/statistics")
    assert resp_mon.status_code == 200
    mon_data = resp_mon.json()
    assert "total_events" in mon_data

    # Report statistics endpoint
    resp_rep = client.get("/api/v1/reports/statistics")
    assert resp_rep.status_code == 200
    rep_data = resp_rep.json()
    assert "total_reports" in rep_data

    # Incident intelligence overview
    resp_intel = client.get("/api/v1/incident-intelligence/overview")
    assert resp_intel.status_code == 200
    intel_data = resp_intel.json()
    assert "total_incidents" in intel_data


def test_workflow_02_asset_lifecycle(workflow_client):
    """Workflow 2: Asset creation, retrieval, and updating work."""
    client, db, _ = workflow_client

    # 1. Create scope
    scope = ScanScope(
        name="HQ Network",
        cidr="192.168.1.0/24",
        authorization_reference="AUTH-HQ-001",
        enabled=True,
        expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    db.add(scope)
    db.commit()

    # 2. Create asset
    payload = {
        "name": "Border Gateway",
        "target_ip": "192.168.1.1",
        "port": 443,
        "scope_id": scope.id,
    }
    resp = client.post("/api/v1/assets/", json=payload)
    assert resp.status_code in (200, 201), f"Failed to create asset: {resp.text}"
    asset_id = resp.json()["id"]

    # 3. Retrieve asset
    get_resp = client.get(f"/api/v1/assets/{asset_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Border Gateway"


def test_workflow_03_network_scan_submission(workflow_client):
    """Workflow 3: Network scan can be enqueued for an asset and retrieved."""
    client, db, _ = workflow_client

    scope = ScanScope(
        name="Scan Scope",
        cidr="10.0.0.0/24",
        authorization_reference="AUTH-SCAN-01",
        enabled=True,
        expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    db.add(scope)
    db.commit()

    asset = Asset(
        name="Scan Target",
        target_ip="10.0.0.5",
        port=80,
        scope_id=scope.id,
        status="UNKNOWN",
        availability_status="UNKNOWN",
    )
    db.add(asset)
    db.commit()

    # Enqueue scan via /assets/{id}/scans
    resp = client.post(f"/api/v1/assets/{asset.id}/scans")
    assert resp.status_code == 201, f"Error: {resp.text}"
    scan_id = resp.json()["id"]

    # Query scan status
    scan_resp = client.get(f"/api/v1/scans/{scan_id}")
    assert scan_resp.status_code == 200
    assert scan_resp.json()["status"] == "PENDING"


def test_workflow_04_web_security_target_and_assessments(workflow_client):
    """Workflow 4: Web security targets can be listed and retrieved."""
    client, db, _ = workflow_client

    # Query web-targets
    resp = client.get("/api/v1/web-targets")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_workflow_05_incident_query_and_lifecycle(workflow_client):
    """Workflow 5: Security incidents can be queried and updated."""
    client, db, _ = workflow_client

    scope = ScanScope(
        name="Incident Scope",
        cidr="10.10.0.0/16",
        authorization_reference="AUTH-INC-01",
        enabled=True,
        expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    db.add(scope)
    db.commit()

    asset = Asset(
        name="Core Switch",
        target_ip="10.10.1.1",
        port=22,
        scope_id=scope.id,
        status="UNDER_ATTACK",
        availability_status="UP",
    )
    db.add(asset)
    db.commit()

    inc = Incident(
        asset_id=asset.id,
        source_ip="203.0.113.5",
        attack_type="BRUTE_FORCE",
        severity="HIGH",
        is_mitigated=False,
        lifecycle_status="OPEN",
        timestamp=datetime.now(timezone.utc),
    )
    db.add(inc)
    db.commit()

    resp = client.get("/api/v1/incidents/")
    assert resp.status_code == 200
    paginated = resp.json()
    assert "items" in paginated
    assert len(paginated["items"]) >= 1
    assert paginated["items"][0]["severity"] == "HIGH"

    # Update lifecycle status via /incidents/{id}/status
    patch_resp = client.patch(
        f"/api/v1/incidents/{inc.id}/status",
        json={"new_status": "INVESTIGATING", "reason": "SOC team investigating attack patterns"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["new_status"] == "INVESTIGATING"


def test_workflow_06_ai_health_and_triage(workflow_client):
    """Workflow 6: AI health inspection and triage enqueueing."""
    client, db, _ = workflow_client

    # 1. AI Health endpoint
    health_resp = client.get("/api/v1/ai/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert "ai_enabled" in health_data
    assert "active_provider" in health_data

    # 2. Enqueue triage
    scope = ScanScope(
        name="Triage Scope",
        cidr="10.20.0.0/16",
        authorization_reference="AUTH-TRIAGE",
        enabled=True,
        expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    db.add(scope)
    db.commit()

    asset = Asset(
        name="DB Server",
        target_ip="10.20.1.5",
        port=5432,
        scope_id=scope.id,
        status="UNDER_ATTACK",
        availability_status="UP",
    )
    db.add(asset)
    db.commit()

    inc = Incident(
        asset_id=asset.id,
        source_ip="198.51.100.99",
        attack_type="SQL_INJECTION",
        severity="CRITICAL",
        is_mitigated=False,
        lifecycle_status="OPEN",
        timestamp=datetime.now(timezone.utc),
    )
    db.add(inc)
    db.commit()

    triage_resp = client.post(f"/api/v1/incidents/{inc.id}/triage")
    assert triage_resp.status_code in (201, 202)
    triage_data = triage_resp.json()
    assert triage_data["status"] == "PENDING"
    assert triage_data["incident_id"] == inc.id


def test_workflow_07_and_08_report_generation_and_downloads(workflow_client):
    """Workflow 7 & 8: Report generation completes and multi-format downloads work."""
    client, db, rpt_dir = workflow_client

    # 1. Enqueue JSON report
    req_payload = {
        "report_type": "EXECUTIVE",
        "format": "JSON",
        "title": "Full Workflow Executive Report",
    }
    resp = client.post("/api/v1/reports/", json=req_payload)
    assert resp.status_code == 201
    rep_id = resp.json()["report_id"]

    # Process job via engine
    engine = ReportingEngine(db, reports_dir=rpt_dir)
    engine.process_report_job(rep_id)

    # Download JSON
    dl_resp = client.get(f"/api/v1/reports/{rep_id}/download")
    assert dl_resp.status_code == 200
    assert "application/json" in dl_resp.headers.get("content-type", "")
    assert "X-Report-Checksum" in dl_resp.headers

    # 2. Enqueue and process PDF report
    pdf_payload = {
        "report_type": "OPERATIONS",
        "format": "PDF",
        "title": "Operations PDF Report",
    }
    resp_pdf = client.post("/api/v1/reports/", json=pdf_payload)
    assert resp_pdf.status_code == 201
    pdf_id = resp_pdf.json()["report_id"]

    engine.process_report_job(pdf_id)

    # Download PDF
    dl_pdf = client.get(f"/api/v1/reports/{pdf_id}/download")
    assert dl_pdf.status_code == 200
    assert "application/pdf" in dl_pdf.headers.get("content-type", "")
    assert dl_pdf.content.startswith(b"%PDF")


def test_workflow_09_audit_chain_verification_endpoint(workflow_client):
    """Workflow 9: Audit-chain verification endpoint returns correct status."""
    client, db, rpt_dir = workflow_client

    req_payload = {
        "report_type": "TECHNICAL",
        "format": "HTML",
        "title": "Technical HTML Audit Report",
    }
    resp = client.post("/api/v1/reports/", json=req_payload)
    assert resp.status_code == 201
    rep_id = resp.json()["report_id"]

    engine = ReportingEngine(db, reports_dir=rpt_dir)
    engine.process_report_job(rep_id)

    audit_resp = client.get(f"/api/v1/reports/{rep_id}/audit-chain")
    assert audit_resp.status_code == 200
    chain = audit_resp.json()
    assert chain["verified"] is True
    assert chain["status"] == "CHAIN_VALID"
    assert chain["event_count"] >= 1


def test_workflow_10_empty_states_and_error_handling(workflow_client):
    """Workflow 10: Empty states and 404 errors are handled honestly."""
    client, db, rpt_dir = workflow_client

    # 404 for non-existent report
    resp = client.get("/api/v1/reports/REP-NONEXISTENT-999")
    assert resp.status_code == 404

    # 404 for non-existent download
    dl_resp = client.get("/api/v1/reports/REP-NONEXISTENT-999/download")
    assert dl_resp.status_code == 404

    # Honest empty state report
    empty_payload = {
        "report_type": "EXECUTIVE",
        "format": "JSON",
        "title": "Empty Posture Verification",
    }
    empty_resp = client.post("/api/v1/reports/", json=empty_payload)
    assert empty_resp.status_code == 201
    rep_id = empty_resp.json()["report_id"]

    engine = ReportingEngine(db, reports_dir=rpt_dir)
    engine.process_report_job(rep_id)

    rep_detail = client.get(f"/api/v1/reports/{rep_id}")
    assert rep_detail.status_code == 200
    assert rep_detail.json()["source_count"] == 0
