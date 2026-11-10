"""
pdf.py — Corporate/Military-grade PDF report exporter using ReportLab.

Phase 6 Final Refinement:
- Two-pass `NumberedCanvas` rendering running header, running footer, and dynamic page counts ("Halaman X dari Y").
- Margins and printable bounds strictly maintained (36pt left/right, 54pt top/bottom; content strictly within 540pt width).
- Auto word-wrapped table cells preventing text overflow or clipping.
- Indonesian Unicode support verified.
- Visual empty-state handling for unassessed telemetry ("NOT ASSESSED").
- Cryptographic integrity audit block at document termination.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.reporting.sanitization import redact_sensitive_data

# A4 Geometry Standards:
# Width = 595.28 pt, Height = 841.89 pt.
# Margins: Left = 36 pt, Right = 36 pt, Top = 54 pt, Bottom = 54 pt.
# Printable Width = 595.28 - 36 - 36 = 523.28 pt.
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 36.0
RIGHT_MARGIN = 36.0
TOP_MARGIN = 54.0
BOTTOM_MARGIN = 54.0
PRINTABLE_WIDTH = round(PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN, 2)  # 523.28 pt
RIGHT_BOUND = round(PAGE_WIDTH - RIGHT_MARGIN, 2)  # 559.28 pt


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass ReportLab canvas for running headers, footers, and dynamic page counts
    ('Halaman X dari Y'). Ensures visual consistency across multi-page documents on A4 paper.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int) -> None:
        self.saveState()

        # Top Running Header (x: 36 to 559.28 pt, above content boundary y = 787.89 pt)
        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(colors.HexColor("#475569"))
        self.drawString(LEFT_MARGIN, 802, "KAWAL SIBER — SISTEM PERTAHANAN SIBER TERITORIAL [DOKUMEN OPERASIONAL]")

        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(LEFT_MARGIN, 794, RIGHT_BOUND, 794)

        # Bottom Running Footer (x: 36 to 559.28 pt, below content boundary y = 54 pt)
        self.line(LEFT_MARGIN, 44, RIGHT_BOUND, 44)
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(LEFT_MARGIN, 32, "Integritas Forensik SHA-256 | KAWAL SIBER Reporting Engine v6.1.0")
        page_str = f"Halaman {self._pageNumber} dari {page_count}"
        self.drawRightString(RIGHT_BOUND, 32, page_str)

        self.restoreState()


def export_to_pdf(data: Dict[str, Any], output_path: Path) -> Path:
    """
    Generate an executive PDF document using ReportLab with NumberedCanvas on A4.
    Includes cover header, metadata grid, metrics, narrative, artifact tables, and audit footer.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # A4: 595.28 x 841.89 pt. Printable width = 595.28 - 72 = 523.28 pt.
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    brand_style = ParagraphStyle(
        "BrandHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#22C55E"),
        alignment=0,
    )
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#475569"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E293B"),
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
        wordWrap="CJK",
    )
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )
    alert_box_style = ParagraphStyle(
        "AlertBox",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=12,
        textColor=colors.HexColor("#991B1B"),
    )

    story: List[Any] = []

    # 1. Header Banner
    story.append(Paragraph("KAWAL SIBER — SISTEM PERTAHANAN SIBER TERITORIAL", brand_style))
    story.append(Spacer(1, 4))
    report_title = data.get("title", "Laporan Keamanan Siber")
    story.append(Paragraph(report_title, title_style))
    story.append(Spacer(1, 4))

    # 2. Metadata Grid (colWidths: 261.64 + 261.64 = 523.28 pt)
    report_id = data.get("report_id", "N/A")
    report_type = data.get("report_type", "SECURITY")
    gen_at = data.get("generated_at", "")
    gen_by = data.get("generated_by", "KAWAL SIBER Operations")

    meta_data = [
        [
            Paragraph(f"<b>Report ID:</b> {report_id}", meta_style),
            Paragraph(f"<b>Tipe Laporan:</b> {report_type}", meta_style),
        ],
        [
            Paragraph(f"<b>Waktu Pembuatan:</b> {gen_at}", meta_style),
            Paragraph(f"<b>Otoritas Penerbit:</b> {gen_by}", meta_style),
        ],
    ]
    half_w = round(PRINTABLE_WIDTH / 2, 2)
    meta_table = Table(meta_data, colWidths=[half_w, half_w])
    meta_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 3),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Empty Database / Insufficient Telemetry Visual Warning Banner
    posture = data.get("posture") or data.get("metrics", {}).get("postur_keamanan")
    if posture == "NOT ASSESSED":
        reason = data.get("posture_reason") or "INSUFFICIENT SECURITY TELEMETRY"
        warning_data = [[
            Paragraph(
                f"<b>PERINGATAN OPERASIONAL: STATUS POSTUR [{posture}] — {reason}</b><br/>"
                "Basis data tidak memiliki aset aktif, event jaringan, atau asesmen selesai untuk dianalisis. "
                "<i>Ketiadaan temuan ancaman tidak sama dengan jaminan sistem aman (angka nol bukan bukti keamanan).</i>",
                alert_box_style,
            )
        ]]
        warning_table = Table(warning_data, colWidths=[PRINTABLE_WIDTH])
        warning_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#EF4444")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(warning_table)
        story.append(Spacer(1, 10))

    # 3. Executive Summary
    exec_summary = data.get("executive_summary")
    if exec_summary:
        story.append(Paragraph("1. Ringkasan Eksekutif", section_heading))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#22C55E"), spaceAfter=6))
        story.append(Paragraph(redact_sensitive_data(exec_summary), body_style))
        story.append(Spacer(1, 10))

    # 4. Metrics Table (colWidths: 323.28 + 200.0 = 523.28 pt)
    metrics: Dict[str, Any] = data.get("metrics", {})
    if metrics:
        story.append(Paragraph("2. Indikator & Metrik Utama", section_heading))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#22C55E"), spaceAfter=6))

        metric_rows = [["Metrik Pengukuran", "Nilai Snapshot"]]
        for k, v in metrics.items():
            metric_rows.append([k.replace("_", " ").title(), str(v)])

        m_col1 = round(PRINTABLE_WIDTH - 200.0, 2)
        m_table = Table(
            [[Paragraph(cell, table_header_style if i == 0 else table_cell_style) for cell in row] for i, row in enumerate(metric_rows)],
            colWidths=[m_col1, 200.0],
        )
        m_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("PADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ])
        )
        story.append(m_table)
        story.append(Spacer(1, 10))

    # 5. AI Narrative Section (if present)
    ai_narrative = data.get("ai_narrative")
    if ai_narrative:
        story.append(Paragraph("3. Analisis Inteligensi Siber", section_heading))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#22C55E"), spaceAfter=6))
        story.append(Paragraph(
            "<i>[CATATAN SISTEM: Bagian ini disusun dengan asistensi AI Triage. Seluruh tindakan memerlukan persetujuan operator manusia.]</i>",
            meta_style,
        ))
        story.append(Spacer(1, 4))
        story.append(Paragraph(redact_sensitive_data(ai_narrative), body_style))
        story.append(Spacer(1, 10))

    # 6. Detail Items Table (Findings / Incidents) - (colWidths: 523.28 pt total)
    items = data.get("items") or data.get("incidents") or data.get("findings")
    if items and isinstance(items, list) and len(items) > 0:
        story.append(Paragraph("4. Detail Telemetri & Temuan", section_heading))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#22C55E"), spaceAfter=6))

        # Select max 4 columns to fit page nicely
        all_cols = list(items[0].keys())
        selected_cols = all_cols[:4]
        col_width = round(PRINTABLE_WIDTH / len(selected_cols), 2)

        table_data = [
            [Paragraph(col.replace("_", " ").title(), table_header_style) for col in selected_cols]
        ]
        for item in items[:25]:  # limit to 25 items per page view
            row = [
                Paragraph(redact_sensitive_data(str(item.get(c, "")))[:100], table_cell_style)
                for c in selected_cols
            ]
            table_data.append(row)

        item_table = Table(table_data, colWidths=[col_width] * len(selected_cols))
        item_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("PADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(item_table)
        story.append(Spacer(1, 15))

    # 7. Audit & Reproducibility Footer
    repro = data.get("reproducibility", {})
    comp_versions = repro.get("component_versions", {})
    versions_text = ", ".join(f"{k}: {v}" for k, v in comp_versions.items() if v != "NOT_AVAILABLE") or "Localhost Dev Environment"

    story.append(KeepTogether([
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceAfter=6),
        Paragraph(
            f"<b>Komponen Versi:</b> {versions_text}<br/>"
            "<b>Integritas Forensik:</b> Checksum SHA-256 dihitung secara independen pada berkas final yang diekspor "
            "dan dicatat dalam database (mencegah paradoks self-referential hashing).",
            meta_style,
        ),
        Spacer(1, 3),
        Paragraph(
            "Dokumen ini dihasilkan secara otomatis oleh KAWAL SIBER Platform — Kartika Cyber Hackathon 2026.",
            meta_style,
        ),
    ]))

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
