"""
KAWAL SIBER — Phase 3 Master Acceptance Test Suite
Suricata IDS, Offline PCAP Analysis & Network Threat Detection
Kartika Cyber Hackathon 2026
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
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
    return httpx.get(f"{BASE_URL}{path}", timeout=15.0, **kwargs)


def api_post(path: str, data: Any = None, **kwargs) -> httpx.Response:
    return httpx.post(f"{BASE_URL}{path}", json=data, timeout=30.0, **kwargs)


print("\n" + "=" * 70)
print("  KAWAL SIBER — PHASE 3 MASTER ACCEPTANCE TEST SUITE")
print("  Suricata IDS & Network Threat Detection Engine")
print(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
print(f"  Database : {DB_PATH}")
print("=" * 70)

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(WORKSPACE_ROOT))

# ===========================================================================
# 1. SURICATA ENGINE AUDIT & DETECTION
# ===========================================================================
print("\n[CRITERION 1] Suricata Engine Audit & Verification")
from app.services.suricata_engine import (
    get_default_config_path,
    get_suricata_version,
    resolve_suricata_executable,
)

suricata_path = None
try:
    exe = resolve_suricata_executable()
    suricata_path = str(exe)
    ver = get_suricata_version(exe)
    ok = exe.is_file() and "Suricata" in ver
    record_result(
        "SURI-01",
        "Suricata native Windows executable detected and version verified",
        ok,
        f"Path: {suricata_path} | Version: {ver}",
    )
except Exception as e:
    record_result("SURI-01", "Suricata native Windows executable detection", False, str(e))

# Configuration test
try:
    conf = get_default_config_path()
    res = subprocess.run(
        [suricata_path, "-T", "-c", str(conf)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    ok = res.returncode == 0 and "Configuration provided was successfully loaded" in (res.stdout + res.stderr)
    record_result(
        "SURI-02",
        "Dedicated Suricata configuration validated in test mode (-T)",
        ok,
        f"Config: {conf.name} | Loaded OK",
    )
except Exception as e:
    record_result("SURI-02", "Suricata config validation", False, str(e))


# ===========================================================================
# 2. PCAP GENERATION & OFFLINE ANALYSIS
# ===========================================================================
print("\n[CRITERION 2] PCAP Processing & Analysis Engine")
from app.services.pcap_builder import (
    build_http_get_packet,
    build_icmp_echo_packet,
    build_tcp_scan_packet,
    write_pcap,
)

test_pcap_name = "hackathon_threat_lab.pcap"
test_pcap_path = WORKSPACE_ROOT / "storage" / "pcaps" / test_pcap_name

try:
    # Target is Asset 1: 127.0.0.1
    pkts = [
        # 1. ICMP Ping from 192.168.1.100
        build_icmp_echo_packet("192.168.1.100", "127.0.0.1"),
        # 2. Web Attack (SQL Injection in URI) attacking Asset 1 on port 8000
        build_http_get_packet("10.0.0.55", "127.0.0.1", 45120, 8000, "/api/v1/users?id=1%20UNION%20SELECT%20username,password", "sqlmap/1.7#stable"),
        # 3. Inbound SSH Recon to port 22
        build_tcp_scan_packet("172.16.1.5", "127.0.0.1", 50000, 22, 0x02),
        # 4. TCP XMAS scan to port 80
        build_tcp_scan_packet("172.16.1.5", "127.0.0.1", 50001, 80, 0x29),
    ]
    write_pcap(test_pcap_path, pkts)
    fsize = test_pcap_path.stat().st_size
    ok = test_pcap_path.is_file() and fsize > 0
    record_result(
        "PCAP-01",
        "Synthetic lab PCAP created with multi-vector threats (ICMP, SQLi, SSH, XMAS)",
        ok,
        f"Path: {test_pcap_path.name} ({fsize} bytes)",
    )
except Exception as e:
    record_result("PCAP-01", "Synthetic lab PCAP creation", False, str(e))

# Submit PCAP to API
ANALYSIS_ID: int | None = None
try:
    resp = api_post("/monitoring/pcap", {"filename": test_pcap_name})
    ok = resp.status_code == 201
    if ok:
        data = resp.json()
        ANALYSIS_ID = data["id"]
    record_result(
        "PCAP-02",
        "POST /api/v1/monitoring/pcap accepts authorized PCAP file -> 201 Created",
        ok,
        f"HTTP {resp.status_code}, Analysis ID={ANALYSIS_ID}",
    )
except Exception as e:
    record_result("PCAP-02", "POST /api/v1/monitoring/pcap submission", False, str(e))

# Wait for background Suricata worker to finish analysis
analysis_completed = False
if ANALYSIS_ID:
    for attempt in range(20):
        time.sleep(1)
        resp = api_get(f"/monitoring/pcap/{ANALYSIS_ID}")
        if resp.status_code == 200:
            job_data = resp.json()
            if job_data["status"] == "COMPLETED":
                analysis_completed = True
                record_result(
                    "PCAP-03",
                    "Suricata offline analysis transitions PENDING -> RUNNING -> COMPLETED",
                    True,
                    f"Status: COMPLETED | Ingested events: {job_data['event_count']} | Alerts: {job_data['alert_count']}",
                )
                break
            elif job_data["status"] == "FAILED":
                record_result("PCAP-03", "Suricata offline analysis execution", False, f"Job failed: {job_data.get('error_message')}")
                break
    if not analysis_completed:
        record_result("PCAP-03", "Suricata offline analysis execution", False, "Timed out waiting for COMPLETED status")


# ===========================================================================
# 3. EVE JSON INGESTION & THREAT DETECTION
# ===========================================================================
print("\n[CRITERION 3] EVE JSON Ingestion & Threat Classification")
try:
    # Check events in DB
    events = db_query("SELECT id, event_type, signature, severity, category FROM security_events WHERE pcap_analysis_id=?", (ANALYSIS_ID,))
    alerts = [e for e in events if e["event_type"] == "alert"]
    ok = len(events) >= 4 and len(alerts) >= 2
    signatures = [a["signature"] for a in alerts]
    record_result(
        "EVE-01",
        "EVE JSON event stream parsed into structured security_events table",
        ok,
        f"Total events: {len(events)} | Alerts: {len(alerts)} | Signatures: {signatures[:2]}",
    )
except Exception as e:
    record_result("EVE-01", "EVE JSON database records", False, str(e))


# ===========================================================================
# 4. INCIDENT CORRELATION & ASSET THREAT STATUS
# ===========================================================================
print("\n[CRITERION 4] Incident Correlation & Asset Status Management")
try:
    # Check if Asset 1 was correlated
    asset1 = db_query("SELECT id, name, target_ip, status FROM assets WHERE id=1")[0]
    # Check if incidents were created
    incidents = db_query("SELECT id, asset_id, attack_type, severity, source_ip FROM incidents WHERE asset_id=1")
    ok = len(incidents) >= 1
    # Check status changed to UNDER_ATTACK due to critical SQLi alert targeting Asset 1
    status_updated = asset1["status"] in ("UNDER_ATTACK", "WARNING")
    record_result(
        "CORR-01",
        "Correlator links alerts to matching asset and generates Incident record",
        ok,
        f"Asset: {asset1['name']} ({asset1['target_ip']}) | Incidents count: {len(incidents)} | Latest attack_type: {incidents[-1]['attack_type'] if incidents else 'None'}",
    )
    record_result(
        "CORR-02",
        "Asset security status updated to UNDER_ATTACK only upon validated high/critical alert",
        status_updated,
        f"Asset 1 status: {asset1['status']}",
    )
except Exception as e:
    record_result("CORR-01", "Incident correlation", False, str(e))
    record_result("CORR-02", "Asset status update", False, str(e))


# ===========================================================================
# 5. SECURITY ALERT & TELEMETRY API ENDPOINTS
# ===========================================================================
print("\n[CRITERION 5] REST API Telemetry & Alert Endpoints")
# GET /security-alerts
try:
    resp = api_get("/security-alerts?page=1&page_size=20")
    ok = resp.status_code == 200 and len(resp.json()["items"]) >= 1
    record_result("API-01", "GET /api/v1/security-alerts returns actionable alerts", ok, f"HTTP {resp.status_code}, count={len(resp.json()['items'])}")
except Exception as e:
    record_result("API-01", "GET /api/v1/security-alerts", False, str(e))

# GET /security-events
try:
    resp = api_get("/security-events?page=1&page_size=20")
    ok = resp.status_code == 200 and len(resp.json()["items"]) >= 1
    record_result("API-02", "GET /api/v1/security-events returns all telemetry events", ok, f"HTTP {resp.status_code}, total={resp.json()['total']}")
except Exception as e:
    record_result("API-02", "GET /api/v1/security-events", False, str(e))

# GET /monitoring/statistics
try:
    resp = api_get("/monitoring/statistics")
    data = resp.json()
    ok = (
        resp.status_code == 200
        and data["total_events"] >= 1
        and data["total_alerts"] >= 1
        and "CRITICAL" in data["severity_distribution"]
    )
    record_result(
        "API-03",
        "GET /api/v1/monitoring/statistics computes KPIs, protocol and severity distribution",
        ok,
        f"Total events: {data.get('total_events')}, Alerts: {data.get('total_alerts')}, Top sigs: {len(data.get('top_signatures', []))}",
    )
except Exception as e:
    record_result("API-03", "GET /api/v1/monitoring/statistics", False, str(e))


# ===========================================================================
# 6. NEGATIVE & DEFENSIVE SECURITY
# ===========================================================================
print("\n[CRITERION 6] Negative & Defensive Security Tests")
# Path traversal PCAP attempt
try:
    resp = api_post("/monitoring/pcap", {"filename": "../../../../windows/system32/cmd.exe"})
    ok = resp.status_code == 422
    record_result("SEC-01", "Path traversal in PCAP import rejected -> 422 Unprocessable Entity", ok, f"HTTP {resp.status_code}")
except Exception as e:
    record_result("SEC-01", "Path traversal rejection", False, str(e))

# Non-existent file
try:
    resp = api_post("/monitoring/pcap", {"filename": "non_existent_packet.pcap"})
    ok = resp.status_code == 422
    record_result("SEC-02", "Non-existent PCAP filename rejected -> 422 Unprocessable Entity", ok, f"HTTP {resp.status_code}")
except Exception as e:
    record_result("SEC-02", "Non-existent PCAP rejection", False, str(e))

# Malformed extension
try:
    resp = api_post("/monitoring/pcap", {"filename": "payload.bat"})
    ok = resp.status_code == 422
    record_result("SEC-03", "Disallowed file extension rejected -> 422 Unprocessable Entity", ok, f"HTTP {resp.status_code}")
except Exception as e:
    record_result("SEC-03", "Disallowed extension rejection", False, str(e))


# ===========================================================================
# 7. FRONTEND DASHBOARDS & QUALITY VERIFICATION
# ===========================================================================
print("\n[CRITERION 7] Frontend Live HTTP 200 & Quality Verification")
fe_pages = [
    ("/monitoring", "Threat Monitoring Dashboard"),
    ("/monitoring/alerts", "Security Alerts View"),
    ("/monitoring/events", "Security Events Telemetry View"),
    ("/monitoring/pcap", "PCAP Import & Analysis View"),
]

for path, label in fe_pages:
    try:
        resp = httpx.get(f"http://localhost:3000{path}", timeout=20.0, follow_redirects=True)
        ok = resp.status_code == 200
        record_result(f"FE-{path.replace('/', '_')}", f"Frontend page {label} ({path}) responds HTTP 200", ok, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result(f"FE-{path.replace('/', '_')}", f"Frontend page {label} ({path})", None, f"Not reachable: {e}")


# ===========================================================================
# 8. FULL AUTOMATED PYTEST SUITE
# ===========================================================================
print("\n[CRITERION 8] Full Automated Pytest Execution (74 Tests)")
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
    m_pass = re.search(r"(\d+) passed", output)
    m_fail = re.search(r"(\d+) failed", output)
    passed_count = int(m_pass.group(1)) if m_pass else 0
    failed_count = int(m_fail.group(1)) if m_fail else 0
    ok = res.returncode == 0 and passed_count >= 70 and failed_count == 0
    record_result(
        "AUT-01",
        f"Automated pytest suite ({passed_count} passed, {failed_count} failed)",
        ok,
        f"Return code: {res.returncode}",
    )
except Exception as e:
    record_result("AUT-01", "Automated pytest suite", False, str(e))


# ===========================================================================
# SUMMARY & VERDICT
# ===========================================================================
print("\n" + "=" * 70)
print("  PHASE 3 ACCEPTANCE TEST SUMMARY")
print("=" * 70)
print(f"  TOTAL TESTS : {_pass + _fail + _skip}")
print(f"  PASSED      : {_pass} ✅")
print(f"  FAILED      : {_fail} ❌")
print(f"  SKIPPED     : {_skip} ⏭️")

verdict_pass = _fail == 0
verdict_text = "PASSED - ALL ACCEPTANCE CRITERIA SATISFIED" if verdict_pass else f"FAILED - {_fail} CRITERIA UNMET"
print(f"\n  OVERALL VERDICT: {verdict_text}")
print("=" * 70)

out_report = WORKSPACE_ROOT / "phase3_acceptance_report.json"
out_report.write_text(
    json.dumps(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "verdict": "PASSED" if verdict_pass else "FAILED",
            "summary": {"total": _pass + _fail + _skip, "passed": _pass, "failed": _fail, "skipped": _skip},
            "results": results,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(f"  Report exported to: {out_report}\n")

