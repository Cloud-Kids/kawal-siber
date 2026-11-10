"""
technical_report.py — Technical Incident Report generator.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Asset,
    Incident,
    IncidentEvidence,
    IncidentTimelineEvent,
    AITriageRun,
    ScanJob,
    ScanResult,
)


def generate_technical_report_data(
    db: Session,
    report_id: str,
    incident_id: Optional[int] = None,
    title: Optional[str] = None,
    include_ai_narrative: bool = True,
) -> Dict[str, Any]:
    """Compile structured technical incident report from actual database records."""
    now = datetime.now(timezone.utc)

    # 1. Fetch Incident
    if incident_id:
        incident = db.get(Incident, incident_id)
    else:
        # Get most recent critical or high incident
        incident = db.execute(
            select(Incident).order_by(Incident.id.desc())
        ).scalars().first()

    if not incident:
        return {
            "report_id": report_id,
            "report_type": "TECHNICAL",
            "title": title or "Technical Incident Forensic Report",
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "generated_by": "KAWAL SIBER Security Operations Command",
            "executive_summary": "Tidak ada insiden yang ditemukan untuk disusun ke dalam laporan teknis.",
            "metrics": {},
            "items": [],
            "source_count": 0,
        }

    # 2. Fetch Asset & Evidence
    asset = db.get(Asset, incident.asset_id) if incident.asset_id else None
    evidence_rows = list(
        db.execute(
            select(IncidentEvidence).where(IncidentEvidence.incident_id == incident.id)
        ).scalars().all()
    )
    timeline_rows = list(
        db.execute(
            select(IncidentTimelineEvent)
            .where(IncidentTimelineEvent.incident_id == incident.id)
            .order_by(IncidentTimelineEvent.timestamp.asc())
        ).scalars().all()
    )
    latest_triage = db.execute(
        select(AITriageRun)
        .where(AITriageRun.incident_id == incident.id)
        .order_by(AITriageRun.id.desc())
    ).scalars().first()

    # Metric separation
    suricata_ev = [e for e in evidence_rows if e.source_type == "SURICATA_EVENT"]
    web_ev = [e for e in evidence_rows if e.source_type == "WEB_FINDING"]
    nmap_ev = [e for e in evidence_rows if e.source_type == "NMAP_RESULT"]

    # Summary
    summary = (
        f"Laporan forensik teknis untuk Insiden #{incident.id} ({incident.attack_type} - {incident.severity}). "
        f"Serangan menyasar aset {asset.name if asset else 'N/A'} ({asset.target_ip if asset else '0.0.0.0'}:{asset.port if asset else 0}) "
        f"dari alamat sumber {incident.source_ip}. "
        f"Total bukti terkorelasi: {len(evidence_rows)} ({len(suricata_ev)} IDS, {len(web_ev)} Web, {len(nmap_ev)} Nmap). "
        f"Status siklus hidup terkini: {incident.lifecycle_status or 'OPEN'}."
    )

    ai_narrative = ""
    if include_ai_narrative and (latest_triage or incident.ai_analysis):
        ai_narrative = (
            f"Analisis Triase KAWAL SIBER: "
            f"{incident.ai_analysis or 'Triage otomatis telah dijalankan.'} "
            f"Tindakan investigasi yang disarankan: (1) Periksa paket capture pcap pada jendela waktu deteksi, "
            f"(2) Lakukan pengecekan integritas endpoint {asset.target_ip if asset else 'sasaran'}, "
            f"(3) Pastikan aturan filtering gateway memblokir alamat IP penyerang {incident.source_ip}."
        )

    # Itemized evidence list
    items = [
        {
            "id": f"EV-{ev.id}",
            "sumber": ev.source_type,
            "relasi": ev.relationship_type or "N/A",
            "ringkasan_bukti": ev.evidence_summary or "-",
            "waktu_bukti": ev.evidence_timestamp.strftime("%Y-%m-%d %H:%M") if ev.evidence_timestamp else "-",
        }
        for ev in evidence_rows
    ]

    return {
        "report_id": report_id,
        "report_type": "TECHNICAL",
        "title": title or f"Technical Incident Report — INC#{incident.id}",
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "generated_by": "KAWAL SIBER SOC Tier-2/Tier-3",
        "executive_summary": summary,
        "ai_narrative": ai_narrative,
        "metrics": {
            "incident_id": f"#{incident.id}",
            "tingkat_keparahan": incident.severity,
            "jenis_serangan": incident.attack_type,
            "ip_penyerang": incident.source_ip,
            "aset_sasaran": f"{asset.name if asset else 'N/A'} ({asset.target_ip if asset else '0.0.0.0'})",
            "status_siklus_hidup": incident.lifecycle_status or "OPEN",
            "jumlah_bukti_ids": len(suricata_ev),
            "jumlah_temuan_web": len(web_ev),
            "konteks_port_nmap": len(nmap_ev),
            "total_kronologi_timeline": len(timeline_rows),
        },
        "items": items,
        "source_count": len(evidence_rows) + len(timeline_rows),
    }

