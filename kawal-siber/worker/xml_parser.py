"""
xml_parser.py — Safe XML parser for Nmap scan outputs.
Extracts structured host and port discovery findings using xml.etree.ElementTree.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NmapXMLParseError(Exception):
    """Raised when Nmap XML output is malformed or invalid."""
    pass


def parse_nmap_xml(xml_content: str, max_bytes: int = 1024 * 1024) -> Dict[str, Any]:
    """
    Parse Nmap XML output string into structured dictionary findings.

    Args:
        xml_content: Raw XML output from Nmap.
        max_bytes: Maximum allowed byte size of XML input.

    Returns:
        Dict with keys:
          - target_ip: str | None
          - host_status: str (e.g. 'up', 'down', 'unknown')
          - duration_ms: int | None
          - scanner_version: str | None
          - ports: List[Dict[str, Any]] each containing:
              - protocol: str ('tcp')
              - port: int
              - state: str ('open', 'closed', 'filtered')
              - service_name: str | None
              - product: str | None
              - version: str | None
              - extra_info: str | None
              - reason: str | None
    """
    if not xml_content or not xml_content.strip():
        raise NmapXMLParseError("Empty Nmap XML output.")

    # Size threshold validation
    raw_bytes = xml_content.encode("utf-8")
    if len(raw_bytes) > max_bytes:
        raise NmapXMLParseError(
            f"Nmap XML payload exceeds maximum limit of {max_bytes} bytes "
            f"(received {len(raw_bytes)} bytes)."
        )

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise NmapXMLParseError(f"Malformed XML from Nmap: {exc}") from exc

    if root.tag != "nmaprun":
        raise NmapXMLParseError(f"Unexpected XML root element: <{root.tag}>, expected <nmaprun>.")

    scanner_version = root.get("version")

    # Extract scan duration from <runstats><finished elapsed="..."/>
    duration_ms: Optional[int] = None
    finished_elem = root.find(".//runstats/finished")
    if finished_elem is not None:
        elapsed_str = finished_elem.get("elapsed")
        if elapsed_str:
            try:
                duration_ms = int(float(elapsed_str) * 1000)
            except ValueError:
                pass

    # Extract host information
    host_elem = root.find("host")
    if host_elem is None:
        return {
            "target_ip": None,
            "host_status": "unknown",
            "duration_ms": duration_ms,
            "scanner_version": scanner_version,
            "ports": [],
        }

    # Target IP
    target_ip: Optional[str] = None
    addr_elem = host_elem.find("address")
    if addr_elem is not None:
        target_ip = addr_elem.get("addr")

    # Host status
    host_status = "unknown"
    status_elem = host_elem.find("status")
    if status_elem is not None:
        host_status = status_elem.get("state", "unknown")

    # Ports & Services
    port_findings: List[Dict[str, Any]] = []
    ports_elem = host_elem.find("ports")
    if ports_elem is not None:
        for p in ports_elem.findall("port"):
            protocol = p.get("protocol", "tcp")
            port_id_str = p.get("portid")
            if not port_id_str:
                continue
            try:
                port_id = int(port_id_str)
            except ValueError:
                continue

            state = "unknown"
            reason: Optional[str] = None
            state_elem = p.find("state")
            if state_elem is not None:
                state = state_elem.get("state", "unknown")
                reason = state_elem.get("reason")

            service_name: Optional[str] = None
            product: Optional[str] = None
            version: Optional[str] = None
            extra_info: Optional[str] = None

            service_elem = p.find("service")
            if service_elem is not None:
                service_name = service_elem.get("name")
                product = service_elem.get("product")
                version = service_elem.get("version")
                extra_info = service_elem.get("extrainfo")

            port_findings.append(
                {
                    "protocol": protocol,
                    "port": port_id,
                    "state": state,
                    "reason": reason,
                    "service_name": service_name,
                    "product": product,
                    "version": version,
                    "extra_info": extra_info,
                }
            )

    return {
        "target_ip": target_ip,
        "host_status": host_status,
        "duration_ms": duration_ms,
        "scanner_version": scanner_version,
        "ports": port_findings,
    }

