"""
operations_report.py — Security Operations (SOC Shift/Daily) Report generator.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Incident, IncidentTimelineEvent, AITriageRun, SecurityEvent, WebFinding


def generate_operations_report_data(
    db: Session,
    report_id: str,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
    title: Optional[str] = None,
    include_ai_narrative: bool = True,
) -> Dict[str, Any]:
    """Compile structured SOC operations shift report from database activity logs."""
    now = datetime.now(timezone.utc)

    # 1. New Incidents in period
    inc_query = select(Incident)
    if period_start:
        inc_query = inc_query.where(Incident.timestamp >= period_start)
    if period_end:
        inc_query = inc_query.where(Incident.timestamp <= period_end)
    incidents = list(db.execute(inc_query.order_by(Incident.timestamp.desc())).scalars().all())

    # 2. Timeline events (Lifecycle transitions, triage requests)
    tl_query = select(IncidentTimelineEvent)
    if period_start:
        tl_query = tl_query.where(IncidentTimelineEvent.timestamp >= period_start)
    if period_end:
        tl_query = tl_query.where(IncidentTimelineEvent.timestamp <= period_end)
    timeline_events = list(db.execute(tl_query.order_by(IncidentTimelineEvent.timestamp.desc())).scalars().all())

    # 3. Triage runs
    triage_runs = list(db.execute(select(AITriageRun).order_by(AITriageRun.id.desc())).scalars().all())
    completed_triage = len([t for t in triage_runs if t.status == "COMPLETED"])
    pending_triage = len([t for t in triage_runs if t.status in ("PENDING", "RUNNING")])

    # 4. Status counts
    resolved_count = len([i for i in incidents if i.lifecycle_status in ("RESOLVED", "FALSE_POSITIVE") or i.is_mitigated])
    investigating_count = len([i for i in incidents if i.lifecycle_status == "INVESTIGATING"])
    open_count = len([i for i in incidents if i.lifecycle_status in ("OPEN", "ACKNOWLEDGED") and not i.is_mitigated])

    summary = (
        f"Laporan operasional Security Operations Center (SOC) KAWAL SIBER. "
        f"Mencatat {len(incidents)} insiden dalam pengawasan, {len(timeline_events)} aktivitas audit timeline, "
        f"{completed_triage} proses AI triage diselesaikan, dan {resolved_count} insiden tuntas dimitigasi. "
        f"Terdapat {open_count} insiden aktif yang masih menunggu tindak lanjut operasional."
    )

    ai_narrative = ""
    if include_ai_narrative:
        ai_narrative = (
            f"Evaluasi Shift SOC: Rasio penyelesaian insiden berada pada angka "
            f"{round((resolved_count / max(len(incidents), 1)) * 100, 1)}%. "
            f"Fokus operasional shift berikutnya: prioritaskan penyelidikan terhadap {investigating_count} insiden "
            f"yang sedang berjalan dan lakukan verifikasi penutupan tiket mitigasi sebelum pergantian jadwal."
        )

    items = [
        {
            "id": f"TL-{te.id}",
            "waktu": te.timestamp.strftime("%Y-%m-%d %H:%M:%S") if te.timestamp else "-",
            "tipe_event": te.event_type,
            "insiden": f"INC#{te.incident_id}",
            "deskripsi": (te.description or "-")[:80],
        }
        for te in timeline_events[:30]
    ]

    return {
        "report_id": report_id,
        "report_type": "OPERATIONS",
        "title": title or "Security Operations Center (SOC) Daily Operations Report",
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "generated_by": "KAWAL SIBER SOC Watch Officer",
        "executive_summary": summary,
        "ai_narrative": ai_narrative,
        "metrics": {
            "total_insiden_diawasi": len(incidents),
            "insiden_tuntas_dimitigasi": resolved_count,
            "insiden_sedang_diinvestigasi": investigating_count,
            "insiden_menunggu_respon": open_count,
            "total_aktivitas_operasional": len(timeline_events),
            "ai_triage_selesai": completed_triage,
            "ai_triage_tertunda": pending_triage,
        },
        "items": items,
        "source_count": len(incidents) + len(timeline_events) + len(triage_runs),
    }

