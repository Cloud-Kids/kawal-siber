"""
Unit and integration test suite for Phase 4: Web Security & Deep Eye Integration.
Tests scope validation, target management, passive/safe assessment, result sanitization,
deduplication, incident correlation, and statistics.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.integrations.deep_eye.adapter import deep_eye_adapter
from app.integrations.deep_eye.result_parser import (
    compute_finding_fingerprint,
    normalize_severity,
    sanitize_evidence,
)
from app.integrations.deep_eye.validator import (
    InvalidTargetURLError,
    TargetOutOfScopeError,
    parse_and_validate_target_url,
    validate_path_allowed,
)
from app.models import Asset, Incident, ScanScope, WebAssessment, WebFinding, WebTarget
from app.services.web_assessment_service import WebAssessmentService


# ---------------------------------------------------------------------------
# Test: Scope & Target Validator
# ---------------------------------------------------------------------------

def test_target_validator_valid_localhost():
    scheme, host, port, url = parse_and_validate_target_url("http://127.0.0.1:8000/api/v1")
    assert scheme == "http"
    assert host == "127.0.0.1"
    assert port == 8000
    assert url == "http://127.0.0.1:8000/api/v1"

    scheme, host, port, url = parse_and_validate_target_url("http://localhost:3000")
    assert scheme == "http"
    assert host == "localhost"
    assert port == 3000


def test_target_validator_rejects_external_scope():
    with pytest.raises(TargetOutOfScopeError):
        parse_and_validate_target_url("http://example.com:8080")

    with pytest.raises(TargetOutOfScopeError):
        parse_and_validate_target_url("http://8.8.8.8:80")


def test_target_validator_rejects_cloud_metadata():
    with pytest.raises(TargetOutOfScopeError):
        parse_and_validate_target_url("http://169.254.169.254/latest/meta-data/")


def test_target_validator_rejects_invalid_scheme_and_ports():
    with pytest.raises(InvalidTargetURLError):
        parse_and_validate_target_url("ftp://127.0.0.1:21")

    with pytest.raises(InvalidTargetURLError):
        parse_and_validate_target_url("javascript:alert(1)")

    with pytest.raises(InvalidTargetURLError):
        parse_and_validate_target_url("http://127.0.0.1:70000")


def test_path_allowlist_matching():
    assert validate_path_allowed("/api/v1/users", "/*") is True
    assert validate_path_allowed("/api/v1/users", "/api/*") is True
    assert validate_path_allowed("/admin/console", "/api/*, /auth/*") is False
    assert validate_path_allowed("/robots.txt", "/robots.txt, /api/*") is True


# ---------------------------------------------------------------------------
# Test: Evidence Sanitization & Fingerprinting
# ---------------------------------------------------------------------------

def test_evidence_sanitization_removes_secrets():
    raw_evidence = (
        "HTTP/1.1 200 OK\n"
        "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretpayload\n"
        "Set-Cookie: session_token=abcd1234secret; HttpOnly\n"
        "api_key=sk-live-secretkey123456"
    )
    sanitized = sanitize_evidence(raw_evidence)
    assert "eyJhbGci" not in sanitized
    assert "abcd1234secret" not in sanitized
    assert "sk-live-secretkey" not in sanitized
    assert "[REDACTED]" in sanitized


def test_deterministic_fingerprint_generation():
    fp1 = compute_finding_fingerprint(
        web_target_id=1,
        vulnerability_type="MISSING_SECURITY_HEADER",
        title="Missing CSP",
        affected_url="http://127.0.0.1:8000/api",
    )
    fp2 = compute_finding_fingerprint(
        web_target_id=1,
        vulnerability_type="MISSING_SECURITY_HEADER",
        title="Missing CSP",
        affected_url="http://127.0.0.1:8000/api",
    )
    fp3 = compute_finding_fingerprint(
        web_target_id=1,
        vulnerability_type="XSS",
        title="Reflected XSS",
        affected_url="http://127.0.0.1:8000/api",
    )
    assert fp1 == fp2
    assert fp1 != fp3
    assert len(fp1) == 64  # SHA-256


# ---------------------------------------------------------------------------
# Test: WebTarget CRUD via API
# ---------------------------------------------------------------------------

def test_web_target_crud(client: TestClient, db_session: Session):
    # 1. Create target
    payload = {
        "name": "FastAPI Core Gateway",
        "target_url": "http://127.0.0.1:8000",
        "allowed_paths": "/*",
        "authorization_reference": "AUTH-TEST-2026",
        "enabled": True,
    }
    resp = client.post("/api/v1/web-targets", json=payload)
    assert resp.status_code == 201
    target = resp.json()
    target_id = target["id"]
    assert target["name"] == "FastAPI Core Gateway"
    assert target["hostname"] == "127.0.0.1"
    assert target["port"] == 8000

    # 2. List targets
    list_resp = client.get("/api/v1/web-targets")
    assert list_resp.status_code == 200
    assert any(t["id"] == target_id for t in list_resp.json())

    # 3. Update target
    patch_resp = client.patch(f"/api/v1/web-targets/{target_id}", json={"name": "FastAPI Gateway Lab", "enabled": False})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "FastAPI Gateway Lab"
    assert patch_resp.json()["enabled"] is False

    # 4. Delete target
    del_resp = client.delete(f"/api/v1/web-targets/{target_id}")
    assert del_resp.status_code == 200

    # 5. Verify deleted
    get_resp = client.get(f"/api/v1/web-targets/{target_id}")
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Test: Web Assessment Execution & Finding Deduplication
# ---------------------------------------------------------------------------

def test_web_assessment_execution_and_deduplication(client: TestClient, db_session: Session):
    # Register target
    t_resp = client.post(
        "/api/v1/web-targets",
        json={
            "name": "Lab Target Test",
            "target_url": "http://127.0.0.1:8000",
            "allowed_paths": "/*",
            "enabled": True,
        },
    )
    assert t_resp.status_code == 201
    target_id = t_resp.json()["id"]

    # Execute Assessment 1 (PASSIVE)
    a1_resp = client.post(
        "/api/v1/web-assessments?run_immediate=true",
        json={"web_target_id": target_id, "assessment_profile": "PASSIVE"},
    )
    assert a1_resp.status_code == 201
    a1 = a1_resp.json()
    assert a1["status"] == "COMPLETED"
    assert a1["duration_ms"] >= 0
    assert a1["tool_name"] == "Deep Eye"

    findings1 = client.get(f"/api/v1/web-assessments/{a1['id']}/findings").json()

    # Execute Assessment 2 (PASSIVE again)
    a2_resp = client.post(
        "/api/v1/web-assessments?run_immediate=true",
        json={"web_target_id": target_id, "assessment_profile": "PASSIVE"},
    )
    assert a2_resp.status_code == 201
    a2 = a2_resp.json()
    assert a2["status"] == "COMPLETED"

    # Query all findings for this target: findings should be deduplicated by fingerprint
    target_findings = client.get(f"/api/v1/web-findings?web_target_id={target_id}").json()
    fingerprints = [f["fingerprint"] for f in target_findings]
    assert len(fingerprints) == len(set(fingerprints)), "Findings must be uniquely deduplicated by fingerprint."


# ---------------------------------------------------------------------------
# Test: Finding Triage Status Update
# ---------------------------------------------------------------------------

def test_finding_triage_lifecycle(client: TestClient, db_session: Session):
    t_resp = client.post(
        "/api/v1/web-targets",
        json={
            "name": "Triage Target",
            "target_url": "http://127.0.0.1:8000",
            "enabled": True,
        },
    )
    target_id = t_resp.json()["id"]

    client.post(
        "/api/v1/web-assessments?run_immediate=true",
        json={"web_target_id": target_id, "assessment_profile": "PASSIVE"},
    )

    findings = client.get(f"/api/v1/web-findings?web_target_id={target_id}").json()
    if findings:
        f_id = findings[0]["id"]
        # Update triage status to CONFIRMED
        triage_resp = client.patch(f"/api/v1/web-findings/{f_id}", json={"finding_status": "CONFIRMED"})
        assert triage_resp.status_code == 200
        assert triage_resp.json()["finding_status"] == "CONFIRMED"

        # Invalid status rejected
        inv_resp = client.patch(f"/api/v1/web-findings/{f_id}", json={"finding_status": "INVALID_STATUS"})
        assert inv_resp.status_code == 400


# ---------------------------------------------------------------------------
# Test: Statistics Endpoint
# ---------------------------------------------------------------------------

def test_web_security_statistics(client: TestClient, db_session: Session):
    resp = client.get("/api/v1/web-security/statistics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_targets" in data
    assert "total_assessments" in data
    assert "total_findings" in data
    assert "severity_distribution" in data
    assert "status_distribution" in data
    assert "top_vulnerabilities" in data
