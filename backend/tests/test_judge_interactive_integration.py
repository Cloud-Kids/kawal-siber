"""
Integration tests for judge interactive mode core modules.
Tests asset management, web targets, assessments, findings, incidents, and reports.
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Note: DATABASE_URL is set by conftest.py to use a temporary file-based SQLite database
# This ensures proper isolation and table creation via Alembic migrations

from app import judge_mode
from app.main import app
from app.database import get_db
from app.models import Asset, WebTarget, WebAssessment, WebFinding, Incident, GeneratedReport


# Use the client fixture from conftest.py which provides proper database isolation
# The conftest.py client fixture uses db_session which has rollback isolation
# and the create_test_tables session fixture ensures all tables exist


@pytest.fixture(autouse=True)
def _interactive_judge_mode(monkeypatch):
    """Enable interactive judge mode per-test without leaking env/module state."""
    monkeypatch.setenv("KAWAL_JUDGE_MODE", "interactive")
    monkeypatch.setattr(judge_mode, "JUDGE_MODE", True)
    monkeypatch.setattr(judge_mode, "JUDGE_INTERACTIVE", True)


class TestAssetManagement:
    """Test asset management in interactive mode."""
    
    def test_create_asset(self, client):
        """Test creating a new asset."""
        response = client.post("/api/v1/assets", json={
            "name": "Test Asset",
            "target_ip": "192.168.1.100",
            "port": 80,
            "status": "SAFE",
            "availability_status": "UP"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Asset"
        assert data["target_ip"] == "192.168.1.100"
    
    def test_list_assets(self, client):
        """Test listing assets."""
        # Create an asset first
        client.post("/api/v1/assets", json={
            "name": "Test Asset",
            "target_ip": "192.168.1.100",
            "port": 80
        })
        
        response = client.get("/api/v1/assets")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
    
    def test_update_asset(self, client):
        """Test updating an asset."""
        # Create an asset
        create_response = client.post("/api/v1/assets", json={
            "name": "Test Asset",
            "target_ip": "192.168.1.100",
            "port": 80
        })
        asset_id = create_response.json()["id"]
        
        # Update it
        response = client.patch(f"/api/v1/assets/{asset_id}", json={
            "name": "Updated Asset"
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Asset"
    
    def test_delete_asset(self, client):
        """Test deleting an asset."""
        # Create an asset
        create_response = client.post("/api/v1/assets", json={
            "name": "Test Asset",
            "target_ip": "192.168.1.100",
            "port": 80
        })
        asset_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(f"/api/v1/assets/{asset_id}")
        assert response.status_code == 200


class TestWebTargetManagement:
    """Test web target management in interactive mode."""
    
    def test_create_synthetic_target(self, client):
        """Test creating the synthetic target."""
        response = client.post("/api/v1/web-targets", json={
            "name": "Synthetic Target",
            "target_url": "http://synthetic-target:8080",
            "allowed_paths": "/*",
            "authorization_reference": "JUDGE-DEMO-2026"
        })
        assert response.status_code == 201
        data = response.json()
        # URL is normalized to include trailing slash
        assert data["target_url"] == "http://synthetic-target:8080/"
    
    def test_create_external_target_denied(self, client):
        """Test that external targets are denied."""
        response = client.post("/api/v1/web-targets", json={
            "name": "External Target",
            "target_url": "http://example.com",
            "allowed_paths": "/*"
        })
        assert response.status_code == 400
        assert "synthetic target" in response.json()["detail"].lower()
    
    def test_create_localhost_target_denied(self, client):
        """Test that localhost targets are denied."""
        response = client.post("/api/v1/web-targets", json={
            "name": "Localhost Target",
            "target_url": "http://localhost:8000",
            "allowed_paths": "/*"
        })
        assert response.status_code == 400
    
    def test_list_web_targets(self, client):
        """Test listing web targets."""
        # Create a target
        client.post("/api/v1/web-targets", json={
            "name": "Synthetic Target",
            "target_url": "http://synthetic-target:8080"
        })
        
        response = client.get("/api/v1/web-targets")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestWebAssessments:
    """Test web assessments in interactive mode."""
    
    def test_create_assessment(self, client):
        """Test creating a web assessment."""
        # Create a web target first
        target_response = client.post("/api/v1/web-targets", json={
            "name": "Synthetic Target",
            "target_url": "http://synthetic-target:8080"
        })
        target_id = target_response.json()["id"]
        
        # Create assessment
        response = client.post("/api/v1/web-assessments", json={
            "web_target_id": target_id,
            "assessment_profile": "PASSIVE"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["web_target_id"] == target_id
        assert data["assessment_profile"] == "PASSIVE"
    
    def test_list_assessments(self, client):
        """Test listing web assessments."""
        response = client.get("/api/v1/web-assessments")
        assert response.status_code == 200


class TestFindingsManagement:
    """Test findings management in interactive mode."""
    
    def test_list_findings(self, client):
        """Test listing web findings."""
        response = client.get("/api/v1/web-findings")
        assert response.status_code == 200


class TestIncidentManagement:
    """Test incident management in interactive mode."""
    
    def test_create_incident(self, client):
        """Test creating an incident."""
        # Create an asset first
        asset_response = client.post("/api/v1/assets", json={
            "name": "Test Asset",
            "target_ip": "192.168.1.100",
            "port": 80
        })
        asset_id = asset_response.json()["id"]
        
        # Create incident
        response = client.post("/api/v1/incidents", json={
            "asset_id": asset_id,
            "timestamp": "2026-11-15T07:30:00Z",
            "source_ip": "192.168.1.200",
            "attack_type": "SQL_INJECTION",
            "payload": "SELECT * FROM users",
            "severity": "HIGH",
            "ai_analysis": "Potential SQL injection",
            "is_mitigated": False
        })
        assert response.status_code == 201
    
    def test_list_incidents(self, client):
        """Test listing incidents."""
        response = client.get("/api/v1/incidents")
        assert response.status_code == 200


class TestReportGeneration:
    """Test report generation in interactive mode."""
    
    def test_create_report(self, client):
        """Test creating a report."""
        response = client.post("/api/v1/reports", json={
            "report_type": "EXECUTIVE",
            "format": "PDF",
            "title": "Test Report",
            "generated_by": "Test User"
        })
        assert response.status_code == 201
    
    def test_list_reports(self, client):
        """Test listing reports."""
        response = client.get("/api/v1/reports")
        assert response.status_code == 200


class TestSecurityControls:
    """Test security controls in interactive mode."""
    
    def test_admin_access_denied(self, client):
        """Test that admin endpoints are denied."""
        response = client.get("/api/v1/admin/users")
        assert response.status_code == 403
    
    def test_docs_disabled(self, client):
        """Test that docs endpoints are disabled."""
        response = client.get("/docs")
        assert response.status_code == 403
    
    def test_arbitrary_write_denied(self, client):
        """Test that arbitrary write operations are denied."""
        response = client.post("/api/v1/unknown", json={})
        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
