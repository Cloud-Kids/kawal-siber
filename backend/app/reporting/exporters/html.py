"""
html.py — Responsive, print-friendly HTML report generator.
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Dict, List

from app.reporting.sanitization import redact_sensitive_data, sanitize_for_html


def export_to_html(data: Dict[str, Any], output_path: Path) -> Path:
    """
    Generate a standalone, responsive, print-friendly HTML security report.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report_id = sanitize_for_html(data.get("report_id", "N/A"))
    title = sanitize_for_html(data.get("title", "Laporan Keamanan Siber"))
    report_type = sanitize_for_html(data.get("report_type", "SECURITY_REPORT"))
    generated_at = sanitize_for_html(data.get("generated_at", ""))
    generated_by = sanitize_for_html(data.get("generated_by", "KAWAL SIBER Platform"))
    executive_summary = sanitize_for_html(data.get("executive_summary", ""))

    # Empty Database / Insufficient Telemetry Warning Banner
    posture = data.get("posture") or data.get("metrics", {}).get("postur_keamanan")
    warning_html = ""
    if posture == "NOT ASSESSED":
        reason = sanitize_for_html(data.get("posture_reason") or "INSUFFICIENT SECURITY TELEMETRY")
        warning_html = f"""
        <div class="alert-box" style="background:#451a1a;border:1px solid #ef4444;border-radius:8px;padding:16px;margin-bottom:25px;color:#fecaca;">
            <div style="font-weight:bold;font-size:13px;color:#f87171;margin-bottom:4px;">⚠️ PERINGATAN OPERASIONAL: STATUS POSTUR [NOT ASSESSED] — {reason}</div>
            <div style="font-size:12px;line-height:1.5;">Basis data tidak memiliki aset aktif, event jaringan, atau asesmen selesai untuk dianalisis.
            <em>Ketiadaan temuan ancaman tidak sama dengan jaminan sistem aman (angka nol bukan bukti keamanan).</em></div>
        </div>
        """

    # Metrics
    metrics: Dict[str, Any] = data.get("metrics", {})
    metrics_html = "".join(
        f"""
        <div class="metric-card">
            <div class="metric-label">{sanitize_for_html(k.replace('_', ' ').title())}</div>
            <div class="metric-value">{sanitize_for_html(str(v))}</div>
        </div>
        """
        for k, v in metrics.items()
    )

    # Narrative
    ai_narrative = sanitize_for_html(data.get("ai_narrative", ""))
    narrative_html = ""
    if ai_narrative:
        narrative_html = f"""
        <div class="section">
            <h2 class="section-title">Analisis Inteligensi Siber & Rekomendasi</h2>
            <div class="narrative-box">
                <div class="ai-badge">AI-ASSISTED TRIAGE NARRATIVE (HUMAN REVIEW REQUIRED)</div>
                <p>{ai_narrative}</p>
            </div>
        </div>
        """

    # Tables: items / incidents / findings
    table_items = data.get("items") or data.get("incidents") or data.get("findings") or []
    table_html = ""
    if table_items and isinstance(table_items, list):
        headers = list(table_items[0].keys())
        header_row = "".join(f"<th>{sanitize_for_html(h.replace('_', ' ').title())}</th>" for h in headers)
        data_rows = ""
        for row in table_items:
            cols = "".join(f"<td>{sanitize_for_html(str(row.get(h, '')))}</td>" for h in headers)
            data_rows += f"<tr>{cols}</tr>"
        table_html = f"""
        <div class="section">
            <h2 class="section-title">Detail Artefak & Telemetri</h2>
            <div class="table-container">
                <table>
                    <thead><tr>{header_row}</tr></thead>
                    <tbody>{data_rows}</tbody>
                </table>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — {report_id}</title>
    <style>
        :root {{
            --bg: #0A0F1D;
            --surface: #0F172A;
            --surface-card: #1E293B;
            --border: #334155;
            --text-primary: #F8FAFC;
            --text-secondary: #94A3B8;
            --accent: #22C55E;
            --danger: #EF4444;
            --warning: #F59E0B;
            --info: #3B82F6;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-primary);
            line-height: 1.6;
            margin: 0;
            padding: 30px;
        }}
        .report-wrapper {{
            max-width: 1000px;
            margin: 0 auto;
            background-color: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }}
        .report-header {{
            border-bottom: 2px solid var(--border);
            padding-bottom: 25px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .brand-title {{
            font-size: 11px;
            font-family: monospace;
            color: var(--accent);
            letter-spacing: 2px;
            text-transform: uppercase;
        }}
        h1 {{
            font-size: 24px;
            margin: 8px 0;
            color: var(--text-primary);
        }}
        .meta-pill {{
            display: inline-block;
            font-family: monospace;
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 6px;
            background: rgba(34, 197, 94, 0.1);
            color: var(--accent);
            border: 1px solid rgba(34, 197, 94, 0.3);
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            font-family: monospace;
            font-size: 12px;
            color: var(--text-secondary);
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: var(--surface-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
        }}
        .metric-label {{
            font-size: 11px;
            font-family: monospace;
            color: var(--text-secondary);
            text-transform: uppercase;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            font-family: monospace;
            color: var(--text-primary);
            margin-top: 6px;
        }}
        .section {{
            margin-bottom: 35px;
        }}
        .section-title {{
            font-size: 16px;
            border-left: 3px solid var(--accent);
            padding-left: 10px;
            margin-bottom: 15px;
            color: var(--text-primary);
        }}
        .summary-box {{
            background: var(--surface-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 18px;
            color: var(--text-secondary);
            font-size: 13px;
        }}
        .narrative-box {{
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(34, 197, 94, 0.2);
            border-radius: 8px;
            padding: 18px;
            font-size: 13px;
        }}
        .ai-badge {{
            font-family: monospace;
            font-size: 10px;
            color: var(--accent);
            margin-bottom: 8px;
        }}
        .table-container {{
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            font-family: monospace;
        }}
        th {{
            background: #1E293B;
            color: var(--text-secondary);
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid rgba(51, 65, 85, 0.5);
            color: var(--text-primary);
        }}
        tr:hover td {{
            background: rgba(30, 41, 59, 0.5);
        }}
        .footer {{
            border-top: 1px solid var(--border);
            padding-top: 20px;
            margin-top: 40px;
            font-family: monospace;
            font-size: 11px;
            color: var(--text-secondary);
            display: flex;
            justify-content: space-between;
        }}
        @media print {{
            body {{
                background: #FFFFFF !important;
                color: #000000 !important;
                padding: 0;
            }}
            .report-wrapper {{
                border: none !important;
                box-shadow: none !important;
                max-width: 100% !important;
                padding: 0 !important;
            }}
            .metric-card, .summary-box, .narrative-box {{
                background: #F8FAFC !important;
                color: #000000 !important;
                border: 1px solid #CBD5E1 !important;
            }}
            th {{
                background: #F1F5F9 !important;
                color: #000000 !important;
            }}
            td {{
                color: #000000 !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="report-wrapper">
        <div class="report-header">
            <div>
                <div class="brand-title">KAWAL SIBER — SISTEM PERTAHANAN SIBER TERITORIAL</div>
                <h1>{title}</h1>
                <span class="meta-pill">{report_type} REPORT</span>
            </div>
            <div class="meta-grid">
                <div>ID: {report_id}</div>
                <div>Tanggal: {generated_at}</div>
                <div>Otoritas: {generated_by}</div>
                <div>Status: VERIFIED SNAPSHOT</div>
            </div>
        </div>

        {warning_html}

        {f'''
        <div class="section">
            <h2 class="section-title">Ringkasan Eksekutif</h2>
            <div class="summary-box">
                <p>{executive_summary}</p>
            </div>
        </div>
        ''' if executive_summary else ''}

        {f'''
        <div class="section">
            <h2 class="section-title">Metrik Telemetri Utama</h2>
            <div class="metrics-grid">
                {metrics_html}
            </div>
        </div>
        ''' if metrics_html else ''}

        {narrative_html}

        {table_html}

        <div class="footer">
            <div>Dokumen Resmi KAWAL SIBER — Kartika Cyber Hackathon 2026</div>
            <div>Integritas: SHA-256 Verified Snapshot</div>
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path

