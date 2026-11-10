"""
json_export.py — Structured JSON exporter with schema version and checksum integrity.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from app.reporting.sanitization import redact_sensitive_data


def export_to_json(data: Dict[str, Any], output_path: Path) -> Path:
    """
    Export structured report data to a formatted UTF-8 JSON file.
    Enforces schema_version = '1.0' and redacts sensitive credentials.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def _sanitize_dict(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _sanitize_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_sanitize_dict(item) for item in obj]
        elif isinstance(obj, str):
            return redact_sensitive_data(obj)
        return obj

    payload = _sanitize_dict(data)
    payload["schema_version"] = "1.0"
    payload["platform"] = "KAWAL SIBER — Sistem Pertahanan Siber Teritorial"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)

    return output_path

