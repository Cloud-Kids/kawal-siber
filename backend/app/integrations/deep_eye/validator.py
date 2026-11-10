"""
Security validator for Web Security Assessment & Deep Eye Integration.
Enforces strict localhost allowlist, port checks, path allowlist, and SSRF/DNS rebinding prevention.
"""
from __future__ import annotations

import fnmatch
import ipaddress
import re
import socket
from typing import List, Optional, Set, Tuple
from urllib.parse import urlparse

from app.integrations.deep_eye.config import DEFAULT_ALLOWED_HOSTS, DEFAULT_ALLOWED_PORTS


class WebValidationError(Exception):
    """Base exception for web target validation failures."""
    pass


class InvalidTargetURLError(WebValidationError):
    """Raised when the URL format or protocol is invalid."""
    pass


class TargetOutOfScopeError(WebValidationError):
    """Raised when the target host or IP is outside authorized scope."""
    pass


class PathNotAllowedError(WebValidationError):
    """Raised when requested target path violates allowed paths policy."""
    pass


def parse_and_validate_target_url(
    target_url: str,
    extra_allowed_hosts: Optional[Set[str]] = None,
) -> Tuple[str, str, int, str]:
    """
    Parses and strictly validates target URL.
    Returns: (protocol, hostname, port, normalized_url)
    """
    if not target_url or not isinstance(target_url, str):
        raise InvalidTargetURLError("Target URL must be a non-empty string.")

    target_url = target_url.strip()

    # Reject dangerous protocols and formats
    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        raise InvalidTargetURLError("Only HTTP and HTTPS protocols are permitted.")

    try:
        parsed = urlparse(target_url)
    except Exception as exc:
        raise InvalidTargetURLError(f"Malformed URL: {exc}") from exc

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise InvalidTargetURLError(f"Unsupported scheme '{scheme}'. Only http and https are allowed.")

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise InvalidTargetURLError("Target URL is missing hostname.")

    # Determine port
    try:
        if parsed.port:
            port = parsed.port
        else:
            port = 443 if scheme == "https" else 80
    except ValueError as exc:
        raise InvalidTargetURLError(f"Invalid port: {exc}") from exc

    if port < 1 or port > 65535:
        raise InvalidTargetURLError(f"Port {port} is out of valid range (1-65535).")

    # Scope / Localhost allowlist check
    allowed_hosts = set(DEFAULT_ALLOWED_HOSTS)
    if extra_allowed_hosts:
        allowed_hosts.update(h.lower().strip() for h in extra_allowed_hosts)

    # Validate hostname / IP
    is_allowed = False
    if hostname in allowed_hosts:
        is_allowed = True
    else:
        # Check if hostname is an IP address
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_loopback:
                is_allowed = True
            elif extra_allowed_hosts and str(ip) in extra_allowed_hosts:
                is_allowed = True
        except ValueError:
            # Hostname might resolve to loopback or authorized IP
            try:
                resolved_ips = resolve_hostname_ips(hostname)
                if resolved_ips and all(
                    ipaddress.ip_address(rip).is_loopback or (extra_allowed_hosts and rip in extra_allowed_hosts)
                    for rip in resolved_ips
                ):
                    is_allowed = True
            except Exception:
                is_allowed = False

    if not is_allowed:
        raise TargetOutOfScopeError(
            f"Target host '{hostname}' is outside the authorized security scope. "
            f"Only local laboratory and authorized assets are permitted."
        )

    # Protect against cloud metadata endpoints (169.254.169.254) and other forbidden ranges
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise TargetOutOfScopeError(f"IP address {hostname} belongs to a restricted/forbidden address range.")
    except ValueError:
        pass

    path = parsed.path or "/"
    if parsed.query:
        normalized_url = f"{scheme}://{hostname}:{port}{path}?{parsed.query}"
    else:
        normalized_url = f"{scheme}://{hostname}:{port}{path}"

    return scheme, hostname, port, normalized_url


def resolve_hostname_ips(hostname: str) -> List[str]:
    """Resolves all IPv4 and IPv6 addresses for a hostname."""
    cleaned = hostname.strip().rstrip(".")
    try:
        addrinfo = socket.getaddrinfo(cleaned, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise WebValidationError(f"DNS resolution failed for '{hostname}': {exc}") from exc

    ips: List[str] = []
    for _, _, _, _, sockaddr in addrinfo:
        ip = sockaddr[0]
        if ip not in ips:
            ips.append(ip)
    return ips


def validate_path_allowed(path: str, allowed_paths: Optional[str]) -> bool:
    """
    Checks if a given path matches the allowed paths pattern (e.g. '/*' or comma-separated list).
    """
    if not allowed_paths or allowed_paths.strip() in ("", "*", "/*"):
        return True

    patterns = [p.strip() for p in allowed_paths.replace("\n", ",").split(",") if p.strip()]
    if not patterns or "/*" in patterns or "*" in patterns:
        return True

    normalized_path = "/" + path.lstrip("/")
    for pattern in patterns:
        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            if normalized_path.startswith(prefix):
                return True
        elif fnmatch.fnmatch(normalized_path, pattern):
            return True

    return False


def validate_redirect_url(redirect_url: str, base_host: str, extra_allowed_hosts: Optional[Set[str]] = None) -> bool:
    """
    Validates that an HTTP redirect target remains within authorized localhost / scope boundary.
    """
    try:
        parsed = urlparse(redirect_url)
        # Relative redirect is within base_host
        if not parsed.netloc:
            return True

        redirect_host = (parsed.hostname or "").lower()
        if redirect_host == base_host.lower():
            return True

        allowed = set(DEFAULT_ALLOWED_HOSTS)
        if extra_allowed_hosts:
            allowed.update(h.lower().strip() for h in extra_allowed_hosts)

        return redirect_host in allowed
    except Exception:
        return False
