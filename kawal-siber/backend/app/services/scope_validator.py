"""
backend/app/services/scope_validator.py — Scope validation service for API endpoints.
"""
from __future__ import annotations

import ipaddress
import logging
import socket
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger(__name__)


class ScopeValidationError(Exception):
    pass


class ScopeDisabledError(ScopeValidationError):
    pass


class ScopeExpiredError(ScopeValidationError):
    pass


class OutOfScopeError(ScopeValidationError):
    pass


class DNSResolutionError(ScopeValidationError):
    pass


def validate_scope_active(enabled: bool, expires_at: datetime) -> None:
    if not enabled:
        raise ScopeDisabledError("Scan scope is currently disabled by administrator.")

    now = datetime.now(timezone.utc)
    exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    if exp <= now:
        raise ScopeExpiredError(
            f"Scan authorization expired at {exp.isoformat()} (current UTC: {now.isoformat()})."
        )


def check_ip_in_cidr(ip_str: str, cidr_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        network = ipaddress.ip_network(cidr_str.strip(), strict=False)
        return ip in network
    except ValueError as exc:
        raise ScopeValidationError(f"Invalid IP or CIDR: {exc}") from exc


def resolve_hostname_all_ips(hostname: str) -> List[str]:
    cleaned = hostname.strip().rstrip(".")
    try:
        addrinfo = socket.getaddrinfo(
            cleaned,
            None,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise DNSResolutionError(f"Failed to resolve hostname {hostname!r}: {exc}") from exc

    ips: List[str] = []
    for family, _, _, _, sockaddr in addrinfo:
        ip = sockaddr[0]
        if ip not in ips:
            ips.append(ip)

    if not ips:
        raise DNSResolutionError(f"No IP addresses returned for hostname {hostname!r}")

    return ips


def validate_target_against_scope(
    target: str,
    cidr: str,
    enabled: bool,
    expires_at: datetime,
) -> str:
    validate_scope_active(enabled, expires_at)

    target_clean = target.strip()

    try:
        ip_obj = ipaddress.ip_address(target_clean)
        network = ipaddress.ip_network(cidr.strip(), strict=False)
        if ip_obj not in network:
            raise OutOfScopeError(
                f"Target IP {target_clean} is outside authorized scope {cidr}."
            )
        return str(ip_obj)
    except ValueError:
        pass

    resolved_ips = resolve_hostname_all_ips(target_clean)
    network = ipaddress.ip_network(cidr.strip(), strict=False)

    for resolved_ip in resolved_ips:
        ip_obj = ipaddress.ip_address(resolved_ip)
        if ip_obj not in network:
            raise OutOfScopeError(
                f"Target hostname {target_clean!r} resolves to {resolved_ip}, "
                f"which is outside authorized scope {cidr}."
            )

    return resolved_ips[0]

