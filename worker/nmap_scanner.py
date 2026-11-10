"""
nmap_scanner.py — Executes authorized Nmap scans using strict subprocess safety.
Implements the fixed scanning policy profile without shell invocation.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
from typing import Optional, Tuple

from worker.config import config

logger = logging.getLogger(__name__)


class NmapExecutionError(Exception):
    """Raised when the Nmap process encounters an error or non-zero exit."""
    pass


def build_nmap_command(resolved_ip: str, port: int, nmap_bin: str = "nmap") -> list[str]:
    """
    Construct the fixed, unmodifiable Nmap command argument list.
    No user options, scripts, or extra parameters can be injected.
    """
    # Strict validation of IP
    try:
        ipaddress.ip_address(resolved_ip.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid resolved IP for scan: {resolved_ip!r}") from exc

    # Strict validation of port
    if not (1 <= port <= 65535):
        raise ValueError(f"Invalid port: {port}. Must be between 1 and 65535.")

    # Fixed scanning profile as mandated by Phase 2 Engineering Specification:
    # - TCP connect scan (-sT)
    # - Service detection (-sV)
    # - Lightweight version detection (--version-light)
    # - Disable DNS lookup (-n)
    # - Skip host discovery (-Pn)
    # - Single registered port (-p)
    # - Limited host timeout
    # - Limited retries
    # - Reason reporting (--reason)
    # - XML stdout output (-oX -)
    return [
        nmap_bin,
        "-sT",
        "-sV",
        "--version-light",
        "-n",
        "-Pn",
        f"-p{port}",
        "--host-timeout",
        "30s",
        "--max-retries",
        "1",
        "--reason",
        "-oX",
        "-",
        resolved_ip.strip(),
    ]


async def run_nmap_scan(
    resolved_ip: str,
    port: int,
    timeout_seconds: Optional[int] = None,
    nmap_bin: Optional[str] = None,
    max_bytes: Optional[int] = None,
) -> str:
    """
    Execute Nmap asynchronously without shell=True.
    Limits execution time, stdout size, and captures exit code.

    Returns:
        Raw XML output string from Nmap.
    """
    timeout = timeout_seconds or config.NMAP_TIMEOUT_SECONDS
    bin_path = nmap_bin or config.NMAP_PATH
    max_xml_len = max_bytes or config.MAX_XML_BYTES

    cmd = build_nmap_command(resolved_ip, port, bin_path)
    logger.info("Executing Nmap scan: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_data, stderr_data = await asyncio.wait_for(
            proc.communicate(),
            timeout=float(timeout),
        )
    except asyncio.TimeoutError:
        logger.warning("Nmap process timed out after %ds; terminating PID=%s", timeout, proc.pid)
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass
        raise TimeoutError(f"Nmap scan timed out after {timeout} seconds.")

    if len(stdout_data) > max_xml_len:
        raise NmapExecutionError(
            f"Nmap output exceeded maximum permitted byte limit ({len(stdout_data)} > {max_xml_len})."
        )

    # Some versions of Nmap exit 0 even with partial warnings, but non-zero means failure
    if proc.returncode != 0:
        err_msg = stderr_data.decode("utf-8", errors="replace").strip()
        logger.error("Nmap exited with code %d: %s", proc.returncode, err_msg)
        raise NmapExecutionError(
            f"Nmap terminated with error exit code {proc.returncode}: {err_msg[:200]}"
        )

    return stdout_data.decode("utf-8", errors="replace")


async def get_nmap_version(nmap_bin: Optional[str] = None) -> str:
    """Check binary availability and retrieve version string."""
    bin_path = nmap_bin or config.NMAP_PATH
    try:
        proc = await asyncio.create_subprocess_exec(
            bin_path,
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        first_line = stdout.decode("utf-8", errors="replace").splitlines()[0]
        return first_line.strip()
    except Exception as exc:
        raise RuntimeError(f"Nmap binary not found or inaccessible at {bin_path!r}: {exc}") from exc

