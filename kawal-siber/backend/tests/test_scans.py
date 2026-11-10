"""
test_scans.py — Tests for Scan Job Orchestration API endpoints.
Verifies scope enforcement, queuing semantics, duplicate prevention, and history.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


class TestScanJobs:
    """Test suite for /api/v1/scans and asset scanning endpoints."""

    def test_enqueue_scan_job_within_scope_success(self, client: TestClient) -> None:
        # 1. Create active authorized scope
        future_time = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        scope_resp = client.post(
            "/api/v1/scan-scopes",
            json={
                "name": "Local Test Scope",
                "cidr": "127.0.0.0/8",
                "authorization_reference": "AUTH-LOCAL-001",
                "enabled": True,
                "expires_at": future_time,
            },
        )
        scope_id = scope_resp.json()["id"]

        # 2. Create asset within that scope
        asset_resp = client.post(
            "/api/v1/assets",
            json={
                "name": "Local Loopback Gateway",
                "target_ip": "127.0.0.1",
                "port": 8080,
                "scope_id": scope_id,
            },
        )
        asset_id = asset_resp.json()["id"]

        # 3. Enqueue scan
        scan_resp = client.post(f"/api/v1/assets/{asset_id}/scans")
        assert scan_resp.status_code == 201
        job_data = scan_resp.json()
        assert job_data["id"] > 0
        assert job_data["asset_id"] == asset_id
        assert job_data["status"] == "PENDING"

    def test_enqueue_scan_job_out_of_scope_rejected(self, client: TestClient) -> None:
        # Create scope for 10.0.0.0/24
        future_time = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        scope_resp = client.post(
            "/api/v1/scan-scopes",
            json={
                "name": "Strict Subnet",
                "cidr": "10.0.0.0/24",
                "authorization_reference": "AUTH-STRICT-001",
                "enabled": True,
                "expires_at": future_time,
            },
        )
        scope_id = scope_resp.json()["id"]

        # Create asset with IP outside that scope (e.g. 192.168.1.50)
        asset_resp = client.post(
            "/api/v1/assets",
            json={
                "name": "External Asset",
                "target_ip": "192.168.1.50",
                "port": 443,
                "scope_id": scope_id,
            },
        )
        asset_id = asset_resp.json()["id"]

        # Enqueue scan must be rejected with 403 Forbidden
        scan_resp = client.post(f"/api/v1/assets/{asset_id}/scans")
        assert scan_resp.status_code == 403
        assert "outside authorized scope" in scan_resp.text

    def test_enqueue_scan_job_disabled_scope_rejected(self, client: TestClient) -> None:
        future_time = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        scope_resp = client.post(
            "/api/v1/scan-scopes",
            json={
                "name": "Disabled Scope Test",
                "cidr": "172.20.0.0/16",
                "authorization_reference": "AUTH-DIS-002",
                "enabled": False,
                "expires_at": future_time,
            },
        )
        scope_id = scope_resp.json()["id"]

        asset_resp = client.post(
            "/api/v1/assets",
            json={
                "name": "Internal Asset In Disabled Scope",
                "target_ip": "172.20.1.10",
                "port": 22,
                "scope_id": scope_id,
            },
        )
        asset_id = asset_resp.json()["id"]

        scan_resp = client.post(f"/api/v1/assets/{asset_id}/scans")
        assert scan_resp.status_code == 403
        assert "disabled" in scan_resp.text.lower()

    def test_enqueue_duplicate_scan_job_rejected(self, client: TestClient) -> None:
        future_time = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        scope_resp = client.post(
            "/api/v1/scan-scopes",
            json={
                "name": "Dedup Test Scope",
                "cidr": "10.50.0.0/16",
                "authorization_reference": "AUTH-DEDUP-001",
                "enabled": True,
                "expires_at": future_time,
            },
        )
        scope_id = scope_resp.json()["id"]

        asset_resp = client.post(
            "/api/v1/assets",
            json={
                "name": "Dedup Server",
                "target_ip": "10.50.1.1",
                "port": 80,
                "scope_id": scope_id,
            },
        )
        asset_id = asset_resp.json()["id"]

        # First enqueue -> 201
        resp1 = client.post(f"/api/v1/assets/{asset_id}/scans")
        assert resp1.status_code == 201

        # Second enqueue while first is still PENDING -> 409 Conflict
        resp2 = client.post(f"/api/v1/assets/{asset_id}/scans")
        assert resp2.status_code == 409
        assert "already active" in resp2.text

    def test_list_scans_and_get_scan_detail(self, client: TestClient) -> None:
        future_time = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        scope_resp = client.post(
            "/api/v1/scan-scopes",
            json={
                "name": "History Test Scope",
                "cidr": "10.60.0.0/16",
                "authorization_reference": "AUTH-HIST-001",
                "enabled": True,
                "expires_at": future_time,
            },
        )
        scope_id = scope_resp.json()["id"]

        asset_resp = client.post(
            "/api/v1/assets",
            json={
                "name": "History Asset",
                "target_ip": "10.60.1.5",
                "port": 53,
                "scope_id": scope_id,
            },
        )
        asset_id = asset_resp.json()["id"]

        scan_resp = client.post(f"/api/v1/assets/{asset_id}/scans")
        job_id = scan_resp.json()["id"]

        # List all scans
        list_resp = client.get("/api/v1/scans")
        assert list_resp.status_code == 200
        jobs = list_resp.json()
        assert any(j["id"] == job_id for j in jobs)

        # Get specific scan
        detail_resp = client.get(f"/api/v1/scans/{job_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["id"] == job_id

        # Get asset scan history
        asset_history_resp = client.get(f"/api/v1/assets/{asset_id}/scans")
        assert asset_history_resp.status_code == 200
        assert len(asset_history_resp.json()) >= 1

