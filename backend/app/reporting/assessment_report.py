"""
assessment_report.py — Security Assessment Report generator.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Asset, ScanJob, ScanResult, WebAssessment, WebFinding, WebTarget


def generate_assessment_report_data(
    db: Session,
    report_id: str,
    asset_id: Optional[int] = None,
    title: Optional[str] = None,
    include_ai_narrative: bool = True,
) -> Dict[str, Any]:
    """Compile structured security assessment data from Nmap scans and Deep Eye findings."""
    now = datetime.now(timezone.utc)

    # 1. Assets
    asset_stmt = select(Asset)
    if asset_id:
        asset_stmt = asset_stmt.where(Asset.id == asset_id)
    assets = list(db.execute(asset_stmt).scalars().all())

    # 2. Findings
    findings_stmt = select(WebFinding).order_by(WebFinding.id.desc())
    if asset_id:
        # Find web targets linked to asset
        target_ids = [
            row[0]
            for row in db.execute(select(WebTarget.id).where(WebTarget.asset_id == asset_id)).all()
        ]
        if target_ids:
            findings_stmt = findings_stmt.where(WebFinding.web_target_id.in_(target_ids))
    findings = list(db.execute(findings_stmt).scalars().all())

    # 3. Port scans
    scans_count = db.execute(select(func.count()).select_from(ScanJob)).scalar_one()
    open_ports_count = db.execute(
        select(func.count()).select_from(ScanResult).where(ScanResult.state == "open")
    ).scalar_one()

    crit_findings = len([f for f in findings if f.severity == "CRITICAL"])
    high_findings = len([f for f in findings if f.severity == "HIGH"])
    med_findings = len([f for f in findings if f.severity == "MEDIUM"])

    summary = (
        f"Laporan asesmen kerentanan dan audit permukaan serang (attack surface) KAWAL SIBER. "
        f"Meliputi audit inventaris {len(assets)} aset, {scans_count} eksekusi pemindaian port Nmap "
        f"({open_ports_count} port aktif terverifikasi), dan {len(findings)} temuan kerentanan aplikasi web Deep Eye "
        f"({crit_findings} kritis, {high_findings} tinggi, {med_findings} sedang)."
    )

    ai_narrative = ""
    if include_ai_narrative:
        ai_narrative = (
            f"Analisis Evaluasi Postur: Permukaan serang teridentifikasi pada {open_ports_count} port layanan aktif. "
            f"Prioritas mitigasi rekayasa perangkat lunak: "
            f"(1) Terapkan parameter query yang aman (prepared statements) untuk mencegah SQL Injection, "
            f"(2) Implementasikan Content-Security-Policy (CSP) dan flag cookie HttpOnly/Secure, "
            f"(3) Batasi akses layanan administratif hanya dari subnet manajemen berotorisasi."
        )

    items = [
        {
            "id": f"FIND-{f.id}",
            "judul": f.title,
            "jenis": f.vulnerability_type,
            "keparahan": f.severity,
            "url_terdampak": f.affected_url[:60],
            "status_triase": f.finding_status,
        }
        for f in findings[:25]
    ]

    return {
        "report_id": report_id,
        "report_type": "ASSESSMENT",
        "title": title or "Comprehensive Security & Vulnerability Assessment Report",
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "generated_by": "KAWAL SIBER Security Assessment Team",
        "executive_summary": summary,
        "ai_narrative": ai_narrative,
        "metrics": {
            "total_aset_diasesmen": len(assets),
            "total_port_terbuka_nmap": open_ports_count,
            "total_riwayat_scan_nmap": scans_count,
            "total_temuan_kerentanan": len(findings),
            "temuan_kritis": crit_findings,
            "temuan_tinggi": high_findings,
            "temuan_sedang": med_findings,
        },
        "items": items,
        "source_count": len(assets) + len(findings) + open_ports_count,
    }

