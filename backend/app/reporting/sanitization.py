"""
sanitization.py — Report content sanitization and formula injection protection.
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Any, List, Union

# Regex for sensitive token redaction
_SENSITIVE_RE = re.compile(
    r"(?i)(authorization:\s*(bearer|basic)\s+)[^\s,;]+|"
    r"(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*[^\s,;]+|"
    r"(session|cookie|sessid)\s*[:=]\s*[^\s,;]+"
)

# Characters that trigger formula execution in spreadsheet software (CSV Injection / DDE)
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n", "%", "|")

# Allowed URL schemes for safe hyperlink rendering
_ALLOWED_SCHEMES = ("http://", "https://", "#", "/")


def redact_sensitive_data(text: Any) -> str:
    """Sanitize and redact credentials, authorization tokens, and API secrets from text."""
    if text is None:
        return ""
    s = str(text)
    return _SENSITIVE_RE.sub(r"\1[REDACTED]", s)


def validate_safe_url(url: Any) -> str:
    """
    Validate and sanitize URLs for HTML/PDF rendering.
    Allows only http://, https://, anchor (#), or legitimate relative paths (e.g. /dashboard).
    Explicitly rejects:
    - Dangerous pseudo-protocols: javascript:, data:, vbscript:, file:, blob: (including case and URL-encoded variants)
    - Protocol-relative URLs (e.g. //example.com)
    - Backslash-based bypasses (e.g. \\example.com, /\\example.com, https:\\)
    - Control characters (\x00-\x1f, \x7f)
    - Quote and HTML tag injection attempts
    """
    if url is None:
        return "#"
    s = str(url).strip()
    if not s:
        return "#"

    # Reject any control characters (\x00-\x1f, \x7f) or quote/tag injection characters
    if any(ord(c) < 32 or ord(c) == 127 or c in ('"', "'", "<", ">") for c in s):
        return "#"

    # Reject any backslash anywhere (prevents UNC paths, protocol-relative backslash, and domain bypasses)
    if "\\" in s:
        return "#"

    # Reject protocol-relative URLs (//example.com, ///example.com)
    if s.startswith("//"):
        return "#"

    # Check decoded/unquoted representation to catch encoded schemes (e.g. %6a%61%76... or javascript%3a)
    unquoted = urllib.parse.unquote(s).strip().lower()
    # Remove whitespace/control chars within the decoded string (some browsers ignore embedded spaces/tabs in protocol)
    unquoted_clean = re.sub(r"[\s\x00-\x1f]", "", unquoted)
    dangerous_schemes = ("javascript:", "data:", "vbscript:", "file:", "blob:")
    if any(unquoted_clean.startswith(bad) for bad in dangerous_schemes):
        return "#"

    # Validate against allowed patterns
    if s.startswith(("http://", "https://")):
        try:
            parsed = urllib.parse.urlsplit(s)
            if not parsed.netloc:
                return "#"
            return s
        except Exception:
            return "#"
    elif s.startswith("#"):
        return s
    elif s.startswith("/") and not s.startswith(("//", "/\\")):
        return s

    return "#"


def sanitize_csv_cell(value: Any) -> str:
    """
    Sanitize a cell value for CSV export to prevent formula injection (CSV Injection / DDE).
    Neutralizes formula triggers (=, +, -, @, tab, cr, lf, %, |) by prepending a single quote (').
    Also neutralizes dangerous control characters and null bytes.
    """
    if value is None:
        return ""
    s = str(value)
    # Neutralize null bytes
    s = s.replace("\x00", "")

    # Check if raw string or stripped string starts with formula trigger characters
    if s.startswith(_FORMULA_PREFIXES):
        return f"'{s}"
    s_lstripped = s.lstrip(" \t\r\n")
    if s_lstripped and s_lstripped.startswith(_FORMULA_PREFIXES):
        return f"'{s}"
    return s


def sanitize_for_html(text: Any) -> str:
    """Escape HTML control characters safely with quote escaping."""
    if text is None:
        return ""
    import html
    redacted = redact_sensitive_data(text)
    return html.escape(str(redacted), quote=True)


