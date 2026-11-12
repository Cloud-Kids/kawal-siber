"""
paths.py — Centralized runtime storage path resolution for KAWAL SIBER.

Replaces fragile ``Path(__file__).parent.parent...`` traversal with a single
configurable storage root:

- ``KAWAL_STORAGE_ROOT``  — root directory holding pcaps/, reports/, suricata/
- ``KAWAL_WORKSPACE_ROOT``— project/workspace root (used for tool locations)
- ``REPORTS_STORAGE_PATH``— explicit override for the reports directory
- ``DEEP_EYE_ROOT``       — explicit override for the Deep Eye submodule root

Defaults preserve local development layout: ``<repo>/storage``.
In containers, set ``KAWAL_STORAGE_ROOT=/data`` (or the mounted storage path).
"""
from __future__ import annotations

import os
from pathlib import Path


def _default_workspace_root() -> Path:
    """Repository root derived from this file's location (backend/app/paths.py)."""
    return Path(__file__).resolve().parents[2]


WORKSPACE_ROOT = Path(
    os.environ.get("KAWAL_WORKSPACE_ROOT", str(_default_workspace_root()))
).expanduser().resolve()

STORAGE_ROOT = Path(
    os.environ.get("KAWAL_STORAGE_ROOT", str(WORKSPACE_ROOT / "storage"))
).expanduser().resolve()

REPORTS_DIR = Path(
    os.environ.get("REPORTS_STORAGE_PATH", str(STORAGE_ROOT / "reports"))
).expanduser().resolve()

PCAP_DIR = Path(
    os.environ.get("PCAP_STORAGE_PATH", str(STORAGE_ROOT / "pcaps"))
).expanduser().resolve()

SURICATA_DIR = Path(
    os.environ.get("SURICATA_STORAGE_PATH", str(STORAGE_ROOT / "suricata"))
).expanduser().resolve()

SURICATA_RULES_DIR = SURICATA_DIR / "rules"
SURICATA_LOGS_DIR = SURICATA_DIR / "logs"
SURICATA_CONFIG_PATH = SURICATA_DIR / "suricata.yaml"


def ensure_storage_dirs() -> None:
    """Create the standard storage subdirectories if missing (idempotent)."""
    for d in (STORAGE_ROOT, REPORTS_DIR, PCAP_DIR, SURICATA_DIR,
              SURICATA_RULES_DIR, SURICATA_LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
