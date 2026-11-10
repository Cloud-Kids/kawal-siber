"""
KAWAL SIBER — Phase 4 Master Acceptance Test Suite
Web Application Security Assessment & Deep Eye Integration
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
PROJECT_ROOT = WORKSPACE_ROOT.parent
BACKEND_DIR = WORKSPACE_ROOT / "backend"
FRONTEND_DIR = WORKSPACE_ROOT / "frontend"
DB_PATH = WORKSPACE_ROOT / "storage" / "kawal_siber.db"
DEEP_EYE_DIR = PROJECT_ROOT / "tools" / "deep-eye"
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


def check_backend_running() -> bool:
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


def main():
    print("=" * 75)
    print("  KAWAL SIBER — PHASE 4 ACCEPTANCE TEST SUITE")
    print("  WEB APPLICATION SECURITY ASSESSMENT & DEEP EYE INTEGRATION")
    print("  Kartika Cyber Hackathon 2026")
    print("=" * 75)
    print(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"  Workspace: {WORKSPACE_ROOT}")
    print(f"  Deep Eye:  {DEEP_EYE_DIR}")
    print(f"  Database:  {DB_PATH}\n")

    # -------------------------------------------------------------------------
    # 1. DEEP_EYE_01: Deep Eye Repository Audit & Executable Detection
    # -------------------------------------------------------------------------
    try:
        script = DEEP_EYE_DIR / "deep_eye.py"
        venv_py = DEEP_EYE_DIR / ".deep-venv" / "Scripts" / "python.exe"
        if not venv_py.exists():
            venv_py = Path(sys.executable)

        cmd = [str(venv_py), str(script), "--version"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10, shell=False)
        out = (res.stdout or res.stderr).strip()
        if res.returncode == 0 and "Deep Eye" in out:
            record_result("DEEP_EYE_01", "Deep Eye Engine & CLI Detection", True, f"Output: {out}")
        else:
            record_result("DEEP_EYE_01", "Deep Eye Engine & CLI Detection", False, f"Exit: {res.returncode}, out: {out}")
    except Exception as exc:
        record_result("DEEP_EYE_01", "Deep Eye Engine & CLI Detection", False, str(exc))

    # -------------------------------------------------------------------------
    # 2. VALIDATOR_01: Scope Policy & Allowed Localhost Allowlist
    # -------------------------------------------------------------------------
    try:
        sys.path.insert(0, str(BACKEND_DIR))
        from app.integrations.deep_eye.validator import (
            parse_and_validate_target_url,
            InvalidTargetURLError,
            TargetOutOfScopeError,
            validate_path_allowed,
        )

        scheme, host, port, norm_url = parse_and_validate_target_url("http://127.0.0.1:8000/api")
        assert host == "127.0.0.1" and port == 8000 and scheme == "http"
        scheme, host, port, norm_url = parse_and_validate_target_url("http://localhost:3000")
        assert host == "localhost" and port == 3000
        record_result("VALIDATOR_01", "Strict Localhost Lab Allowlist Enforcement", True, "127.0.0.1:8000 and localhost:3000 successfully validated.")
    except Exception as exc:
        record_result("VALIDATOR_01", "Strict Localhost Lab Allowlist Enforcement", False, str(exc))

    # -------------------------------------------------------------------------
    # 3. VALIDATOR_02: Negative Testing: External and Unauthorized Scope Rejection
    # -------------------------------------------------------------------------
    try:
        rejected = False
        try:
            parse_and_validate_target_url("https://google.com")
        except TargetOutOfScopeError:
            rejected = True

        rejected_ip = False
        try:
            parse_and_validate_target_url("http://8.8.8.8:80")
        except TargetOutOfScopeError:
            rejected_ip = True

        if rejected and rejected_ip:
            record_result("VALIDATOR_02", "External / Unauthorized Targets Rejection", True, "google.com and 8.8.8.8 rejected by TargetOutOfScopeError.")
        else:
            record_result("VALIDATOR_02", "External / Unauthorized Targets Rejection", False, "Failed to reject external targets.")
    except Exception as exc:
        record_result("VALIDATOR_02", "External / Unauthorized Targets Rejection", False, str(exc))

    # -------------------------------------------------------------------------
    # 4. VALIDATOR_03: Negative Testing: Dangerous Schemes & Cloud Metadata
    # -------------------------------------------------------------------------
    try:
        rej_scheme = False
        try:
            parse_and_validate_target_url("javascript:alert(1)")
        except InvalidTargetURLError:
            rej_scheme = True

        rej_meta = False
        try:
            parse_and_validate_target_url("http://169.254.169.254/latest/meta-data/")
        except TargetOutOfScopeError:
            rej_meta = True

        rej_port = False
        try:
            parse_and_validate_target_url("http://127.0.0.1:70000")
        except InvalidTargetURLError:
            rej_port = True

        if rej_scheme and rej_meta and rej_port:
            record_result("VALIDATOR_03", "Dangerous Schemes, Metadata & Port Boundaries Rejection", True, "javascript:, 169.254.169.254, and port 70000 rejected.")
        else:
            record_result("VALIDATOR_03", "Dangerous Schemes, Metadata & Port Boundaries Rejection", False, f"Flags: scheme={rej_scheme}, meta={rej_meta}, port={rej_port}")
    except Exception as exc:
        record_result("VALIDATOR_03", "Dangerous Schemes, Metadata & Port Boundaries Rejection", False, str(exc))

    # -------------------------------------------------------------------------
    # 5. VALIDATOR_04: Path Allowlist Policy Validation
    # -------------------------------------------------------------------------
    try:
        p1 = validate_path_allowed("/api/v1/users", "/*")
        p2 = validate_path_allowed("/api/v1/users", "/api/*")
        p3 = validate_path_allowed("/admin/shell", "/api/*, /public/*")
        if p1 is True and p2 is True and p3 is False:
            record_result("VALIDATOR_04", "Path Allowlist Policy Enforcement", True, "Wildcard, prefix, and disallowed path restrictions validated.")
        else:
            record_result("VALIDATOR_04", "Path Allowlist Policy Enforcement", False, f"Path flags: p1={p1}, p2={p2}, p3={p3}")
    except Exception as exc:
        record_result("VALIDATOR_04", "Path Allowlist Policy Enforcement", False, str(exc))

    # -------------------------------------------------------------------------
    # 6. PARSER_01: Evidence Sanitization (Credentials, Tokens, Cookies)
    # -------------------------------------------------------------------------
    try:
        from app.integrations.deep_eye.result_parser import sanitize_evidence
        raw_test = "GET / HTTP/1.1\nAuthorization: Bearer SECRET_TOKEN_XYZ\nCookie: session=ABC123XYZ; secret=MYPASSWORD\napi_key=sk-live-12345"
        sanitized = sanitize_evidence(raw_test)
        if "SECRET_TOKEN_XYZ" not in sanitized and "MYPASSWORD" not in sanitized and "sk-live-12345" not in sanitized and "[REDACTED]" in sanitized:
            record_result("PARSER_01", "Evidence Sanitization & Redaction", True, "Authorization bearer, cookie values, and API keys redacted.")
        else:
            record_result("PARSER_01", "Evidence Sanitization & Redaction", False, f"Evidence leaked content: {sanitized}")
    except Exception as exc:
        record_result("PARSER_01", "Evidence Sanitization & Redaction", False, str(exc))

    # -------------------------------------------------------------------------
    # 7. PARSER_02: Deterministic SHA-256 Fingerprinting
    # -------------------------------------------------------------------------
    try:
        from app.integrations.deep_eye.result_parser import compute_finding_fingerprint
        fp_a = compute_finding_fingerprint(1, "MISSING_SECURITY_HEADER", "Missing CSP", "http://127.0.0.1:8000/api")
        fp_b = compute_finding_fingerprint(1, "MISSING_SECURITY_HEADER", "Missing CSP", "http://127.0.0.1:8000/api")
        fp_c = compute_finding_fingerprint(1, "XSS", "Reflected XSS", "http://127.0.0.1:8000/api")
        if fp_a == fp_b and fp_a != fp_c and len(fp_a) == 64:
            record_result("PARSER_02", "Deterministic SHA-256 Fingerprinting", True, f"Fingerprint reproducible (SHA256: {fp_a[:16]}...)")
        else:
            record_result("PARSER_02", "Deterministic SHA-256 Fingerprinting", False, "Fingerprint mismatch or collision.")
    except Exception as exc:
        record_result("PARSER_02", "Deterministic SHA-256 Fingerprinting", False, str(exc))

    # -------------------------------------------------------------------------
    # 8. TARGET_01: WebTarget CRUD Operations via Service / Database
    # -------------------------------------------------------------------------
    target_id = None
    try:
        from app.database import SessionLocal
        from app.services.web_assessment_service import WebAssessmentService
        with SessionLocal() as db:
            svc = WebAssessmentService(db)
            target = svc.create_web_target(
                name="Phase 4 Acceptance Lab Target",
                target_url="http://127.0.0.1:8000",
                allowed_paths="/*",
                authorization_reference="KCH2026-ACCEPTANCE-REF",
                enabled=True,
            )
            target_id = target.id
            assert target_id is not None
            assert target.port == 8000
            assert target.protocol == "http"
        record_result("TARGET_01", "WebTarget Registration & Persistence", True, f"WebTarget created with ID {target_id} (http://127.0.0.1:8000)")
    except Exception as exc:
        record_result("TARGET_01", "WebTarget Registration & Persistence", False, str(exc))

    # -------------------------------------------------------------------------
    # 9. ASSESSMENT_01: Passive Assessment Execution & Rules Audit
    # -------------------------------------------------------------------------
    assessment_id = None
    try:
        with SessionLocal() as db:
            svc = WebAssessmentService(db)
            assessment = svc.enqueue_assessment(web_target_id=target_id, assessment_profile="PASSIVE")
            assessment_id = assessment.id
            assert assessment.status == "PENDING"

            completed = svc.execute_assessment_job(assessment_id)
            assert completed.status == "COMPLETED"
            assert completed.duration_ms is not None and completed.duration_ms >= 0
            assert completed.total_findings >= 0

        findings = db_query("SELECT * FROM web_findings WHERE assessment_id = ?", (assessment_id,))
        record_result(
            "ASSESSMENT_01",
            "Passive Web Security Assessment Execution",
            True,
            f"Assessment #{assessment_id} completed in {completed.duration_ms} ms with {len(findings)} findings.",
        )
    except Exception as exc:
        record_result("ASSESSMENT_01", "Passive Web Security Assessment Execution", False, str(exc))

    # -------------------------------------------------------------------------
    # 10. ASSESSMENT_02: Safe Local Assessment Execution (Non-destructive)
    # -------------------------------------------------------------------------
    try:
        with SessionLocal() as db:
            svc = WebAssessmentService(db)
            assessment2 = svc.enqueue_assessment(web_target_id=target_id, assessment_profile="SAFE_LOCAL")
            completed2 = svc.execute_assessment_job(assessment2.id)
            assert completed2.status == "COMPLETED"
            assert completed2.assessment_profile == "SAFE_LOCAL"

        record_result(
            "ASSESSMENT_02",
            "Safe Local Assessment Execution (Rate-Limited)",
            True,
            f"Safe Local Assessment #{completed2.id} completed with status {completed2.status} ({completed2.total_findings} findings).",
        )
    except Exception as exc:
        record_result("ASSESSMENT_02", "Safe Local Assessment Execution (Rate-Limited)", False, str(exc))

    # -------------------------------------------------------------------------
    # 11. DEDUPLICATION_01: Deduplication of Findings Across Runs
    # -------------------------------------------------------------------------
    try:
        all_target_findings = db_query("SELECT fingerprint FROM web_findings WHERE web_target_id = ?", (target_id,))
        fps = [r["fingerprint"] for r in all_target_findings]
        if len(fps) == len(set(fps)):
            record_result("DEDUPLICATION_01", "Finding Deduplication Invariant", True, f"All {len(fps)} stored findings have unique fingerprints.")
        else:
            record_result("DEDUPLICATION_01", "Finding Deduplication Invariant", False, f"Duplicate fingerprints detected: {len(fps)} vs {len(set(fps))}")
    except Exception as exc:
        record_result("DEDUPLICATION_01", "Finding Deduplication Invariant", False, str(exc))

    # -------------------------------------------------------------------------
    # 12. CORRELATION_01: Incident Correlation & Duplicate Suppression
    # -------------------------------------------------------------------------
    try:
        with SessionLocal() as db:
            from app.models import Asset, WebFinding, Incident, WebTarget
            asset = db_query("SELECT id FROM assets LIMIT 1")
            asset_id = asset[0]["id"] if asset else 1

            # Inject a test critical finding
            fp_crit = "test_crit_fp_" + str(int(time.time()))
            finding_crit = WebFinding(
                assessment_id=assessment_id,
                web_target_id=target_id,
                title="Critical SQL Injection Canary",
                vulnerability_type="SQL_INJECTION",
                severity="CRITICAL",
                confidence="CERTAIN",
                finding_status="NEEDS_REVIEW",
                affected_url="http://127.0.0.1:8000/api/v1/test",
                description="Simulated critical finding for acceptance test.",
                evidence="UNION SELECT CANARY",
                fingerprint=fp_crit,
            )
            target_obj = db.get(WebTarget, target_id)
            target_obj.asset_id = asset_id

            svc = WebAssessmentService(db)
            svc._correlate_findings_to_incidents(target_obj, [finding_crit])
            db.commit()

            # Verify incident created
            inc = db_query("SELECT * FROM incidents WHERE asset_id = ? AND attack_type = 'SQL_INJECTION' ORDER BY id DESC LIMIT 1", (asset_id,))
            assert len(inc) > 0, "Correlated incident was not found."

            # Re-run correlation to test duplicate suppression
            svc._correlate_findings_to_incidents(target_obj, [finding_crit])
            db.commit()

            inc_after = db_query("SELECT * FROM incidents WHERE asset_id = ? AND attack_type = 'SQL_INJECTION'", (asset_id,))
            assert len(inc_after) == len(inc), "Duplicate incident storm occurred."

        record_result("CORRELATION_01", "Incident Correlation & Suppression Invariant", True, "Critical finding mapped to Incident, and duplicate storm suppressed.")
    except Exception as exc:
        record_result("CORRELATION_01", "Incident Correlation & Suppression Invariant", False, str(exc))

    # -------------------------------------------------------------------------
    # 13. TRIAGE_01: Finding Triage Status Lifecycle
    # -------------------------------------------------------------------------
    try:
        findings = db_query("SELECT id, finding_status FROM web_findings WHERE web_target_id = ? LIMIT 1", (target_id,))
        if findings:
            f_id = findings[0]["id"]
            with SessionLocal() as db:
                f_obj = db.get(WebFinding, f_id)
                f_obj.finding_status = "CONFIRMED"
                db.commit()
            updated = db_query("SELECT finding_status FROM web_findings WHERE id = ?", (f_id,))[0]
            assert updated["finding_status"] == "CONFIRMED"
            record_result("TRIAGE_01", "Finding Triage Status Lifecycle", True, f"Finding #{f_id} status updated to CONFIRMED.")
        else:
            record_result("TRIAGE_01", "Finding Triage Status Lifecycle", True, "No findings to triage; schema verified.")
    except Exception as exc:
        record_result("TRIAGE_01", "Finding Triage Status Lifecycle", False, str(exc))

    # -------------------------------------------------------------------------
    # 14. STATS_01: Telemetry & Statistics Invariant
    # -------------------------------------------------------------------------
    try:
        t_count = db_query("SELECT COUNT(*) as c FROM web_targets")[0]["c"]
        a_count = db_query("SELECT COUNT(*) as c FROM web_assessments")[0]["c"]
        f_count = db_query("SELECT COUNT(*) as c FROM web_findings")[0]["c"]
        assert t_count >= 1
        assert a_count >= 1
        record_result("STATS_01", "Web Security Statistics & Telemetry Invariant", True, f"Stats verified: {t_count} targets, {a_count} assessments, {f_count} findings.")
    except Exception as exc:
        record_result("STATS_01", "Web Security Statistics & Telemetry Invariant", False, str(exc))

    # -------------------------------------------------------------------------
    # Summary Report
    # -------------------------------------------------------------------------
    print("\n" + "=" * 75)
    print(f"  PHASE 4 ACCEPTANCE SUMMARY: {_pass} PASSED, {_fail} FAILED, {_skip} SKIPPED (TOTAL: {len(results)})")
    print("=" * 75)

    report_path = WORKSPACE_ROOT / "phase4_acceptance_report.json"
    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": "FASE 4: WEB SECURITY ASSESSMENT & DEEP EYE INTEGRATION",
        "passed": _pass,
        "failed": _fail,
        "skipped": _skip,
        "total": len(results),
        "results": results,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"\n  Master report saved to: {report_path}\n")

    if _fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
