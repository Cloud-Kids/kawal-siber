"""
test_nmap_scanner.py — Unit tests for Nmap command construction and subprocess execution.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.nmap_scanner import (
    NmapExecutionError,
    build_nmap_command,
    get_nmap_version,
    run_nmap_scan,
)


def test_build_nmap_command_fixed_profile():
    cmd = build_nmap_command("192.168.1.50", 443, nmap_bin="/usr/bin/nmap")
    expected = [
        "/usr/bin/nmap",
        "-sT",
        "-sV",
        "--version-light",
        "-n",
        "-Pn",
        "-p443",
        "--host-timeout",
        "30s",
        "--max-retries",
        "1",
        "--reason",
        "-oX",
        "-",
        "192.168.1.50",
    ]
    assert cmd == expected


def test_build_nmap_command_invalid_inputs_rejected():
    with pytest.raises(ValueError, match="Invalid port"):
        build_nmap_command("10.0.0.1", 0)

    with pytest.raises(ValueError, match="Invalid port"):
        build_nmap_command("10.0.0.1", 65536)

    with pytest.raises(ValueError, match="Invalid resolved IP"):
        build_nmap_command("not-an-ip", 80)


@pytest.mark.asyncio
async def test_run_nmap_scan_success():
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"<nmaprun>output</nmaprun>", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await run_nmap_scan("127.0.0.1", 80)
        assert "<nmaprun>output</nmaprun>" in result


@pytest.mark.asyncio
async def test_run_nmap_scan_timeout_handled():
    mock_proc = AsyncMock()
    mock_proc.communicate.side_effect = asyncio.TimeoutError()
    mock_proc.kill = MagicMock()
    mock_proc.wait = AsyncMock()

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(TimeoutError):
            await run_nmap_scan("127.0.0.1", 80, timeout_seconds=1)
        mock_proc.kill.assert_called_once()


@pytest.mark.asyncio
async def test_run_nmap_scan_nonzero_exit_code():
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"Failed to resolve target")
    mock_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(NmapExecutionError, match="error exit code 1"):
            await run_nmap_scan("127.0.0.1", 80)


@pytest.mark.asyncio
async def test_get_nmap_version():
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (
        b"Nmap version 7.94 ( https://nmap.org )\nPlatform: x86_64\n",
        b"",
    )
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        ver = await get_nmap_version()
        assert ver.startswith("Nmap version 7.94")
