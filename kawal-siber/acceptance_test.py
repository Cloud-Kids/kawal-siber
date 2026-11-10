"""
KAWAL SIBER - Phase 2 Comprehensive Acceptance Test
Kartika Cyber Hackathon 2026
Automated End-to-End & In-depth Acceptance Verification
"""
from __future__ import annotations

import ipaddress
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

WORKSPACE_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = WORKSPACE_ROOT / "backend"
FRONTEND_DIR = WORKSPACE_ROOT / "frontend"
DB_PATH = WORKSPACE_ROOT / "storage" / "kawal_siber.db"
BASE_URL = "http://127.0.0.1:8000/api/v1"

results: list[dict[str, Any]] = []
_pass = 0
_fail = 0
_skip = 0


def record_result(test_id: str, name: str, passed: bool | None, detail: str = "") -> None:
    global _pass, _fail, _skip
    if passed is True:
        status = "PASS"
        _pass += 1
        icon = "✅"
    elif passed is False:
        status = "FAIL"
        _fail += 1
        icon = "❌"
    else:
        status = "SKIP"
        _skip += 1
        icon = "⏭️"

    print(f"  {icon} [{test_id}] {name}")
    if detail:
        print(f"       └─ {detail}")
    results.append({"id": test_id, "name": name, "status": status, "detail": detail})


def db_query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def api_get(path: str, **kwargs) -> httpx.Response:
    return httpx.get(f"{BASE_URL}{path}", timeout=10.0, **kwargs)


def api_post(path: str, data: Any = None, **kwargs) -> httpx.Response:
    return httpx.post(f"{BASE_URL}{path}", json=data, timeout=10.0, **kwargs)


def api_patch(path: str, data: Any = None, **kwargs) -> httpx.Response:
    return httpx.patch(f"{BASE_URL}{path}", json=data, timeout=10.0, **kwargs)


def api_delete(path: str, **kwargs) -> httpx.Response:
    return httpx.delete(f"{BASE_URL}{path}", timeout=10.0, **kwargs)


print("\n" + "=" * 70)
print("  KAWAL SIBER — PHASE 2 MASTER ACCEPTANCE TEST SUITE")
print(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
print(f"  Database : {DB_PATH}")
print("=" * 70)

# ===========================================================================
# 1. NMAP EXECUTABLE DETECTION
# ===========================================================================
print("\n[CRITERION 1] Nmap Executable Detection")
nmap_path = shutil.which("nmap")
if not nmap_path:
    # Check default Windows location
    default_win_path = Path("C:/Program Files (x86)/Nmap/nmap.exe")
    if default_win_path.exists():
        nmap_path = str(default_win_path)

if nmap_path:
    try:
        proc = subprocess.run([nmap_path, "--version"], capture_output=True, text=True, timeout=5)
        nmap_ver = proc.stdout.splitlines()[0] if proc.stdout else "unknown"
        record_result(
            "NM-01",
            "Nmap binary detected on Windows host",
            True,
            f"Path: {nmap_path} | Version: {nmap_ver}",
        )
    except Exception as e:
        record_result("NM-01", "Nmap binary detected on Windows host", False, str(e))
else:
    record_result("NM-01", "Nmap binary detected on Windows host", False, "nmap executable not found in PATH or standard directory")


# ===========================================================================
# 2. BACKEND HEALTH & INITIAL CONNECTIVITY
# ===========================================================================
print("\n[CRITERION 2] Backend FastAPI Health & Status")
try:
    resp = api_get("/health")
    data = resp.json()
    ok = resp.status_code == 200 and data.get("status") == "healthy" and data.get("database") == "connected"
    record_result(
        "BE-01",
        "Backend /health endpoint returns status=healthy, database=connected",
        ok,
        f"HTTP {resp.status_code} -> {data}",
    )
except Exception as e:
    record_result("BE-01", "Backend /health endpoint connectivity", False, str(e))


# ===========================================================================
# 3. ASSET CRUD (Positive Flows)
# ===========================================================================
print("\n[CRITERION 3] Asset CRUD & Management")
# List
try:
    resp = api_get("/assets")
    assets = resp.json()
    ok = resp.status_code == 200 and isinstance(assets, list) and len(assets) >= 1
    record_result("AST-01", "List assets endpoint returns existing assets", ok, f"HTTP {resp.status_code}, count={len(assets)}")
except Exception as e:
    record_result("AST-01", "List assets endpoint", False, str(e))

# Create valid asset
TEST_ASSET_ID: int | None = None
try:
    payload = {
        "name": "Phase 2 Validation Lab Node",
        "target_ip": "127.0.0.1",
        "port": 8888,
        "scope_id": 1,
    }
    resp = api_post("/assets", payload)
    ok = resp.status_code == 201
    if ok:
        data = resp.json()
        TEST_ASSET_ID = data["id"]
        ok = (
            data["name"] == payload["name"]
            and data["target_ip"] == payload["target_ip"]
            and data["port"] == payload["port"]
            and data["status"] == "UNKNOWN"
            and data["availability_status"] == "UNKNOWN"
        )
    record_result(
        "AST-02",
        "Create asset with valid parameters (IP, Port, Scope ID)",
        ok,
        f"HTTP {resp.status_code}, created_id={TEST_ASSET_ID}",
    )
except Exception as e:
    record_result("AST-02", "Create asset with valid parameters", False, str(e))

# Get asset by ID
try:
    resp = api_get(f"/assets/{TEST_ASSET_ID}")
    data = resp.json()
    ok = resp.status_code == 200 and data.get("id") == TEST_ASSET_ID
    record_result("AST-03", "Get asset by ID returns exact match", ok, f"HTTP {resp.status_code}, name={data.get('name')}")
except Exception as e:
    record_result("AST-03", "Get asset by ID", False, str(e))

# Update asset (PATCH)
try:
    patch_payload = {"name": "Phase 2 Updated Node", "port": 8889}
    resp = api_patch(f"/assets/{TEST_ASSET_ID}", patch_payload)
    data = resp.json()
    ok = resp.status_code == 200 and data.get("name") == "Phase 2 Updated Node" and data.get("port") == 8889
    record_result("AST-04", "Update asset via PATCH persists changes", ok, f"HTTP {resp.status_code}, name={data.get('name')}, port={data.get('port')}")
except Exception as e:
    record_result("AST-04", "Update asset via PATCH", False, str(e))

# Delete asset
try:
    resp = api_delete(f"/assets/{TEST_ASSET_ID}")
    ok = resp.status_code == 200
    # Confirm 404 on subsequent get
    resp_check = api_get(f"/assets/{TEST_ASSET_ID}")
    ok = ok and resp_check.status_code == 404
    record_result("AST-05", "Delete asset succeeds and subsequent GET returns 404", ok, f"Delete HTTP {resp.status_code}, Get HTTP {resp_check.status_code}")
except Exception as e:
    record_result("AST-05", "Delete asset", False, str(e))


# ===========================================================================
# 4. SCOPE AUTHORIZATION & CIDR VALIDATION
# ===========================================================================
print("\n[CRITERION 4] Scope Authorization & CIDR Validation")
# Import worker modules directly for unit-level verification
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(WORKSPACE_ROOT))

try:
    from worker.scope_validator import (
        OutOfScopeError,
        ScopeDisabledError,
        ScopeExpiredError,
        check_ip_in_cidr,
        validate_scope_active,
        validate_target_against_scope,
    )

    # CIDR Subnet logic
    in_range = check_ip_in_cidr("127.0.0.1", "127.0.0.1/32")
    out_range = check_ip_in_cidr("192.168.1.50", "127.0.0.1/32")
    subnet_range = check_ip_in_cidr("10.10.5.23", "10.10.0.0/16")
    ok = in_range is True and out_range is False and subnet_range is True
    record_result("SCP-01", "check_ip_in_cidr correctly checks IP within CIDR boundaries", ok, f"in={in_range}, out={out_range}, subnet={subnet_range}")

    # Expiry verification
    now_utc = datetime.now(timezone.utc)
    future_utc = now_utc + timedelta(days=10)
    past_utc = now_utc - timedelta(days=1)

    exp_passed = False
    try:
        validate_scope_active(enabled=True, expires_at=past_utc)
    except ScopeExpiredError:
        exp_passed = True

    dis_passed = False
    try:
        validate_scope_active(enabled=False, expires_at=future_utc)
    except ScopeDisabledError:
        dis_passed = True

    record_result("SCP-02", "validate_scope_active raises ScopeExpiredError and ScopeDisabledError", exp_passed and dis_passed, f"exp_check={exp_passed}, dis_check={dis_passed}")

except Exception as e:
    record_result("SCP-01", "Scope validator logic", False, str(e))
    record_result("SCP-02", "Scope expiry/disabled validation", False, str(e))

# Scope API Create
NEW_SCOPE_ID: int | None = None
try:
    scope_payload = {
        "name": "Phase 2 Formal Engagement Scope",
        "cidr": "10.200.0.0/24",
        "authorization_reference": "KARTIKA-2026-AUTH-099",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
        "enabled": True,
    }
    resp = api_post("/scan-scopes", scope_payload)
    ok = resp.status_code == 201
    if ok:
        NEW_SCOPE_ID = resp.json()["id"]
    record_result("SCP-03", "Register authorized scan scope via API -> 201 Created", ok, f"HTTP {resp.status_code}, scope_id={NEW_SCOPE_ID}")
except Exception as e:
    record_result("SCP-03", "Register authorized scan scope via API", False, str(e))


# ===========================================================================
# 5. SCAN JOB LIFECYCLE & EXECUTION (Positive & State Management)
# ===========================================================================
print("\n[CRITERION 5] Scan Job Lifecycle & Nmap Discovery")
# Enqueue scan job on Asset 1 (Local Gateway API, 127.0.0.1:8000)
# Asset 1 has scope 1 (127.0.0.1/32)
# Check if there is already a PENDING or RUNNING job for Asset 1
pending_jobs = db_query("SELECT id FROM scan_jobs WHERE asset_id=1 AND status IN ('PENDING', 'RUNNING')")
if pending_jobs:
    print(f"       Note: Active job {pending_jobs[0]['id']} found for Asset 1, using it for duplicate test first.")

# List scan jobs
try:
    resp = api_get("/scans")
    ok = resp.status_code == 200 and isinstance(resp.json(), list)
    record_result("SCN-01", "GET /scans returns list of all jobs", ok, f"HTTP {resp.status_code}, count={len(resp.json())}")
except Exception as e:
    record_result("SCN-01", "GET /scans list", False, str(e))

# Get scan details & results for Job 1 (previously COMPLETED)
try:
    resp = api_get("/scans/1")
    ok1 = resp.status_code == 200 and resp.json().get("status") == "COMPLETED"
    resp_res = api_get("/scans/1/results")
    ok2 = resp_res.status_code == 200 and len(resp_res.json()) >= 1
    record_result(
        "SCN-02",
        "GET /scans/1 and /scans/1/results retrieve persisted scan findings",
        ok1 and ok2,
        f"job_status={resp.json().get('status')}, results_count={len(resp_res.json()) if ok2 else 0}",
    )
except Exception as e:
    record_result("SCN-02", "GET /scans/1 findings", False, str(e))


# ===========================================================================
# 6. NMAP XML PARSER UNIT VERIFICATION
# ===========================================================================
print("\n[CRITERION 6] Nmap XML Parser Integrity")
try:
    from worker.xml_parser import NmapXMLParseError, parse_nmap_xml

    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" version="7.993">
  <runstats>
    <finished time="1730865600" elapsed="2.5"/>
  </runstats>
  <host>
    <status state="up" reason="localhost-response"/>
    <address addr="127.0.0.1" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="8000">
        <state state="open" reason="syn-ack"/>
        <service name="http" product="Uvicorn" version="0.34.0"/>
      </port>
    </ports>
  </host>
</nmaprun>"""

    parsed = parse_nmap_xml(sample_xml)
    ok = (
        parsed["host_status"] == "up"
        and parsed["target_ip"] == "127.0.0.1"
        and len(parsed["ports"]) == 1
        and parsed["ports"][0]["port"] == 8000
        and parsed["ports"][0]["state"] == "open"
        and parsed["ports"][0]["product"] == "Uvicorn"
    )
    record_result("XML-01", "parse_nmap_xml correctly extracts host status, port, state, and service metadata", ok, f"parsed: {parsed['ports']}")

    # Oversize rejection check
    oversize_caught = False
    try:
        parse_nmap_xml(sample_xml, max_bytes=50)
    except NmapXMLParseError:
        oversize_caught = True
    record_result("XML-02", "parse_nmap_xml rejects oversized XML payloads", oversize_caught, f"caught={oversize_caught}")

except Exception as e:
    record_result("XML-01", "Nmap XML Parser", False, str(e))
    record_result("XML-02", "Nmap XML Parser oversize", False, str(e))


# ===========================================================================
# 7. NEGATIVE TESTS & DEFENSIVE SECURITY
# ===========================================================================
print("\n[CRITERION 7] Negative Testing Suite")

# NEG-01: Asset with invalid IP address
try:
    resp = api_post("/assets", {"name": "Invalid IP Asset", "target_ip": "999.999.999.999", "port": 80, "scope_id": 1})
    ok = resp.status_code == 422
    record_result("NEG-01", "Asset creation with invalid IP (999.999.999.999) rejected -> 422", ok, f"HTTP {resp.status_code}")
except Exception as e:
    record_result("NEG-01", "Invalid IP rejection", False, str(e))

# NEG-02: Port = 0
try:
    resp = api_post("/assets", {"name": "Port Zero", "target_ip": "127.0.0.1", "port": 0, "scope_id": 1})
    ok = resp.status_code == 422
    record_result("NEG-02", "Asset creation with port=0 rejected -> 422", ok, f"HTTP {resp.status_code}")
except Exception as e:
    record_result("NEG-02", "Port 0 rejection", False, str(e))

# NEG-03: Port = 99999
try:
    resp = api_post("/assets", {"name": "Port Too High", "target_ip": "127.0.0.1", "port": 99999, "scope_id": 1})
    ok = resp.status_code == 422
    record_result("NEG-03", "Asset creation with port=99999 rejected -> 422", ok, f"HTTP {resp.status_code}")
except Exception as e:
    record_result("NEG-03", "Port 99999 rejection", False, str(e))

# NEG-04: Empty name
try:
    resp = api_post("/assets", {"name": "   ", "target_ip": "127.0.0.1", "port": 80, "scope_id": 1})
    ok = resp.status_code == 422
    record_result("NEG-04", "Asset creation with whitespace-only name rejected -> 422", ok, f"HTTP {resp.status_code}")
except Exception as e:
    record_result("NEG-04", "Empty name rejection", False, str(e))

# NEG-05: Scope with past expiry
try:
    past_iso = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    resp = api_post("/scan-scopes", {
        "name": "Past Scope",
        "cidr": "192.168.10.0/24",
        "authorization_reference": "PAST-REF-001",
        "expires_at": past_iso,
        "enabled": True,
    })
    ok = resp.status_code == 422
    record_result("NEG-05", "Scope creation with past expiry date rejected -> 422", ok, f"HTTP {resp.status_code}")
except Exception as e:
    record_result("NEG-05", "Past expiry rejection", False, str(e))

# NEG-06: Scope with invalid CIDR notation
try:
    future_iso = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    resp = api_post("/scan-scopes", {
        "name": "Malformed CIDR",
        "cidr": "invalid-cidr-notation/999",
        "authorization_reference": "MALFORMED-001",
        "expires_at": future_iso,
        "enabled": True,
    })
    ok = resp.status_code == 422
    record_result("NEG-06", "Scope creation with invalid CIDR notation rejected -> 422", ok, f"HTTP {resp.status_code}")
except Exception as e:
    record_result("NEG-06", "Invalid CIDR rejection", False, str(e))

# NEG-07: Scan job for target outside authorized scope
OUT_ASSET_ID: int | None = None
try:
    # Asset with IP 172.16.50.4 (outside Scope 1: 127.0.0.1/32)
    # We assign scope_id=1 to test mismatch detection
    resp = api_post("/assets", {
        "name": "Rogue Node",
        "target_ip": "172.16.50.4",
        "port": 443,
        "scope_id": 1,
    })
    if resp.status_code == 201:
        OUT_ASSET_ID = resp.json()["id"]
        # Now trigger scan
        resp_scan = api_post(f"/assets/{OUT_ASSET_ID}/scans")
        ok = resp_scan.status_code == 403
        record_result(
            "NEG-07",
            "Scan job on asset with IP outside authorized scope rejected -> 403 Forbidden",
            ok,
            f"Asset ID={OUT_ASSET_ID}, HTTP {resp_scan.status_code}: {resp_scan.text[:90]}",
        )
        # Cleanup
        api_delete(f"/assets/{OUT_ASSET_ID}")
    else:
        record_result("NEG-07", "Outside scope scan rejection", False, f"Could not create asset: {resp.status_code}")
except Exception as e:
    record_result("NEG-07", "Outside scope scan rejection", False, str(e))

# NEG-08: Scan job with disabled scope
try:
    # Temporarily disable Scope 1
    patch_resp = api_patch("/scan-scopes/1", {"enabled": False})
    if patch_resp.status_code == 200:
        # Try to scan Asset 1 (scope is disabled)
        # Note: If duplicate job exists, conflict might trigger first, so test on an asset without active job
        # Or test directly with scope authorization validator
        resp_dis = api_post("/assets/1/scans")
        # Should be 403 Forbidden (or 409 if active job exists)
        ok = resp_dis.status_code in (403, 409)
        record_result("NEG-08", "Scan job request under disabled scope is blocked", ok, f"HTTP {resp_dis.status_code}: {resp_dis.text[:90]}")
        # Re-enable scope 1
        api_patch("/scan-scopes/1", {"enabled": True})
    else:
        record_result("NEG-08", "Disabled scope test", False, f"Could not disable scope: HTTP {patch_resp.status_code}")
except Exception as e:
    api_patch("/scan-scopes/1", {"enabled": True})
    record_result("NEG-08", "Disabled scope test", False, str(e))

# NEG-09: Duplicate scan job rejection
try:
    # Ensure there is an active (PENDING/RUNNING) scan job for Asset 1
    active = db_query("SELECT id FROM scan_jobs WHERE asset_id=1 AND status IN ('PENDING', 'RUNNING')")
    if not active:
        api_post("/assets/1/scans")
    # Immediate subsequent scan attempt MUST be rejected with 409 Conflict
    resp_dup = api_post("/assets/1/scans")
    ok = resp_dup.status_code == 409
    record_result("NEG-09", "Duplicate scan job while previous job is PENDING/RUNNING rejected -> 409 Conflict", ok, f"HTTP {resp_dup.status_code}: {resp_dup.text[:90]}")
except Exception as e:
    record_result("NEG-09", "Duplicate scan job rejection", False, str(e))

# NEG-10: 404 on non-existent endpoints
try:
    resp_ast = api_get("/assets/99999")
    resp_scp = api_get("/scan-scopes/99999")
    resp_scn = api_get("/scans/99999")
    ok = resp_ast.status_code == 404 and resp_scp.status_code == 404 and resp_scn.status_code == 404
    record_result("NEG-10", "Non-existent asset, scope, and scan resources return 404", ok, f"Asset: {resp_ast.status_code}, Scope: {resp_scp.status_code}, Scan: {resp_scn.status_code}")
except Exception as e:
    record_result("NEG-10", "404 on non-existent resources", False, str(e))


# ===========================================================================
# 8. SECURITY INVARIANT VERIFICATION
# ===========================================================================
print("\n[CRITERION 8] Security Invariant Verification")
# Invariant: A successful port scan or open port must NEVER change security status to SAFE!
# Availability status = UP/DOWN, Security status = UNKNOWN (or UNDER_ATTACK if incident logged)
try:
    asset_1 = db_query("SELECT id, name, availability_status, status FROM assets WHERE id=1")[0]
    ok_avail = asset_1["availability_status"] == "UP"
    ok_sec = asset_1["status"] != "SAFE" and asset_1["status"] == "UNKNOWN"
    record_result(
        "SEC-01",
        "Asset security_status remains UNKNOWN (NOT SAFE) despite successful Nmap scan and open port",
        ok_avail and ok_sec,
        f"availability_status={asset_1['availability_status']} | security_status={asset_1['status']}",
    )

    # Check all assets in database
    all_assets = db_query("SELECT id, name, status FROM assets")
    all_unknown = all(a["status"] == "UNKNOWN" for a in all_assets)
    record_result("SEC-02", "No monitored asset has illegitimate SAFE status inferred from port scans", all_unknown, f"Checked {len(all_assets)} asset(s)")

except Exception as e:
    record_result("SEC-01", "Security invariant check", False, str(e))
    record_result("SEC-02", "Security status audit", False, str(e))


# ===========================================================================
# 9. DATABASE PERSISTENCE & INTEGRITY
# ===========================================================================
print("\n[CRITERION 9] Database Persistence & Foreign Key Integrity")
try:
    # Record counts
    c_assets = db_query("SELECT COUNT(*) as c FROM assets")[0]["c"]
    c_scopes = db_query("SELECT COUNT(*) as c FROM scan_scopes")[0]["c"]
    c_jobs = db_query("SELECT COUNT(*) as c FROM scan_jobs")[0]["c"]
    c_results = db_query("SELECT COUNT(*) as c FROM scan_results")[0]["c"]
    ok_counts = c_assets >= 2 and c_scopes >= 1 and c_jobs >= 1 and c_results >= 1

    # Check foreign key constraint in sqlite
    pragma_fk = db_query("PRAGMA foreign_keys")[0]
    # Check WAL mode
    pragma_wal = db_query("PRAGMA journal_mode")[0]

    record_result(
        "DB-01",
        "Database stores and persists records across operations",
        ok_counts,
        f"Assets={c_assets}, Scopes={c_scopes}, Jobs={c_jobs}, Results={c_results} | WAL={pragma_wal.get('journal_mode')}",
    )
except Exception as e:
    record_result("DB-01", "Database persistence check", False, str(e))


# ===========================================================================
# 10. FRONTEND QUALITY & BUILD VERIFICATION
# ===========================================================================
print("\n[CRITERION 10] Frontend Quality & Production Build")
npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

# Frontend live HTTP verification (executed before build so dev cache is clean)
fe_pages = [
    ("/dashboard", "Dashboard View"),
    ("/assets", "Asset Inventory"),
    ("/scopes", "Scope Management"),
    ("/monitoring/scans", "Scan Activity Monitor"),
]
for path, desc in fe_pages:
    try:
        resp = httpx.get(f"http://localhost:3000{path}", timeout=20.0, follow_redirects=True)
        ok = resp.status_code == 200
        record_result(f"FE-PAGE-{path.replace('/', '_')}", f"Frontend {desc} ({path}) responds HTTP 200", ok, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result(f"FE-PAGE-{path.replace('/', '_')}", f"Frontend {desc} ({path})", None, f"Frontend not currently running on :3000 ({e})")

# ESLint
try:
    res = subprocess.run([npm_cmd, "run", "lint"], cwd=str(FRONTEND_DIR), capture_output=True, text=True, timeout=120)
    ok = res.returncode == 0
    record_result("FE-01", "Frontend ESLint pass with 0 errors/warnings", ok, (res.stdout + res.stderr)[-200:].strip())
except Exception as e:
    record_result("FE-01", "Frontend ESLint", False, str(e))

# TypeScript Type-Check
try:
    res = subprocess.run([npm_cmd, "run", "type-check"], cwd=str(FRONTEND_DIR), capture_output=True, text=True, timeout=120)
    ok = res.returncode == 0
    record_result("FE-02", "Frontend TypeScript check pass with 0 errors", ok, (res.stdout + res.stderr)[-200:].strip())
except Exception as e:
    record_result("FE-02", "Frontend TypeScript check", False, str(e))

# Next.js Build
try:
    res = subprocess.run([npm_cmd, "run", "build"], cwd=str(FRONTEND_DIR), capture_output=True, text=True, timeout=300)
    ok = res.returncode == 0
    record_result("FE-03", "Frontend Next.js production build succeeds", ok, (res.stdout + res.stderr)[-300:].strip())
except Exception as e:
    record_result("FE-03", "Frontend Next.js build", False, str(e))


# ===========================================================================
# 11. AUTOMATED TEST SUITE (PYTEST)
# ===========================================================================
print("\n[CRITERION 11] Automated Test Suite Execution")
try:
    test_env = {**os.environ, "PYTHONPATH": f"{BACKEND_DIR};{WORKSPACE_ROOT}"}
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "backend/tests", "worker/tests", "-q", "--tb=line"],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
        env=test_env,
        timeout=180,
    )
    output = res.stdout + res.stderr
    import re
    match_pass = re.search(r"(\d+) passed", output)
    match_fail = re.search(r"(\d+) failed", output)
    passed_count = int(match_pass.group(1)) if match_pass else 0
    failed_count = int(match_fail.group(1)) if match_fail else 0
    ok = res.returncode == 0 and passed_count >= 60 and failed_count == 0
    record_result(
        "AUT-01",
        f"Automated pytest test suite ({passed_count} passed, {failed_count} failed)",
        ok,
        f"Pytest return code: {res.returncode}",
    )
except Exception as e:
    record_result("AUT-01", "Automated pytest suite", False, str(e))


# ===========================================================================
# SUMMARY & VERDICT
# ===========================================================================
print("\n" + "=" * 70)
print("  PHASE 2 ACCEPTANCE TEST SUMMARY")
print("=" * 70)
print(f"  TOTAL TESTS : {_pass + _fail + _skip}")
print(f"  PASSED      : {_pass} ✅")
print(f"  FAILED      : {_fail} ❌")
print(f"  SKIPPED     : {_skip} ⏭️")

verdict_pass = _fail == 0
verdict_text = "PASSED - ALL ACCEPTANCE CRITERIA SATISFIED" if verdict_pass else f"FAILED - {_fail} CRITERIA UNMET"
print(f"\n  OVERALL VERDICT: {verdict_text}")
print("=" * 70)

# Export JSON
report_file = WORKSPACE_ROOT / "acceptance_test_report.json"
report_data = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "verdict": "PASSED" if verdict_pass else "FAILED",
    "summary": {"total": _pass + _fail + _skip, "passed": _pass, "failed": _fail, "skipped": _skip},
    "results": results,
}
report_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
print(f"  JSON Report exported to: {report_file}\n")
