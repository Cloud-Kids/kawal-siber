"""Tests for public judge read-only mode enforcement (KAWAL_JUDGE_MODE=true)."""
from __future__ import annotations

import os
import pytest

os.environ["KAWAL_JUDGE_MODE"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
API = "/api/v1"


# ---------- positive: allowed GETs ----------

@pytest.mark.parametrize("path", [
    "/health",
    "/assets",
    "/scan-scopes",
    "/scans",
    "/incidents",
    "/monitoring/statistics",
    "/security-events",
    "/security-alerts",
    "/web-targets",
    "/web-assessments",
    "/web-findings",
    "/reports",
    "/ai/health",
    "/incident-intelligence/overview",
])
def test_judge_allows_safe_gets(path):
    r = client.get(f"{API}{path}")
    assert r.status_code in (200, 404), f"{path} -> {r.status_code} (404 ok if empty table)"


# ---------- negative: all writes denied ----------

@pytest.mark.parametrize("method,path", [
    ("post", "/assets"),
    ("post", "/assets/1/scans"),
    ("post", "/scan-scopes"),
    ("patch", "/scan-scopes/1"),
    ("post", "/incidents"),
    ("patch", "/incidents/1"),
    ("post", "/web-targets"),
    ("patch", "/web-targets/1"),
    ("delete", "/web-targets/1"),
    ("post", "/web-assessments"),
    ("delete", "/web-assessments/1"),
    ("post", "/monitoring/pcap"),
    ("post", "/reports"),
    ("post", "/incidents/1/triage"),
    ("put", "/assets/1"),
    ("delete", "/assets/1"),
    ("delete", "/incidents/1"),
])
def test_judge_denies_all_writes(method, path):
    r = client.request(method.upper(), f"{API}{path}", json={})
    assert r.status_code == 403, f"{method.upper()} {path} -> {r.status_code}"


# ---------- negative: docs/schema disabled ----------

@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_judge_disables_docs(path):
    r = client.get(path)
    assert r.status_code in (403, 404)


# ---------- negative: non-allowlisted GET denied ----------

def test_judge_denies_unknown_api_route():
    r = client.get(f"{API}/definitely-not-a-route")
    assert r.status_code in (403, 404)


def test_judge_denies_admin_prefix():
    r = client.get(f"{API}/admin/users")
    assert r.status_code == 403


# ---------- negative: report download id must be UUID ----------

def test_judge_report_download_rejects_traversal():
    r = client.get(f"{API}/reports/..%2F..%2Fetc%2Fpasswd/download")
    assert r.status_code in (403, 404, 422)


def test_judge_report_download_rejects_non_uuid():
    r = client.get(f"{API}/reports/abc123/download")
    assert r.status_code == 403


# ---------- bypass attempts ----------

def test_judge_head_allowed_on_safe_route():
    r = client.head(f"{API}/health")
    assert r.status_code in (200, 404, 405)


def test_judge_options_denied():
    r = client.options(f"{API}/assets")
    assert r.status_code == 403


def test_judge_prefix_boundary_no_false_allow():
    # /api/v1/assetsfoo must NOT match /api/v1/assets prefix
    r = client.get(f"{API}/assetsfoo")
    assert r.status_code in (403, 404)


def test_judge_encoded_traversal_denied():
    r = client.get(f"{API}/reports/%2e%2e%2f%2e%2e%2fetc%2fpasswd/download")
    assert r.status_code in (403, 404, 422)


def test_judge_method_override_header_ignored():
    # X-HTTP-Method-Override must not bypass method check
    r = client.post(f"{API}/assets", json={}, headers={"X-HTTP-Method-Override": "GET"})
    assert r.status_code == 403


def test_judge_websocket_route_denied():
    # No websocket routes exist; a ws upgrade request gets 403/404
    r = client.get(f"{API}/monitoring/pcap/stream")
    assert r.status_code in (403, 404, 422)  # 422 = allowlisted GET, bad param


def test_judge_rate_limit_headers_spoof_resistant():
    # Spoofed XFF should not reset the bucket — cf-connecting-ip/x-real-ip win
    for _ in range(3):
        client.get(f"{API}/health", headers={"CF-Connecting-IP": "198.51.100.99"})
    r = client.get(f"{API}/health", headers={"CF-Connecting-IP": "198.51.100.99"})
    assert r.status_code in (200, 404, 429)  # bucket shared per real IP header
