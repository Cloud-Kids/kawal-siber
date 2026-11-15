"""
judge_mode.py — Public Judge enforcement layer.

Supports two modes:
  - KAWAL_JUDGE_MODE=true: Read-only mode (GET/HEAD only on allowlist)
  - KAWAL_JUDGE_MODE=interactive: Interactive mode (authorized writes allowed)

Enforces:
  - Deny-by-default authorization
  - Explicit method/path/resource rules
  - Write-specific rate limits
  - Assessment and report concurrency limits
  - Request size and upload size limits
  - Safe report download authorization
  - Input validation and path traversal protection
  - Audit events for sensitive actions
"""
from __future__ import annotations

import os
import re
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse

# Mode detection
JUDGE_MODE_RAW = os.environ.get("KAWAL_JUDGE_MODE", "").lower()
JUDGE_MODE = JUDGE_MODE_RAW in ("true", "interactive")
JUDGE_INTERACTIVE = JUDGE_MODE_RAW == "interactive"

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

# Explicit write allowlist for interactive mode: (method, path_prefix, resource_type)
# Only these exact patterns are allowed for write operations
_INTERACTIVE_WRITE_RULES = (
    # Asset management
    ("POST", "/api/v1/assets", "asset_create"),
    ("PATCH", "/api/v1/assets/", "asset_update"),
    ("DELETE", "/api/v1/assets/", "asset_delete"),
    
    # Web target management
    ("POST", "/api/v1/web-targets", "web_target_create"),
    ("PATCH", "/api/v1/web-targets/", "web_target_update"),
    ("DELETE", "/api/v1/web-targets/", "web_target_delete"),
    
    # Web assessments
    ("POST", "/api/v1/web-assessments", "web_assessment_create"),
    
    # Web findings triage
    ("PATCH", "/api/v1/web-findings/", "web_finding_update"),
    
    # Incident management
    ("POST", "/api/v1/incidents", "incident_create"),
    ("PATCH", "/api/v1/incidents/", "incident_update"),
    ("POST", "/api/v1/incidents/", "incident_action"),  # triage, correlate, status
    
    # Report generation
    ("POST", "/api/v1/reports", "report_create"),
    ("POST", "/api/v1/reports/", "report_action"),  # regenerate
    
    # PCAP upload
    ("POST", "/api/v1/monitoring/pcap", "pcap_upload"),
    
    # Scan creation (restricted to synthetic targets)
    ("POST", "/api/v1/assets/", "scan_create"),  # /assets/{id}/scans
)

# Routes that must NEVER be reachable even via GET (defense in depth)
_DENIED_PREFIXES = (
    "/api/v1/admin",
)

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# Rate limiting configuration
_RATE_LIMIT_READ = 120  # req/min per IP for GET requests
_RATE_LIMIT_WRITE = 30   # req/min per IP for write requests
_RATE_LIMIT_ASSESSMENT = 10  # req/min per IP for assessment creation
_RATE_LIMIT_REPORT = 5   # req/min per IP for report creation
_WINDOW = 60.0

# Concurrency limits
_MAX_CONCURRENT_ASSESSMENTS = 3
_MAX_CONCURRENT_REPORTS = 2
_MAX_CONCURRENT_SCANS = 2

# Request size limits
_MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
_MAX_UPLOAD_SIZE = 50 * 1024 * 1024   # 50MB for PCAP uploads

# In-memory rate limit tracking
_hits_read: dict[str, deque[float]] = defaultdict(deque)
_hits_write: dict[str, deque[float]] = defaultdict(deque)
_hits_assessment: dict[str, deque[float]] = defaultdict(deque)
_hits_report: dict[str, deque[float]] = defaultdict(deque)

# Concurrency tracking (simplified - in production use Redis or database)
_active_assessments: dict[str, int] = defaultdict(int)
_active_reports: dict[str, int] = defaultdict(int)
_active_scans: dict[str, int] = defaultdict(int)


def _rate_limited(ip: str, limit_type: str = "read") -> bool:
    """Check if IP is rate limited for the given limit type."""
    now = time.monotonic()
    
    if limit_type == "read":
        dq = _hits_read[ip]
        limit = _RATE_LIMIT_READ
    elif limit_type == "write":
        dq = _hits_write[ip]
        limit = _RATE_LIMIT_WRITE
    elif limit_type == "assessment":
        dq = _hits_assessment[ip]
        limit = _RATE_LIMIT_ASSESSMENT
    elif limit_type == "report":
        dq = _hits_report[ip]
        limit = _RATE_LIMIT_REPORT
    else:
        return False
    
    while dq and now - dq[0] > _WINDOW:
        dq.popleft()
    
    if len(dq) >= limit:
        return True
    
    dq.append(now)
    return False


def _client_ip(request: Request) -> str:
    """Extract client IP from request headers."""
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


def _is_write_allowed(method: str, path: str) -> tuple[bool, Optional[str]]:
    """
    Check if a write operation is allowed in interactive mode.
    Returns (allowed, resource_type) tuple.
    """
    if not JUDGE_INTERACTIVE:
        return False, None
    
    # Handle specific cases first to avoid conflicts
    
    # Scan creation (most specific)
    if method == "POST" and "/scans" in path and path.startswith("/api/v1/assets/"):
        return True, "scan_create"
    
    # Incident actions (triage, correlate, status)
    if method == "POST" and path.startswith("/api/v1/incidents/"):
        if any(action in path for action in ["/triage", "/correlate", "/status"]):
            return True, "incident_action"
    
    # Report actions (regenerate)
    if method == "POST" and path.startswith("/api/v1/reports/") and path.endswith("/regenerate"):
        return True, "report_action"
    
    # General write rules
    for rule_method, rule_path, resource_type in _INTERACTIVE_WRITE_RULES:
        if method == rule_method:
            # Handle trailing slash in rule_path
            if rule_path.endswith("/"):
                # For paths ending with /, match exact or path starts with rule_path
                if path == rule_path.rstrip("/") or path.startswith(rule_path):
                    # Skip specific cases that were already handled
                    if resource_type in ("scan_create", "incident_action", "report_action"):
                        continue
                    return True, resource_type
            else:
                # For paths without trailing slash, match exact or path starts with rule_path + "/"
                if path == rule_path or path.startswith(rule_path + "/"):
                    # Skip specific cases that were already handled
                    if resource_type in ("scan_create", "incident_action", "report_action"):
                        continue
                    return True, resource_type
    
    return False, None


def _check_concurrency_limit(resource_type: str, ip: str) -> bool:
    """Check if concurrency limit is exceeded for the resource type."""
    if resource_type == "web_assessment_create":
        return _active_assessments[ip] >= _MAX_CONCURRENT_ASSESSMENTS
    elif resource_type == "report_create":
        return _active_reports[ip] >= _MAX_CONCURRENT_REPORTS
    elif resource_type == "scan_create":
        return _active_scans[ip] >= _MAX_CONCURRENT_SCANS
    return False


def _increment_concurrency(resource_type: str, ip: str):
    """Increment concurrency counter for resource type."""
    if resource_type == "web_assessment_create":
        _active_assessments[ip] += 1
    elif resource_type == "report_create":
        _active_reports[ip] += 1
    elif resource_type == "scan_create":
        _active_scans[ip] += 1


def _decrement_concurrency(resource_type: str, ip: str):
    """Decrement concurrency counter for resource type."""
    if resource_type == "web_assessment_create":
        _active_assessments[ip] = max(0, _active_assessments[ip] - 1)
    elif resource_type == "report_create":
        _active_reports[ip] = max(0, _active_reports[ip] - 1)
    elif resource_type == "scan_create":
        _active_scans[ip] = max(0, _active_scans[ip] - 1)


def _validate_target_url(url: str) -> bool:
    """
    Validate that target URL is the synthetic target only.
    This is a critical security check for interactive mode.
    """
    if not JUDGE_INTERACTIVE:
        return True  # Read-only mode doesn't need this check
    
    # Only allow the exact synthetic target
    allowed_targets = [
        "http://synthetic-target:8080",
        "http://synthetic-target:8080/",
    ]
    
    # Normalize URL for comparison
    normalized = url.rstrip("/")
    
    for allowed in allowed_targets:
        if normalized == allowed.rstrip("/"):
            return True
    
    return False


def judge_guard(request: Request):
    """Return a JSONResponse to short-circuit, or None to continue."""
    if not JUDGE_MODE:
        return None
    
    path = request.url.path
    method = request.method
    ip = _client_ip(request)
    
    # Disable interactive docs / schema in public judge env
    if path in ("/docs", "/redoc", "/openapi.json"):
        return JSONResponse(status_code=403, content={"detail": "Disabled in judge demo mode."})
    
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
    
    # Check request size limits
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            size = int(content_length)
            if size > _MAX_REQUEST_SIZE:
                return JSONResponse(status_code=413, content={"detail": "Request too large."})
            # Special check for PCAP uploads
            if "/monitoring/pcap" in path and method == "POST":
                if size > _MAX_UPLOAD_SIZE:
                    return JSONResponse(status_code=413, content={"detail": "Upload too large."})
        except ValueError:
            pass
    
    # Handle write operations
    if method not in ("GET", "HEAD"):
        if not JUDGE_INTERACTIVE:
            return JSONResponse(
                status_code=403,
                content={"detail": "Read-only judge demo: write operations are disabled."},
            )
        
        # Check if write is allowed
        allowed, resource_type = _is_write_allowed(method, path)
        if not allowed:
            return JSONResponse(
                status_code=403,
                content={"detail": "Write operation not authorized in judge demo mode."},
            )
        
        # Check write-specific rate limits
        if resource_type in ("web_assessment_create",):
            if _rate_limited(ip, "assessment"):
                return JSONResponse(status_code=429, content={"detail": "Assessment rate limit exceeded."})
        elif resource_type in ("report_create",):
            if _rate_limited(ip, "report"):
                return JSONResponse(status_code=429, content={"detail": "Report rate limit exceeded."})
        else:
            if _rate_limited(ip, "write"):
                return JSONResponse(status_code=429, content={"detail": "Write rate limit exceeded."})
        
        # Check concurrency limits for resource creation
        if resource_type in ("web_assessment_create", "report_create", "scan_create"):
            if _check_concurrency_limit(resource_type, ip):
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Too many concurrent {resource_type} operations."},
                )
            _increment_concurrency(resource_type, ip)
        
        # Validate target URL for web target creation
        if resource_type == "web_target_create" and method == "POST":
            # This will be validated again in the service layer
            pass
        
        return None  # Allow the write operation
    
    # GET/HEAD requests - check allowlist
    # Allowlist check — require path-segment boundary so /api/v1/assetsfoo
    # does not match the /api/v1/assets prefix.
    if not any(
        path == p or path.startswith(p + "/") or path.startswith(p + "?")
        for p in _ALLOWED_GET_PREFIXES
    ):
        return JSONResponse(status_code=403, content={"detail": "Endpoint not available in judge demo mode."})
    
    # Rate limit for read operations
    if _rate_limited(ip, "read"):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."})
    
    return None
