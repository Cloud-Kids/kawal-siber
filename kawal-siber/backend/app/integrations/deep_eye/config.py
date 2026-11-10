"""
Configuration for Deep Eye integration adapter.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any

# Root paths
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEEP_EYE_ROOT = Path(
    os.getenv("DEEP_EYE_ROOT", str(WORKSPACE_ROOT / "tools" / "deep-eye"))
).resolve()

# Deep Eye Python virtualenv binary
_venv_python_win = DEEP_EYE_ROOT / ".deep-venv" / "Scripts" / "python.exe"
_venv_python_unix = DEEP_EYE_ROOT / ".deep-venv" / "bin" / "python"

if _venv_python_win.exists():
    DEEP_EYE_PYTHON_PATH = str(_venv_python_win)
elif _venv_python_unix.exists():
    DEEP_EYE_PYTHON_PATH = str(_venv_python_unix)
else:
    import sys
    DEEP_EYE_PYTHON_PATH = sys.executable

DEEP_EYE_SCRIPT_PATH = str(DEEP_EYE_ROOT / "deep_eye.py")

# Execution constraints
DEFAULT_SUBPROCESS_TIMEOUT_SECONDS = int(os.getenv("DEEP_EYE_TIMEOUT_SECONDS", "120"))
DEFAULT_RATE_LIMIT_RPS = float(os.getenv("DEEP_EYE_RATE_LIMIT_RPS", "2.0"))
DEFAULT_REQUEST_BUDGET = int(os.getenv("DEEP_EYE_REQUEST_BUDGET", "50"))

# Authorized local target defaults
DEFAULT_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}
DEFAULT_ALLOWED_PORTS = {80, 443, 3000, 8000, 8080, 8443, 5000, 8765}

# Assessment profiles specification
PROFILES: Dict[str, Dict[str, Any]] = {
    "PASSIVE": {
        "description": "Non-intrusive assessment: security headers, cookies, TLS/SSL, CORS, CSP, metadata disclosure",
        "max_requests": 20,
        "rate_limit_rps": 5.0,
        "timeout_seconds": 60,
        "active_payloads": False,
    },
    "SAFE_LOCAL": {
        "description": "Safe local assessment: non-destructive endpoint enumeration, HTTP methods, rate-limited reflection tests",
        "max_requests": 50,
        "rate_limit_rps": 2.0,
        "timeout_seconds": 120,
        "active_payloads": False,
    },
}

