"""
test_assets.py — Tests for the /assets endpoints and /health endpoint.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Asset, Incident


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_asset(client: TestClient, **overrides) -> dict:
    """POST a valid asset and return the response JSON."""
    payload = {
        "name": "Test Server",
        "target_ip": "192.168.1.1",
        "port": 80,
        **overrides,
    }
    resp = client.post("/api/v1/assets/", json=payload)
    return resp


# ===========================================================================
# Health endpoint
# ===========================================================================

class TestHealthEndpoint:
    def test_health_endpoint(self, client: TestClient) -> None:
        """GET /api/v1/health returns 200 with status=healthy."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["database"] == "connected"
        assert "version" in body


# ===========================================================================
# Asset creation
# ===========================================================================

class TestCreateAsset:
    def test_create_asset_valid(self, client: TestClient) -> None:
        """POST /api/v1/assets/ with valid data returns 201 and the asset."""
        resp = _create_asset(client)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Test Server"
        assert body["target_ip"] == "192.168.1.1"
        assert body["port"] == 80
        assert body["status"] == "UNKNOWN"
        assert "id" in body

    def test_create_asset_invalid_ip(self, client: TestClient) -> None:
        """Invalid IP address must return 422."""
        resp = _create_asset(client, target_ip="not-an-ip!!!")
        assert resp.status_code == 422

    def test_create_asset_invalid_port_zero(self, client: TestClient) -> None:
        """Port 0 is out of range — must return 422."""
        resp = _create_asset(client, port=0)
        assert resp.status_code == 422

    def test_create_asset_invalid_port_high(self, client: TestClient) -> None:
        """Port 99999 exceeds 65535 — must return 422."""
        resp = _create_asset(client, port=99999)
        assert resp.status_code == 422

    def test_create_asset_empty_name(self, client: TestClient) -> None:
        """Empty (whitespace-only) name must return 422."""
        resp = _create_asset(client, name="   ")
        assert resp.status_code == 422

    def test_create_asset_with_hostname(self, client: TestClient) -> None:
        """RFC-1123 hostname should be accepted as target_ip."""
        resp = _create_asset(client, target_ip="example.com", name="Web Server")
        assert resp.status_code == 201

    def test_create_asset_ipv6(self, client: TestClient) -> None:
        """IPv6 address should be accepted."""
        resp = _create_asset(client, target_ip="::1", name="Loopback v6")
        assert resp.status_code == 201


# ===========================================================================
# Asset retrieval
# ===========================================================================

class TestGetAsset:
    def test_get_asset(self, client: TestClient) -> None:
        """GET /api/v1/assets/{id} returns the created asset."""
        create_resp = _create_asset(client, name="Retrieve Me")
        asset_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/assets/{asset_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == asset_id
        assert resp.json()["name"] == "Retrieve Me"

    def test_get_asset_not_found(self, client: TestClient) -> None:
        """GET for a non-existent asset id returns 404."""
        resp = client.get("/api/v1/assets/999999")
        assert resp.status_code == 404


# ===========================================================================
# Asset update
# ===========================================================================

class TestUpdateAsset:
    def test_update_asset(self, client: TestClient) -> None:
        """PATCH updates only the provided fields; others stay unchanged."""
        create_resp = _create_asset(client, name="Original Name", port=443)
        asset_id = create_resp.json()["id"]

        patch_resp = client.patch(
            f"/api/v1/assets/{asset_id}",
            json={"status": "SAFE", "response_time_ms": 12.5},
        )
        assert patch_resp.status_code == 200
        body = patch_resp.json()
        assert body["status"] == "SAFE"
        assert body["response_time_ms"] == pytest.approx(12.5)
        # Unchanged fields
        assert body["name"] == "Original Name"
        assert body["port"] == 443

    def test_update_asset_not_found(self, client: TestClient) -> None:
        """PATCH on missing asset returns 404."""
        resp = client.patch("/api/v1/assets/999999", json={"status": "DOWN"})
        assert resp.status_code == 404


# ===========================================================================
# Asset listing
# ===========================================================================

class TestListAssets:
    def test_list_assets(self, client: TestClient) -> None:
        """GET /api/v1/assets/ returns a list."""
        _create_asset(client, name="Asset Alpha")
        _create_asset(client, name="Asset Beta")

        resp = client.get("/api/v1/assets/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 2

    def test_list_assets_filter_status(self, client: TestClient) -> None:
        """Filtering by status only returns matching assets."""
        _create_asset(client, name="Safe Asset")
        client.patch(
            f"/api/v1/assets/{_create_asset(client, name='Attack Asset').json()['id']}",
            json={"status": "UNDER_ATTACK"},
        )

        resp = client.get("/api/v1/assets/?status=UNDER_ATTACK")
        assert resp.status_code == 200
        results = resp.json()
        assert all(a["status"] == "UNDER_ATTACK" for a in results)


# ===========================================================================
# Asset deletion
# ===========================================================================

class TestDeleteAsset:
    def test_delete_asset_no_incidents(self, client: TestClient) -> None:
        """DELETE an asset with no incidents returns 200."""
        asset_id = _create_asset(client, name="Deletable").json()["id"]

        resp = client.delete(f"/api/v1/assets/{asset_id}")
        assert resp.status_code == 200

        # Confirm it's gone
        assert client.get(f"/api/v1/assets/{asset_id}").status_code == 404

    def test_delete_asset_with_incidents(
        self, client: TestClient, db_session: Session
    ) -> None:
        """DELETE an asset that has incidents returns 409 Conflict."""
        # Create asset
        asset_id = _create_asset(client, name="Asset With Incidents").json()["id"]

        # Attach an incident directly via DB session for speed
        incident = Incident(
            asset_id=asset_id,
            source_ip="10.0.0.1",
            attack_type="PORT_SCAN",
            severity="LOW",
            is_mitigated=False,
        )
        db_session.add(incident)
        db_session.commit()

        resp = client.delete(f"/api/v1/assets/{asset_id}")
        assert resp.status_code == 409
