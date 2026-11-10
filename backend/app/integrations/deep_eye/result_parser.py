"""
Result parser and normalizer for Deep Eye and Web Security Assessments.
Handles vulnerability type normalization, severity mapping, evidence sanitization, and SHA-256 fingerprinting.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Standard severity mapping
SEVERITY_LEVELS = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"}

# Regex for stripping sensitive tokens in evidence
SENSITIVE_PATTERNS = [
    (re.compile(r"(?i)(authorization:\s*bearer\s+)[^\r\n]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(authorization:\s*basic\s+)[^\r\n]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(cookie:\s*)[^\r\n]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(set-cookie:\s*)[^\r\n]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(password|passwd|secret|api[-_]?key|token)=([^\s&]+)"), r"\1=[REDACTED]"),
    (re.compile(r"(?i)('|\")?(password|secret|api[-_]?key|token)('|\")?\s*:\s*('|\")[^'\"]+('|\")"), r'"\2": "[REDACTED]"'),
]


def sanitize_evidence(evidence: Optional[str]) -> Optional[str]:
    """Sanitizes sensitive authorization headers, cookies, passwords, and tokens from evidence."""
    if not evidence or not isinstance(evidence, str):
        return None

    sanitized = evidence
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    # Limit maximum length to prevent database blowup
    if len(sanitized) > 16384:
        sanitized = sanitized[:16384] + "\n...[TRUNCATED FOR SIZE]..."

    return sanitized


def compute_finding_fingerprint(
    web_target_id: int,
    vulnerability_type: str,
    title: str,
    affected_url: str,
) -> str:
    """
    Computes a deterministic SHA-256 fingerprint for deduplicating findings.
    Normalized by target, vulnerability type, title, and URL path.
    """
    try:
        parsed = urlparse(affected_url)
        path = parsed.path.rstrip("/") or "/"
    except Exception:
        path = affected_url

    raw_key = f"{web_target_id}:{vulnerability_type.upper().strip()}:{title.strip()}:{path}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def normalize_severity(raw_severity: Optional[str]) -> str:
    """Normalizes arbitrary severity strings into standard enum."""
    if not raw_severity:
        return "INFORMATIONAL"

    val = str(raw_severity).upper().strip()
    if val in SEVERITY_LEVELS:
        return val

    if "CRIT" in val:
        return "CRITICAL"
    if "HIGH" in val:
        return "HIGH"
    if "MED" in val:
        return "MEDIUM"
    if "LOW" in val:
        return "LOW"
    return "INFORMATIONAL"


def normalize_finding(
    raw_item: Dict[str, Any],
    web_target_id: int,
    base_url: str,
) -> Dict[str, Any]:
    """
    Normalizes raw finding dictionary into standard WebFinding schema fields.
    """
    title = str(raw_item.get("title") or raw_item.get("name") or "Security Finding").strip()
    vuln_type = str(
        raw_item.get("vulnerability_type")
        or raw_item.get("type")
        or "WEB_VULNERABILITY"
    ).upper().replace(" ", "_")

    severity = normalize_severity(raw_item.get("severity"))
    confidence = str(raw_item.get("confidence") or "MEDIUM").upper()
    if confidence not in ("HIGH", "MEDIUM", "LOW", "CERTAIN", "FIRM", "TENTATIVE"):
        confidence = "MEDIUM"

    affected_url = str(raw_item.get("affected_url") or raw_item.get("url") or base_url).strip()
    description = str(raw_item.get("description") or title).strip()
    evidence = sanitize_evidence(raw_item.get("evidence") or raw_item.get("proof"))
    remediation = raw_item.get("remediation") or raw_item.get("solution")
    reference = raw_item.get("reference") or raw_item.get("cve")

    fingerprint = compute_finding_fingerprint(
        web_target_id=web_target_id,
        vulnerability_type=vuln_type,
        title=title,
        affected_url=affected_url,
    )

    # Initial finding status
    finding_status = "NEEDS_REVIEW" if severity in ("CRITICAL", "HIGH") else "UNVERIFIED"

    return {
        "title": title[:255],
        "vulnerability_type": vuln_type[:100],
        "severity": severity,
        "confidence": confidence[:20],
        "finding_status": finding_status,
        "affected_url": affected_url[:1024],
        "description": description,
        "evidence": evidence,
        "remediation": remediation,
        "reference": reference,
        "fingerprint": fingerprint,
    }


def parse_and_normalize_results(
    raw_findings: List[Dict[str, Any]],
    web_target_id: int,
    base_url: str,
) -> List[Dict[str, Any]]:
    """
    Normalizes a list of findings and removes in-memory duplicates based on fingerprint.
    """
    normalized_list: List[Dict[str, Any]] = []
    seen_fingerprints = set()

    for item in raw_findings:
        normalized = normalize_finding(item, web_target_id, base_url)
        fp = normalized["fingerprint"]
        if fp not in seen_fingerprints:
            seen_fingerprints.add(fp)
            normalized_list.append(normalized)

    return normalized_list

