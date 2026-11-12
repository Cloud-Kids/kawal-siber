"""
suricata_engine.py — Suricata IDS Engine Management and Offline PCAP Processing.
Handles executable path discovery, configuration verification, strict argument-array
subprocess execution, and structured EVE JSON output retrieval on Windows host.
"""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.paths import (
    PCAP_DIR as _ALLOWED_PCAP_DIR,
    SURICATA_DIR as _SURICATA_CONF_DIR,
    SURICATA_LOGS_DIR as _SURICATA_LOGS_DIR,
)

logger = logging.getLogger(__name__)

# Standard allowed extensions for network packet captures
ALLOWED_PCAP_EXTENSIONS = {".pcap", ".pcapng", ".cap"}

# Maximum allowed PCAP file size (50 MB default to prevent resource exhaustion)
MAX_PCAP_FILE_SIZE = 50 * 1024 * 1024

# Default paths
_DEFAULT_WIN_SURICATA = Path(r"C:\Program Files\Suricata\suricata.exe")


class SuricataEngineError(Exception):
    """Base exception for Suricata engine operations."""
    pass


class SuricataNotFoundError(SuricataEngineError):
    """Raised when suricata.exe cannot be located."""
    pass


class PcapValidationError(SuricataEngineError):
    """Raised when a PCAP file violates security or format policies."""
    pass


def resolve_suricata_executable(custom_path: Optional[str] = None) -> Path:
    """
    Locate the Suricata executable on Windows host.
    Precedence:
      1. Explicit parameter or env var SURICATA_PATH
      2. PATH lookup via shutil.which('suricata')
      3. Standard Program Files location
    """
    env_path = custom_path or os.environ.get("SURICATA_PATH")
    if env_path:
        p = Path(env_path).resolve()
        if p.is_file():
            return p

    which_path = shutil.which("suricata.exe") or shutil.which("suricata")
    if which_path:
        return Path(which_path).resolve()

    if _DEFAULT_WIN_SURICATA.is_file():
        return _DEFAULT_WIN_SURICATA

    raise SuricataNotFoundError(
        "Suricata executable not found. Ensure Suricata is installed in "
        f"{_DEFAULT_WIN_SURICATA} or configured via SURICATA_PATH environment variable."
    )


def get_suricata_version(executable_path: Optional[Path] = None) -> str:
    """Execute suricata -V with strict argument array and extract version string."""
    exe = executable_path or resolve_suricata_executable()
    try:
        proc = subprocess.run(
            [str(exe), "-V"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        output = proc.stdout.strip() or proc.stderr.strip()
        for line in output.splitlines():
            if "Suricata version" in line:
                return line.replace("This is", "").replace("Info: win32-service: Running as service: no", "").strip()
        return output.splitlines()[0] if output else "Suricata (version unknown)"
    except Exception as exc:
        logger.error("Failed to query Suricata version: %s", exc)
        return "Suricata (unavailable)"


def get_default_config_path() -> Path:
    """Return path to dedicated KAWAL SIBER suricata.yaml configuration."""
    conf = _SURICATA_CONF_DIR / "suricata.yaml"
    if conf.is_file():
        return conf
    # Fallback to system installation config
    sys_conf = Path(r"C:\Program Files\Suricata\suricata.yaml")
    if sys_conf.is_file():
        return sys_conf
    raise SuricataEngineError(f"No valid suricata.yaml found at {conf} or {sys_conf}")


def validate_pcap_file(filepath: Path, allowed_dir: Optional[Path] = None) -> Tuple[str, int]:
    """
    Validate PCAP file for:
      - Existence
      - Path traversal prevention (must reside within authorized storage directory)
      - File extension whitelist (.pcap, .pcapng, .cap)
      - Maximum file size
      - Non-empty content
    Returns:
      (sha256_hash, file_size_bytes)
    """
    target_dir = (allowed_dir or _ALLOWED_PCAP_DIR).resolve()
    resolved_file = filepath.resolve()

    # Path traversal check
    try:
        resolved_file.relative_to(target_dir)
    except ValueError:
        raise PcapValidationError(
            f"Access denied: PCAP file {resolved_file.name} is outside authorized storage directory {target_dir}."
        )

    if not resolved_file.is_file():
        raise PcapValidationError(f"PCAP file does not exist: {resolved_file}")

    ext = resolved_file.suffix.lower()
    if ext not in ALLOWED_PCAP_EXTENSIONS:
        raise PcapValidationError(
            f"Unsupported file extension '{ext}'. Only {sorted(ALLOWED_PCAP_EXTENSIONS)} are allowed."
        )

    file_size = resolved_file.stat().st_size
    if file_size == 0:
        raise PcapValidationError("PCAP file is empty (0 bytes).")
    if file_size > MAX_PCAP_FILE_SIZE:
        raise PcapValidationError(
            f"PCAP file size ({file_size} bytes) exceeds maximum limit of {MAX_PCAP_FILE_SIZE} bytes."
        )

    # Compute SHA256 hash for audit and deduplication
    hasher = hashlib.sha256()
    with open(resolved_file, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    file_hash = hasher.hexdigest()

    return file_hash, file_size


def execute_suricata_pcap(
    pcap_path: Path,
    output_dir: Path,
    config_path: Optional[Path] = None,
    executable_path: Optional[Path] = None,
    timeout_seconds: int = 120,
) -> Path:
    """
    Execute Suricata in offline single-run PCAP processing mode.
    Arguments are passed as a strict array (NO shell=True).
    Checksum verification is disabled (-k none) to ensure lab/synthetic packets are inspected.

    Returns:
      Path to generated eve.json file.
    """
    exe = executable_path or resolve_suricata_executable()
    conf = config_path or get_default_config_path()

    output_dir.mkdir(parents=True, exist_ok=True)
    eve_file = output_dir / "eve.json"

    # Clean existing eve.json in this directory if any
    if eve_file.exists():
        eve_file.unlink()

    # Strict argument list
    cmd = [
        str(exe),
        "-c",
        str(conf),
        "-r",
        str(pcap_path.resolve()),
        "-l",
        str(output_dir.resolve()),
        "-k",
        "none",
    ]

    logger.info("Executing Suricata offline PCAP: %s", " ".join(cmd))

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("Suricata execution timed out after %ds on %s", timeout_seconds, pcap_path.name)
        raise SuricataEngineError(
            f"Suricata timed out after {timeout_seconds} seconds processing {pcap_path.name}."
        ) from exc
    except Exception as exc:
        logger.error("Suricata subprocess execution failed: %s", exc)
        raise SuricataEngineError(f"Failed to launch Suricata: {exc}") from exc

    if not eve_file.is_file():
        logger.warning(
            "Suricata completed with return code %d but eve.json was not created. Stderr: %s",
            proc.returncode,
            proc.stderr[:500],
        )
        raise SuricataEngineError(
            f"Suricata finished without generating EVE JSON output (return code {proc.returncode})."
        )

    logger.info("Suricata analysis succeeded. Output: %s (%d bytes)", eve_file, eve_file.stat().st_size)
    return eve_file

