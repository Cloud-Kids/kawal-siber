"""
tools_agent.py — Authenticated Security Tool Execution Agent for KAWAL SIBER.
Runs inside ks-tools-01 (tools-agent-a / tools-agent-b).
Provides authenticated REST endpoints for Nmap scans, Suricata telemetry, and PCAP analysis
with strict in-container CIDR scope enforcement and concurrency limits.
"""
import asyncio
import ipaddress
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Header, Security, status
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (tools-agent) %(message)s")
logger = logging.getLogger("tools-agent")

AGENT_KEY = os.environ.get("TOOLS_AGENT_KEY", "KawalSiberToolsAgentAuthToken2026!")
MAX_CONCURRENT_SCANS = int(os.environ.get("MAX_CONCURRENT_SCANS", "4"))
SCAN_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_SCANS)

app = FastAPI(title="KAWAL SIBER Security Tools Agent", version="1.0.0")


def verify_agent_token(x_agent_key: Optional[str] = Header(None, alias="X-Agent-Key")) -> str:
    if not x_agent_key or x_agent_key != AGENT_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Agent-Key authentication header.",
        )
    return x_agent_key


class ScanRequest(BaseModel):
    target: str = Field(..., description="Target IPv4 or hostname")
    allowed_cidr: str = Field(..., description="Authorized CIDR boundary")
    ports: str = Field("1-1000", description="Port range (e.g. 1-1000 or 80,443)")
    arguments: Optional[str] = Field(None, description="Safe nmap flags (-sS -sV)")
    timeout_seconds: int = Field(60, ge=5, le=300)


class ScanResponse(BaseModel):
    status: str
    target: str
    resolved_ip: Optional[str] = None
    output_xml: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


def validate_scope(target: str, allowed_cidr: str) -> str:
    """Enforce strict IP/CIDR scope boundaries before executing any binary."""
    try:
        network = ipaddress.ip_network(allowed_cidr, strict=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid allowed_cidr: {e}")

    try:
        ip = ipaddress.ip_address(target)
    except ValueError:
        # If target is a hostname, resolve it to IPv4
        import socket
        try:
            resolved = socket.gethostbyname(target)
            ip = ipaddress.ip_address(resolved)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot resolve hostname '{target}': {e}")

    # Forbid dangerous ranges: Cloud metadata (169.254.169.254), loopback, multicast
    if ip.is_loopback:
        raise HTTPException(status_code=403, detail="Scanning loopback interface (127.0.0.0/8) is strictly prohibited.")
    if ip.is_link_local:
        raise HTTPException(status_code=403, detail="Scanning link-local / metadata addresses (169.254.0.0/16) is strictly prohibited.")
    if ip.is_multicast:
        raise HTTPException(status_code=403, detail="Scanning multicast addresses is strictly prohibited.")

    if ip not in network:
        raise HTTPException(
            status_code=403,
            detail=f"Target IP {ip} is OUT OF BOUNDS for authorized scope {allowed_cidr}."
        )

    return str(ip)


@app.get("/health")
def health() -> Dict[str, Any]:
    nmap_path = shutil.which("nmap")
    return {
        "status": "healthy",
        "container_id": os.environ.get("HOSTNAME", "unknown"),
        "nmap_available": nmap_path is not None,
        "max_concurrent_scans": MAX_CONCURRENT_SCANS,
    }


@app.post("/v1/scan/nmap", response_model=ScanResponse, dependencies=[Depends(verify_agent_token)])
async def execute_nmap_scan(req: ScanRequest) -> ScanResponse:
    # 1. Enforce strict in-container scope validation
    resolved_ip = validate_scope(req.target, req.allowed_cidr)

    # 2. Acquire concurrency semaphore to prevent resource exhaustion
    try:
        async with asyncio.timeout(10):
            await SCAN_SEMAPHORE.acquire()
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tool agent capacity saturated: max concurrent scans reached.",
        )

    temp_dir = tempfile.mkdtemp(prefix="ks_scan_")
    xml_path = os.path.join(temp_dir, "scan.xml")
    start_time = asyncio.get_event_loop().time()

    try:
        cmd = [
            "nmap",
            "-sT",
            "-p", req.ports,
            "-oX", xml_path,
            "--open",
            "-n",
            "-T4",
            resolved_ip,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=req.timeout_seconds)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ScanResponse(
                status="FAILED",
                target=req.target,
                resolved_ip=resolved_ip,
                error=f"Scan timed out after {req.timeout_seconds} seconds.",
            )

        duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

        if os.path.exists(xml_path):
            with open(xml_path, "r", encoding="utf-8") as f:
                xml_content = f.read()
            return ScanResponse(
                status="COMPLETED",
                target=req.target,
                resolved_ip=resolved_ip,
                output_xml=xml_content,
                duration_ms=duration_ms,
            )
        else:
            return ScanResponse(
                status="FAILED",
                target=req.target,
                resolved_ip=resolved_ip,
                error=stderr.decode("utf-8", errors="replace"),
                duration_ms=duration_ms,
            )

    finally:
        SCAN_SEMAPHORE.release()
        shutil.rmtree(temp_dir, ignore_errors=True)

