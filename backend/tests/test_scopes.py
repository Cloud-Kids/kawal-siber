"""
test_scopes.py — Tests for Scan Scope Management API endpoints.
Validates CIDR constraints, expiration policies, and lifecycle management.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


class TestScanScopes:
    """Test suite for /api/v1/scan-scopes endpoints."""

    def test_create_scan_scope_success(self, client: TestClient) -> None:
        future_time = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        payload = {
            "name": "Kodam Jaya Subnet Lab",
            "cidr": "192.168.1.0/24",
            "description": "Authorized territorial perimeter lab network",
            "authorization_reference": "AUTH-KODAM-2026-001",
            "enabled": True,
            "expires_at": future_time,
        }
        response = client.post("/api/v1/scan-scopes", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] > 0
        assert data["name"] == "Kodam Jaya Subnet Lab"
        assert data["cidr"] == "192.168.1.0/24"
        assert data["authorization_reference"] == "AUTH-KODAM-2026-001"
        assert data["enabled"] is True

    def test_create_scan_scope_invalid_cidr_rejected(self, client: TestClient) -> None:
        future_time = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        payload = {
            "name": "Invalid CIDR Scope",
            "cidr": "999.999.999.999/24",
            "authorization_reference": "AUTH-TEST-002",
            "expires_at": future_time,
        }
        response = client.post("/api/v1/scan-scopes", json=payload)
        assert response.status_code == 422

    def test_create_scan_scope_past_expiry_rejected(self, client: TestClient) -> None:
        past_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        payload = {
            "name": "Expired Scope",
            "cidr": "10.0.0.0/8",
            "authorization_reference": "AUTH-TEST-003",
            "expires_at": past_time,
        }
        response = client.post("/api/v1/scan-scopes", json=payload)
        assert response.status_code == 422
        assert "expires_at must be in the future" in response.text

    def test_create_scan_scope_empty_auth_ref_rejected(self, client: TestClient) -> None:
        future_time = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        payload = {
            "name": "No Auth Ref Scope",
            "cidr": "172.16.0.0/16",
            "authorization_reference": "   ",
            "expires_at": future_time,
        }
        response = client.post("/api/v1/scan-scopes", json=payload)
        assert response.status_code == 422

    def test_list_and_filter_scopes(self, client: TestClient) -> None:
        future_time = (datetime.now(timezone.utc) + timedelta(days=15)).isoformat()
        # Create active scope
        client.post(
            "/api/v1/scan-scopes",
            json={
                "name": "Active DMZ",
                "cidr": "10.10.1.0/24",
                "authorization_reference": "AUTH-ACT-01",
                "enabled": True,
                "expires_at": future_time,
            },
        )
        # Create disabled scope
        client.post(
            "/api/v1/scan-scopes",
            json={
                "name": "Disabled Internal",
                "cidr": "10.10.2.0/24",
                "authorization_reference": "AUTH-DIS-01",
                "enabled": False,
                "expires_at": future_time,
            },
        )

        # List all
        resp_all = client.get("/api/v1/scan-scopes")
        assert resp_all.status_code == 200
        assert len(resp_all.json()) >= 2

        # Filter enabled=true
        resp_enabled = client.get("/api/v1/scan-scopes?enabled=true")
        assert resp_enabled.status_code == 200
        for s in resp_enabled.json():
            assert s["enabled"] is True

        # Filter enabled=false
        resp_disabled = client.get("/api/v1/scan-scopes?enabled=false")
        assert resp_disabled.status_code == 200
        for s in resp_disabled.json():
            assert s["enabled"] is False

    def test_update_and_disable_scope(self, client: TestClient) -> None:
        future_time = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
        create_resp = client.post(
            "/api/v1/scan-scopes",
            json={
                "name": "To Be Disabled",
                "cidr": "192.168.100.0/24",
                "authorization_reference": "AUTH-MOD-01",
                "enabled": True,
                "expires_at": future_time,
            },
        )
        scope_id = create_resp.json()["id"]

        # Disable scope
        patch_resp = client.patch(
            f"/api/v1/scan-scopes/{scope_id}",
            json={"enabled": False, "description": "Disabled due to maintenance"},
        )
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["enabled"] is False
        assert data["description"] == "Disabled due to maintenance"

    def test_get_scope_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/scan-scopes/999999")
        assert response.status_code == 404

