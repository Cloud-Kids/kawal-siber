"""
executive_report.py — Executive Security Report generator.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Asset, Incident, ScanJob, SecurityEvent, WebAssessment, WebFinding


def generate_executive_report_data(
    db: Session,
    report_id: str,
    title: Optional[str] = None,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
    include_ai_narrative: bool = True,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compile structured executive security report data from actual database queries."""
    now = datetime.now(timezone.utc)

    # 1. Asset Metrics
    total_assets = db.execute(select(func.count()).select_from(Asset)).scalar_one()
    safe_assets = db.execute(select(func.count()).select_from(Asset).where(Asset.status == "SAFE")).scalar_one()
    attack_assets = db.execute(select(func.count()).select_from(Asset).where(Asset.status == "UNDER_ATTACK")).scalar_one()
    down_assets = db.execute(select(func.count()).select_from(Asset).where(Asset.availability_status == "DOWN")).scalar_one()

    # 2. Incident Metrics
    inc_query = select(Incident)
    if period_start:
        inc_query = inc_query.where(Incident.timestamp >= period_start)
    if period_end:
        inc_query = inc_query.where(Incident.timestamp <= period_end)

    incidents = list(db.execute(inc_query.order_by(Incident.timestamp.desc())).scalars().all())
    total_incidents = len(incidents)
    critical_incidents = len([i for i in incidents if i.severity == "CRITICAL"])
    high_incidents = len([i for i in incidents if i.severity == "HIGH"])
    open_incidents = len([i for i in incidents if not i.is_mitigated])

    # 3. Web & Network Findings
    total_web_findings = db.execute(select(func.count()).select_from(WebFinding)).scalar_one()
    total_ids_alerts = db.execute(select(func.count()).select_from(SecurityEvent).where(SecurityEvent.event_type == "alert")).scalar_one()
    total_events = db.execute(select(func.count()).select_from(SecurityEvent)).scalar_one()

    # Completed & Failed Assessments (Nmap scans + Deep Eye web assessments)
    completed_scans = db.execute(
        select(func.count()).select_from(ScanJob).where(ScanJob.status == "COMPLETED")
    ).scalar_one()
    failed_scans = db.execute(
        select(func.count()).select_from(ScanJob).where(ScanJob.status == "FAILED")
    ).scalar_one()
    completed_web_assessments = db.execute(
        select(func.count()).select_from(WebAssessment).where(WebAssessment.status == "COMPLETED")
    ).scalar_one()
    failed_web_assessments = db.execute(
        select(func.count()).select_from(WebAssessment).where(WebAssessment.status == "FAILED")
    ).scalar_one()
    completed_assessments = completed_scans + completed_web_assessments

    # Unique assets with completed scans
    assessed_assets_count = db.execute(
        select(func.count(func.distinct(ScanJob.asset_id))).where(ScanJob.status == "COMPLETED")
    ).scalar_one()

    # ---------------------------------------------------------------------------
    # 4. Dimensional Security Posture Model (Separation of Concerns)
    # Dimensions:
    # 1. assessment_status: Has assessment been performed?
    # 2. baseline_compliance: Are explicit configuration controls validated?
    # 3. threat_detection_status: Are active threats/incidents detected in telemetry?
    # 4. telemetry_health: Is sensor and scanning telemetry active and healthy?
    # 5. risk_severity: Critical, High, Medium, Low, None, Unknown.
    # ---------------------------------------------------------------------------

    # Dimension 1: Assessment Status
    if total_assets == 0:
        dim_assessment_status = "NOT_ASSESSED"
    elif completed_assessments == 0:
        if failed_scans > 0 or failed_web_assessments > 0:
            dim_assessment_status = "FAILED"
        else:
            dim_assessment_status = "NO_ASSESSMENT_PERFORMED"
    elif assessed_assets_count >= total_assets:
        dim_assessment_status = "COMPLETED_FULL_COVERAGE"
    else:
        dim_assessment_status = "COMPLETED_PARTIAL_COVERAGE"

    # Dimension 2: Baseline Compliance
    # A configuration baseline can be validated regardless of whether threats later emerge.
    # A detected threat must NOT erase the fact that a configuration baseline was verified!
    dim_baseline_compliance = "NOT_EVALUATED"
    baseline_validated = False
    baseline_info: Dict[str, Any] = {}

    if parameters and isinstance(parameters.get("security_baseline"), dict):
        base_cfg = parameters["security_baseline"]
        baseline_name = base_cfg.get("name") or base_cfg.get("baseline_name")
        required_controls = base_cfg.get("required_controls") or base_cfg.get("controls") or []
        if baseline_name and isinstance(required_controls, list) and len(required_controls) > 0:
            all_controls_valid = all(
                isinstance(c, dict)
                and c.get("status") in ("PASS", "VALIDATED", "COMPLIANT")
                and bool(c.get("evidence"))
                and bool(c.get("validated_at"))
                for c in required_controls
            )
            if all_controls_valid and total_assets > 0 and assessed_assets_count >= total_assets:
                baseline_validated = True
                dim_baseline_compliance = "COMPLIANT_BASELINE_VERIFIED"
                baseline_info = {
                    "baseline_name": baseline_name,
                    "controls_count": len(required_controls),
                    "validation_timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "VALIDATED",
                }
            else:
                dim_baseline_compliance = "NON_COMPLIANT"
                baseline_info = {
                    "baseline_name": baseline_name,
                    "controls_count": len(required_controls),
                    "status": "NON_COMPLIANT",
                    "reason": "CONTROLS_FAILED_OR_INCOMPLETE_COVERAGE",
                }

    # Dimension 3: Threat Detection Status
    if total_assets == 0 and total_events == 0 and completed_assessments == 0:
        dim_threat_detection = "UNKNOWN_NO_TELEMETRY"
    elif critical_incidents > 0 or high_incidents > 0 or total_incidents > 0 or attack_assets > 0 or total_web_findings > 0:
        dim_threat_detection = "THREATS_DETECTED"
    elif completed_assessments > 0 or total_events > 0:
        dim_threat_detection = "NO_DETECTED_THREATS"
    else:
        dim_threat_detection = "UNKNOWN"

    # Dimension 4: Telemetry Health
    if total_events == 0 and total_assets == 0:
        dim_telemetry_health = "NO_TELEMETRY"
    elif (failed_scans > 0 or failed_web_assessments > 0) and completed_assessments == 0:
        dim_telemetry_health = "DEGRADED"
    elif total_events > 0 and completed_assessments > 0:
        dim_telemetry_health = "HEALTHY_ACTIVE"
    elif total_events > 0:
        dim_telemetry_health = "PASSIVE_TELEMETRY_ONLY"
    else:
        dim_telemetry_health = "DEGRADED" if total_assets > 0 else "NO_TELEMETRY"

    # Dimension 5: Risk Severity
    if critical_incidents > 0 or attack_assets > 0:
        dim_risk_severity = "CRITICAL"
    elif high_incidents > 0:
        dim_risk_severity = "HIGH"
    elif total_incidents > 0 or total_web_findings > 0:
        dim_risk_severity = "MEDIUM"
    elif total_assets == 0:
        dim_risk_severity = "UNKNOWN"
    else:
        dim_risk_severity = "NONE_IN_SCOPE"

    # ---------------------------------------------------------------------------
    # Composite Posture Calculation (Deterministic Decision Tree)
    # Six Top-Level Posture States with Multiple Sub-Reason Decision Branches
    # ---------------------------------------------------------------------------
    if total_assets == 0 and total_events == 0 and total_incidents == 0 and completed_assessments == 0:
        posture = "NOT ASSESSED"
        posture_reason = "INSUFFICIENT SECURITY TELEMETRY"
        telemetry_status = "NO_AVAILABLE_TELEMETRY"
    elif critical_incidents > 0 or attack_assets > 0:
        posture = "WASPADA TINGGI (CRITICAL DEFENSE)"
        posture_reason = "CONFIRMED CRITICAL ATTACKS OR ASSETS UNDER ATTACK"
        telemetry_status = "CONFIRMED_THREATS_DETECTED"
    elif high_incidents > 0:
        posture = "PERHATIAN (ELEVATED RISK)"
        posture_reason = "ELEVATED RISK INCIDENTS DETECTED"
        telemetry_status = "CONFIRMED_THREATS_DETECTED"
    elif total_assets > 0 and (failed_scans > 0 or failed_web_assessments > 0) and completed_assessments == 0:
        posture = "PERHATIAN (TELEMETRY DEGRADED)"
        posture_reason = "TELEMETRY DEGRADED (FAILED ASSESSMENT JOBS)"
        telemetry_status = "TELEMETRY_DEGRADED"
    elif total_assets > 0 and completed_assessments == 0 and total_events == 0 and total_incidents == 0:
        posture = "NOT ASSESSED"
        posture_reason = "NO ASSESSMENT PERFORMED"
        telemetry_status = "NO_ASSESSMENT_PERFORMED"
    elif baseline_validated and dim_threat_detection == "NO_DETECTED_THREATS" and total_events > 0:
        posture = "TERVERIFIKASI (BASELINE VERIFIED)"
        posture_reason = "100% ASSETS ASSESSED WITH EXPLICITLY VALIDATED SECURITY BASELINE AND ACTIVE TELEMETRY"
        telemetry_status = "BASELINE_VERIFIED"
    elif baseline_validated and dim_threat_detection == "THREATS_DETECTED":
        # Threat detected does NOT erase configuration baseline verification
        posture = "PERHATIAN (BASELINE VERIFIED WITH DETECTED THREATS)"
        posture_reason = "SECURITY BASELINE COMPLIANT BUT ACTIVE THREATS OR FINDINGS DETECTED"
        telemetry_status = "CONFIRMED_THREATS_DETECTED"
    elif completed_assessments > 0 or total_events > 0:
        posture = "TERKENDALI (NO FINDINGS DETECTED)"
        posture_reason = "ASSESSMENTS COMPLETED WITH NO DETECTED THREATS IN SCOPE (BASELINE NOT VALIDATED)"
        telemetry_status = "NO_FINDINGS_DETECTED"
    else:
        posture = "NOT ASSESSED"
        posture_reason = "INSUFFICIENT SECURITY TELEMETRY"
        telemetry_status = "NO_AVAILABLE_TELEMETRY"

    security_dimensions = {
        "assessment_status": dim_assessment_status,
        "baseline_compliance": dim_baseline_compliance,
        "threat_detection_status": dim_threat_detection,
        "telemetry_health": dim_telemetry_health,
        "risk_severity": dim_risk_severity,
    }

    # Scoped Assessment Metadata
    coverage_pct = round((assessed_assets_count / total_assets * 100), 1) if total_assets > 0 else 0.0
    assessment_scope = {
        "assessed_assets_count": assessed_assets_count,
        "total_registered_assets": total_assets,
        "asset_coverage_pct": coverage_pct,
        "completed_scans": completed_scans,
        "failed_scans": failed_scans,
        "completed_web_assessments": completed_web_assessments,
        "failed_web_assessments": failed_web_assessments,
        "suricata_telemetry_events": total_events,
        "sensor_active": total_events > 0,
        "baseline_validated": baseline_validated,
        "baseline_info": baseline_info,
        "security_dimensions": security_dimensions,
        "scope_caveat": (
            "Hasil pemindaian Nmap dan asesmen web Deep Eye yang bersih hanya membuktikan "
            "ketiadaan temuan pada port dan endpoint yang diuji dalam cakupan audit dan "
            "bukan bukti ketiadaan ancaman siber secara menyeluruh. "
            "Ketiadaan telemetri sensor Suricata bukan bukti konfirmasi jaringan bersih."
        ),
    }

    # 5. Narrative
    if posture == "NOT ASSESSED":
        summary = (
            f"Laporan eksekutif pertahanan siber teritorial untuk periode audit terkini. "
            f"Status postur keamanan: {posture} (Alasan: {posture_reason}). "
            f"Belum ada aset terdaftar, telemetri keamanan jaringan, atau asesmen kerentanan aktif yang diselesaikan. "
            f"PERINGATAN OPERASIONAL: Ketiadaan temuan tidak sama dengan jaminan sistem aman. "
            f"Angka nol tidak boleh disamakan dengan bukti keamanan terverifikasi."
        )
        ai_narrative = ""
        if include_ai_narrative:
            ai_narrative = (
                f"Evaluasi Inteligensi KAWAL SIBER: Postur pertahanan dievaluasi sebagai {posture} "
                f"karena {posture_reason.lower()}. "
                f"Rekomendasi prioritas pimpinan: (1) Daftarkan target aset teritorial ke dalam inventaris, "
                f"(2) Definisikan scope pemindaian Nmap yang sah, "
                f"(3) Jalankan Web Security Assessment dan aktifkan penangkapan telemetri Suricata IDS."
            )
    else:
        summary = (
            f"Laporan eksekutif pertahanan siber teritorial untuk periode audit terkini. "
            f"Dari total {total_assets} aset terdaftar, teridentifikasi {total_incidents} insiden siber "
            f"({critical_incidents} kritis, {high_incidents} tinggi) dengan status postur: {posture}. "
            f"Sebanyak {open_incidents} insiden memerlukan investigasi dan penutupan mitigasi lanjutan oleh operator."
        )
        ai_narrative = ""
        if include_ai_narrative:
            ai_narrative = (
                f"Evaluasi Inteligensi KAWAL SIBER: Postur pertahanan saat ini berada pada tingkat {posture}. "
                f"Faktor risiko utama dipicu oleh {critical_incidents} insiden kritis dan {total_ids_alerts} peringatan IDS aktif. "
                f"Rekomendasi prioritas pimpinan: (1) Pastikan isolasi firewall pada aset bertatus UNDER_ATTACK, "
                f"(2) Percepat penutupan insiden terbuka ({open_incidents} tertunda), "
                f"(3) Lakukan verifikasi ulang temuan kerentanan web ({total_web_findings} temuan terdeteksi)."
            )

    # Top incidents list for executive review
    items = [
        {
            "id": f"INC-{inc.id}",
            "waktu": inc.timestamp.strftime("%Y-%m-%d %H:%M") if inc.timestamp else "-",
            "target": f"Asset #{inc.asset_id}",
            "jenis_serangan": inc.attack_type,
            "keparahan": inc.severity,
            "status": inc.lifecycle_status or ("RESOLVED" if inc.is_mitigated else "OPEN"),
        }
        for inc in incidents[:15]
    ]

    return {
        "report_id": report_id,
        "report_type": "EXECUTIVE",
        "title": title or "Executive Security & Cyber Defense Posture Report",
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "generated_by": "KAWAL SIBER Security Operations Command",
        "executive_summary": summary,
        "ai_narrative": ai_narrative,
        "posture": posture,
        "posture_reason": posture_reason,
        "telemetry_status": telemetry_status,
        "total_assets": total_assets,
        "total_incidents": total_incidents,
        "completed_assessments": completed_assessments,
        "metrics": {
            "postur_keamanan": posture,
            "alasan_postur": posture_reason,
            "status_telemetri": telemetry_status,
            "total_aset_teritorial": total_assets,
            "aset_aman": safe_assets,
            "aset_diserang": attack_assets,
            "total_insiden_terdeteksi": total_incidents,
            "insiden_kritis": critical_incidents,
            "insiden_tinggi": high_incidents,
            "insiden_belum_tuntas": open_incidents,
            "temuan_web_deep_eye": total_web_findings,
            "alert_suricata_ids": total_ids_alerts,
            "asesmen_selesai": completed_assessments,
        },
        "assessment_scope": assessment_scope,
        "security_dimensions": security_dimensions,
        "items": items,
        "source_count": total_assets + total_incidents + total_web_findings,
    }

