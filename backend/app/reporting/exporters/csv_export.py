"""
csv_export.py — Table-oriented CSV exporter with formula injection protection.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Dict, List

from app.reporting.sanitization import redact_sensitive_data, sanitize_csv_cell


def export_to_csv(data: Dict[str, Any], output_path: Path) -> Path:
    """
    Export structured report data to a UTF-8 encoded CSV file.
    Applies formula injection protection to all cells and redacts sensitive credentials.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Find primary table in report data
    table_rows: List[Dict[str, Any]] = []
    if "items" in data and isinstance(data["items"], list):
        table_rows = data["items"]
    elif "incidents" in data and isinstance(data["incidents"], list):
        table_rows = data["incidents"]
    elif "findings" in data and isinstance(data["findings"], list):
        table_rows = data["findings"]
    elif "assets" in data and isinstance(data["assets"], list):
        table_rows = data["assets"]
    else:
        # Fall back to flattening top-level key/value pairs
        table_rows = [{"Property": k, "Value": str(v)} for k, v in data.items() if not isinstance(v, (dict, list))]

    fieldnames = list(table_rows[0].keys()) if table_rows else ["Key", "Value"]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        # Header metadata block
        writer.writerow(["# KAWAL SIBER AUDIT REPORT"])
        writer.writerow(["# Report ID", sanitize_csv_cell(data.get("report_id", ""))])
        writer.writerow(["# Title", sanitize_csv_cell(data.get("title", ""))])
        writer.writerow(["# Generated At", sanitize_csv_cell(data.get("generated_at", ""))])
        writer.writerow([])  # blank line separator

        # Table Header
        writer.writerow(fieldnames)

        # Table Data
        for row in table_rows:
            row_values = [
                sanitize_csv_cell(redact_sensitive_data(row.get(col, "")))
                for col in fieldnames
            ]
            writer.writerow(row_values)

    return output_path

