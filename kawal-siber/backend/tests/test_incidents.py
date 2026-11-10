"""
test_incidents.py — Tests for the /incidents endpoints.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Asset, Incident


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_asset(client: TestClient, name: str = "Test Asset") -> int:
    """Create an asset and return its id."""
    resp = client.post(
        "/api/v1/assets/",
        json={"name": name, "target_ip": "10.0.0.1", "port": 22},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _incident_payload(asset_id: int, **overrides) -> dict:
    """Return a valid incident creation payload."""
    base = {
        "asset_id": asset_id,
        "source_ip": "203.0.113.5",
        "attack_type": "PORT_SCAN",
        "severity": "MEDIUM",
    }
    base.update(overrides)
    return base


# ===========================================================================
# Incident creation
# ===========================================================================

class TestCreateIncident:
    def test_create_incident_valid(self, client: TestClient) -> None:
        """POST /api/v1/incidents/ with valid data returns 201."""
        asset_id = _create_asset(client)
        resp = client.post("/api/v1/incidents/", json=_incident_payload(asset_id))
        assert resp.status_code == 201
        body = resp.json()
        assert body["asset_id"] == asset_id
        assert body["severity"] == "MEDIUM"
        assert body["attack_type"] == "PORT_SCAN"
        assert body["is_mitigated"] is False

    def test_create_incident_invalid_asset(self, client: TestClient) -> None:
        """Unknown asset_id returns 404."""
        resp = client.post("/api/v1/incidents/", json=_incident_payload(999999))
        assert resp.status_code == 404

    def test_create_incident_invalid_severity(self, client: TestClient) -> None:
        """Bad severity enum value returns 422."""
        asset_id = _create_asset(client)
        resp = client.post(
            "/api/v1/incidents/",
            json=_incident_payload(asset_id, severity="ULTRA"),
        )
        assert resp.status_code == 422

    def test_create_incident_invalid_attack_type(self, client: TestClient) -> None:
        """Bad attack_type enum value returns 422."""
        asset_id = _create_asset(client)
        resp = client.post(
            "/api/v1/incidents/",
            json=_incident_payload(asset_id, attack_type="DDOS"),
        )
        assert resp.status_code == 422

    def test_create_incident_invalid_source_ip(self, client: TestClient) -> None:
        """Non-IP source_ip returns 422."""
        asset_id = _create_asset(client)
        resp = client.post(
            "/api/v1/incidents/",
            json=_incident_payload(asset_id, source_ip="not-an-ip"),
        )
        assert resp.status_code == 422

    def test_payload_too_large(self, client: TestClient) -> None:
        """payload exceeding 65536 chars returns 422."""
        asset_id = _create_asset(client)
        resp = client.post(
            "/api/v1/incidents/",
            json=_incident_payload(asset_id, payload="A" * 65537),
        )
        assert resp.status_code == 422


# ===========================================================================
# Incident retrieval
# ===========================================================================

class TestGetIncident:
    def test_get_incident(self, client: TestClient) -> None:
        """GET /api/v1/incidents/{id} returns correct data."""
        asset_id = _create_asset(client)
        create_resp = client.post(
            "/api/v1/incidents/",
            json=_incident_payload(asset_id, severity="HIGH"),
        )
        incident_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/incidents/{incident_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == incident_id
        assert body["severity"] == "HIGH"

    def test_get_incident_not_found(self, client: TestClient) -> None:
        """GET for non-existent incident id returns 404."""
        resp = client.get("/api/v1/incidents/999999")
        assert resp.status_code == 404


# ===========================================================================
# Incident listing / pagination
# ===========================================================================

class TestListIncidents:
    def test_list_incidents_pagination(self, client: TestClient) -> None:
        """page and page_size query params control the result slice."""
        asset_id = _create_asset(client, name="Pagination Asset")

        # Create 5 incidents
        for i in range(5):
            client.post(
                "/api/v1/incidents/",
                json=_incident_payload(asset_id, source_ip=f"10.0.0.{i + 1}"),
            )

        resp = client.get(
            "/api/v1/incidents/",
            params={"asset_id": asset_id, "page": 1, "page_size": 2},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 2
        assert len(body["items"]) == 2
        assert body["total"] >= 5

    def test_list_incidents_filter_severity(self, client: TestClient) -> None:
        """Filtering by severity returns only matching incidents."""
        asset_id = _create_asset(client, name="Filter Asset")

        client.post(
            "/api/v1/incidents/",
            json=_incident_payload(asset_id, severity="CRITICAL"),
        )
        client.post(
            "/api/v1/incidents/",
            json=_incident_payload(asset_id, severity="LOW"),
        )

        resp = client.get("/api/v1/incidents/", params={"severity": "CRITICAL"})
        assert resp.status_code == 200
        body = resp.json()
        assert all(item["severity"] == "CRITICAL" for item in body["items"])


# ===========================================================================
# Incident update
# ===========================================================================

class TestUpdateIncident:
    def test_update_incident_mitigated(self, client: TestClient) -> None:
        """PATCH is_mitigated=True flips the mitigation flag."""
        asset_id = _create_asset(client)
        create_resp = client.post(
            "/api/v1/incidents/",
            json=_incident_payload(asset_id),
        )
        incident_id = create_resp.json()["id"]
        assert create_resp.json()["is_mitigated"] is False

        patch_resp = client.patch(
            f"/api/v1/incidents/{incident_id}",
            json={"is_mitigated": True, "ai_analysis": "Confirmed false-positive."},
        )
        assert patch_resp.status_code == 200
        body = patch_resp.json()
        assert body["is_mitigated"] is True
        assert body["ai_analysis"] == "Confirmed false-positive."

    def test_update_incident_not_found(self, client: TestClient) -> None:
        """PATCH on missing incident returns 404."""
        resp = client.patch("/api/v1/incidents/999999", json={"is_mitigated": True})
        assert resp.status_code == 404
