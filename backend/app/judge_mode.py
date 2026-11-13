"""
judge_mode.py — Public Judge Read-Only enforcement layer.

Activated only when env KAWAL_JUDGE_MODE=true. Enforces:
  - GET/HEAD only on an explicit route allowlist (deny-by-default)
  - all other methods -> 403
  - /docs, /redoc, /openapi.json disabled
  - simple per-IP rate limit
  - report download restricted to UUID-shaped ids
"""
from __future__ import annotations

import os
import re
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

JUDGE_MODE = os.environ.get("KAWAL_JUDGE_MODE", "").lower() == "true"

# Explicit GET allowlist (path prefixes under /api/v1). Anything not listed -> 403.
_ALLOWED_GET_PREFIXES = (
    "/api/v1/health",
    "/api/v1/assets",
    "/api/v1/scan-scopes",
    "/api/v1/scans",
    "/api/v1/incidents",
    "/api/v1/incident-intelligence",
    "/api/v1/monitoring",
    "/api/v1/security-events",
    "/api/v1/security-alerts",
    "/api/v1/pcap",
    "/api/v1/web-targets",
    "/api/v1/web-assessments",
    "/api/v1/web-findings",
    "/api/v1/web-security",
    "/api/v1/reports",
    "/api/v1/ai",
)

# Routes that must NEVER be reachable even via GET (defense in depth)
_DENIED_PREFIXES = (
    "/api/v1/admin",
)

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# Simple in-memory rate limit: 120 req/min per IP
_RATE_LIMIT = 120
_WINDOW = 60.0
_hits: dict[str, deque[float]] = defaultdict(deque)


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    dq = _hits[ip]
    while dq and now - dq[0] > _WINDOW:
        dq.popleft()
    if len(dq) >= _RATE_LIMIT:
        return True
    dq.append(now)
    return False


def _client_ip(request: Request) -> str:
    # Prefer Cloudflare-provided / proxy-set headers that clients cannot
    # spoof through the tunnel. X-Forwarded-For leftmost is client-controlled
    # (nginx appends to it), so it is only a last resort.
    for header in ("cf-connecting-ip", "x-real-ip"):
        val = request.headers.get(header)
        if val:
            return val.strip()
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[-1].strip()  # rightmost = appended by trusted proxy
    return request.client.host if request.client else "unknown"


def judge_guard(request: Request):
    """Return a JSONResponse to short-circuit, or None to continue."""
    if not JUDGE_MODE:
        return None

    path = request.url.path

    # Disable interactive docs / schema in public judge env
    if path in ("/docs", "/redoc", "/openapi.json"):
        return JSONResponse(status_code=403, content={"detail": "Disabled in judge demo mode."})

    # Only GET/HEAD allowed anywhere
    if request.method not in ("GET", "HEAD"):
        return JSONResponse(
            status_code=403,
            content={"detail": "Read-only judge demo: write operations are disabled."},
        )

    # Deny explicit blocked prefixes first
    if path.startswith(_DENIED_PREFIXES):
        return JSONResponse(status_code=403, content={"detail": "Forbidden."})

    # Report download: id segment must be a UUID (path traversal / IDOR guard)
    if "/reports/" in path and path.endswith("/download"):
        seg = path.split("/")[-2]
        if not _UUID_RE.match(seg):
            return JSONResponse(status_code=403, content={"detail": "Invalid report identifier."})

    # Everything outside /api/v1 (e.g. stray routes) -> deny
    if not path.startswith("/api/v1/"):
        if path in ("/", "/healthz"):
            return None
        return JSONResponse(status_code=404, content={"detail": "Not found."})

    # Allowlist check — require path-segment boundary so /api/v1/assetsfoo
    # does not match the /api/v1/assets prefix.
    if not any(
        path == p or path.startswith(p + "/") or path.startswith(p + "?")
        for p in _ALLOWED_GET_PREFIXES
    ):
        return JSONResponse(status_code=403, content={"detail": "Endpoint not available in judge demo mode."})

    # Rate limit
    if _rate_limited(_client_ip(request)):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."})

    return None
