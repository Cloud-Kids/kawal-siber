"""
test_phase6_reporting.py — Comprehensive tests for Phase 6 Automated Reporting Engine,
sanitization (CSV formula injection defense), exporters (PDF/HTML/JSON/CSV),
and API endpoints.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Asset, GeneratedReport, Incident, ScanJob, ScanResult
from app.reporting.engine import ReportingEngine
from app.reporting.exporters.csv_export import export_to_csv
from app.reporting.exporters.html import export_to_html
from app.reporting.exporters.json_export import export_to_json
from app.reporting.exporters.pdf import export_to_pdf
from app.reporting.sanitization import (
    redact_sensitive_data,
    sanitize_csv_cell,
    sanitize_for_html,
)


# ===========================================================================
# 1. Sanitization & CSV Formula Injection Prevention Tests
# ===========================================================================


def test_csv_formula_injection_defense():
    """Verify cells starting with =, +, -, @, \\t, \\r are safely neutralized by prepending single quote."""
    dangerous_payloads = [
        "=cmd|'/C calc'!A0",
        "+1+1",
        "-5+5",
        "@SUM(A1:A10)",
        "\tmalicious_tab",
        "\rmalicious_cr",
    ]
    for payload in dangerous_payloads:
        sanitized = sanitize_csv_cell(payload)
        assert sanitized.startswith("'"), f"Dangerous payload {payload!r} was not neutralized with leading quote"
        assert sanitized[1:] == payload

    # Safe cells should NOT be modified
    assert sanitize_csv_cell("Normal Text") == "Normal Text"
    assert sanitize_csv_cell("192.168.1.1") == "192.168.1.1"
    assert sanitize_csv_cell(12345) == "12345"
    assert sanitize_csv_cell(None) == ""


def test_credential_and_token_redaction():
    """Verify secrets, tokens, and basic/bearer auth headers are redacted in reports."""
    text_with_secrets = (
        "Server failed with Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret and "
        "api_key=sk-1234567890abcdef and password=SuperSecretPassword123"
    )
    redacted = redact_sensitive_data(text_with_secrets)
    assert "Bearer [REDACTED]" in redacted
    assert "SuperSecretPassword123" not in redacted


def test_html_sanitization():
    """Verify HTML entities are properly escaped."""
    raw = '<script>alert("XSS")</script>&<foo>'
    safe = sanitize_for_html(raw)
    assert "<script>" not in safe
    assert "&lt;script&gt;" in safe
    assert "&amp;" in safe


# ===========================================================================
# 2. Exporter Tests (PDF, HTML, JSON, CSV)
# ===========================================================================


@pytest.fixture
def sample_snapshot_data() -> Dict[str, Any]:
    return {
        "metadata": {
            "report_id": "REP-20261108-TEST01",
            "report_type": "EXECUTIVE",
            "title": "Executive Security Audit Report",
            "generated_by": "Lead Security Auditor",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "target_asset": "127.0.0.1",
        },
        "executive_summary": "System security audit completed with zero active compromises.",
        "kpi_metrics": [
            {"label": "Total Assets", "value": "5"},
            {"label": "Critical Incidents", "value": "0"},
            {"label": "Mitigation Rate", "value": "100%"},
            {"label": "Risk Posture", "value": "STABLE"},
        ],
        "findings": [
            {
                "id": "1",
                "severity": "LOW",
                "category": "PORT_SCAN",
                "description": "Authorized probe on port 80",
                "source": "Nmap",
                "status": "RESOLVED",
            }
        ],
        "recommendations": [
            "Maintain current firewall filtering rules.",
            "Enforce continuous automated reporting schedule.",
        ],
    }


def test_json_exporter(tmp_path: Path, sample_snapshot_data):
    """Test JSON exporter schema and content."""
    out_file = tmp_path / "test_report.json"
    exported_path = export_to_json(sample_snapshot_data, out_file)

    assert exported_path.exists()
    assert exported_path.stat().st_size > 0

    # Verify content
    with open(exported_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["schema_version"] == "1.0"
    assert "platform" in data


def test_csv_exporter_with_formula_injection(tmp_path: Path, sample_snapshot_data):
    """Test CSV exporter sanitizes cells and produces valid CSV."""
    sample_snapshot_data["findings"].append({
        "id": "2",
        "severity": "HIGH",
        "category": "=cmd|'/C calc'!A0",
        "description": "@SUM(1+1)",
        "source": "+NmapScanner",
        "status": "-ACTIVE",
    })

    out_file = tmp_path / "test_report.csv"
    exported_path = export_to_csv(sample_snapshot_data, out_file)

    assert exported_path.exists()
    assert exported_path.stat().st_size > 0

    with open(exported_path, "r", encoding="utf-8") as f:
        content = f.read()

    # All injected formulas should be neutralized with prepended quote
    assert "'=cmd|'/C calc'!A0" in content
    assert "'@SUM(1+1)" in content
    assert "'+NmapScanner" in content
    assert "'-ACTIVE" in content


def test_html_exporter(tmp_path: Path, sample_snapshot_data):
    """Test HTML exporter produces standalone valid HTML."""
    out_file = tmp_path / "test_report.html"
    exported_path = export_to_html(sample_snapshot_data, out_file)

    assert exported_path.exists()
    assert exported_path.stat().st_size > 0
    with open(exported_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert "<!DOCTYPE html>" in html
    assert "KAWAL SIBER" in html


def test_pdf_exporter(tmp_path: Path, sample_snapshot_data):
    """Test ReportLab PDF generation creates valid binary PDF."""
    out_file = tmp_path / "test_report.pdf"
    exported_path = export_to_pdf(sample_snapshot_data, out_file)

    assert exported_path.exists()
    assert exported_path.stat().st_size > 1000  # ReportLab PDF with tables is typically > 2 KB

    # Verify PDF magic bytes
    with open(exported_path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


# ===========================================================================
# 3. Reporting Engine & SQLite Database Integrity Tests
# ===========================================================================


def test_reporting_engine_process_job(db_session: Session, tmp_path: Path, monkeypatch):
    """Verify ReportingEngine creates snapshot, executes exporter, updates DB and checksum."""
    from app.reporting import engine as engine_mod

    # Redirect storage directory to temporary path
    monkeypatch.setattr(engine_mod, "REPORTS_DIR", tmp_path)

    # Seed an asset and an incident
    asset = Asset(name="Lab Target", target_ip="127.0.0.1", port=80, status="SAFE", availability_status="UP")
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    incident = Incident(
        asset_id=asset.id,
        source_ip="127.0.0.1",
        attack_type="PORT_SCAN",
        severity="LOW",
        lifecycle_status="RESOLVED",
        is_mitigated=True,
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    rep = GeneratedReport(
        report_id="REP-TEST-ENGINE-001",
        report_type="EXECUTIVE",
        title="Test Executive Run",
        format="HTML",
        generation_status="PENDING",
        generated_by="Unit Tester",
    )
    db_session.add(rep)
    db_session.commit()
    db_session.refresh(rep)

    engine = ReportingEngine(db_session)
    completed_report = engine.process_report_job(rep.report_id)

    assert completed_report.generation_status == "COMPLETED"
    assert completed_report.file_path is not None
    assert Path(completed_report.file_path).exists()
    assert completed_report.file_size is not None and completed_report.file_size > 0
    assert completed_report.sha256_checksum is not None and len(completed_report.sha256_checksum) == 64

    # Verify checksum matches actual file
    with open(completed_report.file_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
    assert completed_report.sha256_checksum == actual_hash


# ===========================================================================
# 4. Reports API Route & Traversal Protection Tests
# ===========================================================================


def test_reports_api_crud_and_traversal_guard(client: TestClient, db_session: Session, tmp_path: Path, monkeypatch):
    """Test full reports REST endpoints and path traversal blocking."""
    from app.api.routes import reports as reports_mod
    monkeypatch.setattr(reports_mod, "REPORTS_DIR", tmp_path)

    # 1. Create a report request
    create_resp = client.post(
        "/api/v1/reports",
        json={
            "report_type": "EXECUTIVE",
            "format": "JSON",
            "title": "API Test Report",
            "generated_by": "Auditor Test",
            "include_ai_narrative": True,
        },
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    report_id = data["report_id"]
    db_id = data["id"]
    assert data["generation_status"] == "PENDING"

    # 2. Query statistics
    stats_resp = client.get("/api/v1/reports/statistics")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_reports"] >= 1
    assert "EXECUTIVE" in stats["by_type"]

    # 3. Query list
    list_resp = client.get("/api/v1/reports?report_type=EXECUTIVE")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert any(r["report_id"] == report_id for r in items)

    # 4. Query detail
    detail_resp = client.get(f"/api/v1/reports/{report_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["title"] == "API Test Report"

    # Simulate completion by writing a mock file and setting COMPLETED
    test_file = tmp_path / f"{report_id}.json"
    test_file.write_text('{"status": "ok"}', encoding="utf-8")
    report_obj = db_session.get(GeneratedReport, db_id)
    report_obj.generation_status = "COMPLETED"
    report_obj.file_path = str(test_file)
    report_obj.file_size = len('{"status": "ok"}')
    report_obj.sha256_checksum = hashlib.sha256(b'{"status": "ok"}').hexdigest()
    db_session.commit()

    # 5. Preview report
    prev_resp = client.get(f"/api/v1/reports/{report_id}/preview")
    assert prev_resp.status_code == 200
    assert prev_resp.json()["status"] == "ok"

    # 6. Download report
    dl_resp = client.get(f"/api/v1/reports/{report_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.content == b'{"status": "ok"}'

    # 7. Path traversal guard test:
    # Attempting to access an illegal path or pointing file_path outside REPORTS_DIR
    secret_file = tmp_path.parent / "secret.txt"
    secret_file.write_text("TOP_SECRET", encoding="utf-8")
    report_obj.file_path = str(secret_file)
    db_session.commit()

    traversal_dl_resp = client.get(f"/api/v1/reports/{report_id}/download")
    assert traversal_dl_resp.status_code == 403
    assert "forbidden" in traversal_dl_resp.json()["detail"].lower()

    traversal_prev_resp = client.get(f"/api/v1/reports/{report_id}/preview")
    assert traversal_prev_resp.status_code == 403
    assert "forbidden" in traversal_prev_resp.json()["detail"].lower()
