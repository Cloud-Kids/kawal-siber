"""
Deep Eye Integration Adapter.
Provides controlled subprocess invocation of Deep Eye and a built-in deterministic assessment engine
for PASSIVE and SAFE_LOCAL profiles.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
import yaml

from app.integrations.deep_eye.config import (
    DEEP_EYE_PYTHON_PATH,
    DEEP_EYE_SCRIPT_PATH,
    DEEP_EYE_ROOT,
    PROFILES,
    DEFAULT_SUBPROCESS_TIMEOUT_SECONDS,
)
from app.integrations.deep_eye.result_parser import parse_and_normalize_results
from app.integrations.deep_eye.validator import (
    parse_and_validate_target_url,
    validate_path_allowed,
    validate_redirect_url,
)

logger = logging.getLogger(__name__)


@dataclass
class AssessmentExecutionResult:
    """Holds the outcome of a web security assessment execution."""
    success: bool
    findings: List[Dict[str, Any]] = field(default_factory=list)
    raw_output: str = ""
    error_message: Optional[str] = None
    duration_ms: int = 0
    tool_name: str = "Deep Eye"
    tool_version: str = "1.4.0 (Hanzou)"


class DeepEyeAdapter:
    """Adapter bridging KAWAL SIBER backend and Deep Eye engine."""

    def __init__(self) -> None:
        self.python_path = DEEP_EYE_PYTHON_PATH
        self.script_path = DEEP_EYE_SCRIPT_PATH
        self.root_path = DEEP_EYE_ROOT

    def is_available(self) -> bool:
        """Checks if Deep Eye script and python binary exist."""
        return os.path.exists(self.python_path) and os.path.exists(self.script_path)

    def get_version(self) -> str:
        """Returns Deep Eye version string."""
        if not self.is_available():
            return "Deep Eye (Engine not initialized)"
        try:
            res = subprocess.run(
                [self.python_path, self.script_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,
            )
            if res.returncode == 0 and res.stdout:
                return res.stdout.strip()
        except Exception as exc:
            logger.warning(f"Failed to query Deep Eye version: {exc}")
        return "Deep Eye v1.4.0 (Hanzou)"

    def execute_assessment(
        self,
        target_url: str,
        profile: str = "PASSIVE",
        allowed_paths: Optional[str] = None,
        web_target_id: int = 0,
        extra_allowed_hosts: Optional[set] = None,
    ) -> AssessmentExecutionResult:
        """
        Executes web security assessment against authorized localhost target.
        """
        start_time = time.monotonic()
        profile_key = profile.upper().strip()
        profile_cfg = PROFILES.get(profile_key, PROFILES["PASSIVE"])

        # Validate URL and scheme
        try:
            scheme, hostname, port, normalized_url = parse_and_validate_target_url(
                target_url, extra_allowed_hosts=extra_allowed_hosts
            )
        except Exception as exc:
            return AssessmentExecutionResult(
                success=False,
                error_message=f"Validation failed: {exc}",
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )

        # Enforce path allowlist
        parsed = urlparse(normalized_url)
        if not validate_path_allowed(parsed.path, allowed_paths):
            return AssessmentExecutionResult(
                success=False,
                error_message=f"Path '{parsed.path}' is not within authorized allowed_paths policy.",
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )

        raw_findings: List[Dict[str, Any]] = []
        raw_logs: List[str] = []

        # Step 1: Run deterministic passive assessment engine
        try:
            passive_findings = self._run_deterministic_passive(
                target_url=normalized_url,
                scheme=scheme,
                hostname=hostname,
                port=port,
            )
            raw_findings.extend(passive_findings)
            raw_logs.append(f"Passive check completed: {len(passive_findings)} finding(s) detected.")
        except Exception as exc:
            logger.exception(f"Deterministic passive audit failed: {exc}")
            raw_logs.append(f"Deterministic passive audit error: {exc}")

        # Step 2: If SAFE_LOCAL profile, run safe non-destructive active checks
        if profile_key == "SAFE_LOCAL":
            try:
                active_findings = self._run_safe_local_checks(
                    target_url=normalized_url,
                    allowed_paths=allowed_paths,
                    request_budget=profile_cfg.get("max_requests", 50),
                )
                raw_findings.extend(active_findings)
                raw_logs.append(f"Safe local checks completed: {len(active_findings)} finding(s) detected.")
            except Exception as exc:
                logger.exception(f"Safe local checks failed: {exc}")
                raw_logs.append(f"Safe local checks error: {exc}")

            # Optionally run Deep Eye CLI subprocess if available
            if self.is_available():
                try:
                    cli_findings, cli_log = self._run_deep_eye_subprocess(
                        target_url=normalized_url,
                        timeout_seconds=profile_cfg.get("timeout_seconds", 60),
                    )
                    raw_findings.extend(cli_findings)
                    raw_logs.append(f"Deep Eye CLI execution finished. Output: {cli_log[:500]}")
                except Exception as exc:
                    logger.warning(f"Deep Eye CLI execution bypassed/failed: {exc}")
                    raw_logs.append(f"Deep Eye CLI execution bypassed/failed: {exc}")

        # Normalize and deduplicate findings
        normalized_findings = parse_and_normalize_results(
            raw_findings=raw_findings,
            web_target_id=web_target_id,
            base_url=normalized_url,
        )

        duration_ms = int((time.monotonic() - start_time) * 1000)
        tool_version = self.get_version()

        return AssessmentExecutionResult(
            success=True,
            findings=normalized_findings,
            raw_output="\n".join(raw_logs),
            duration_ms=duration_ms,
            tool_name="Deep Eye",
            tool_version=tool_version,
        )

    def _run_deterministic_passive(
        self,
        target_url: str,
        scheme: str,
        hostname: str,
        port: int,
    ) -> List[Dict[str, Any]]:
        """
        Performs non-intrusive security audits:
        - Security Headers (CSP, X-Frame-Options, X-Content-Type-Options, HSTS, Referrer-Policy, Permissions-Policy)
        - Cookie Security (HttpOnly, Secure, SameSite)
        - CORS misconfigurations (wildcard reflection, credentials)
        - Server & technology disclosures (Server, X-Powered-By)
        """
        findings: List[Dict[str, Any]] = []

        client = httpx.Client(
            timeout=10.0,
            verify=False,
            follow_redirects=False,
        )

        try:
            # Test root or target URL
            resp = client.get(target_url, headers={"User-Agent": "KawalSiber-DeepEye/1.4"})
        except Exception as exc:
            logger.warning(f"Passive probe GET {target_url} failed: {exc}")
            # If server is unreachable, return a finding
            findings.append({
                "title": "Web Service Unreachable",
                "vulnerability_type": "SERVICE_UNREACHABLE",
                "severity": "LOW",
                "confidence": "CERTAIN",
                "affected_url": target_url,
                "description": f"Failed to connect to target web service: {exc}",
                "evidence": str(exc),
                "remediation": "Verify that the web application service is running and listening on the specified port.",
            })
            return findings
        finally:
            client.close()

        headers = {k.lower(): v for k, v in resp.headers.items()}

        # 1. Content-Security-Policy
        if "content-security-policy" not in headers:
            findings.append({
                "title": "Missing Content-Security-Policy (CSP) Header",
                "vulnerability_type": "MISSING_SECURITY_HEADER",
                "severity": "MEDIUM",
                "confidence": "CERTAIN",
                "affected_url": target_url,
                "description": "Content-Security-Policy (CSP) header is not implemented. CSP prevents Cross-Site Scripting (XSS) and code injection attacks.",
                "evidence": f"HTTP/{resp.http_version} {resp.status_code}\nHeaders: {dict(resp.headers)}",
                "remediation": "Configure a restrictive Content-Security-Policy header (e.g., default-src 'self').",
                "reference": "https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP",
            })

        # 2. X-Frame-Options
        if "x-frame-options" not in headers and "frame-ancestors" not in headers.get("content-security-policy", ""):
            findings.append({
                "title": "Missing X-Frame-Options Header",
                "vulnerability_type": "CLICKJACKING_PROTECTION_MISSING",
                "severity": "MEDIUM",
                "confidence": "CERTAIN",
                "affected_url": target_url,
                "description": "The X-Frame-Options header is absent, making the web page vulnerable to clickjacking attacks via framing/iframes.",
                "evidence": f"Response headers lack X-Frame-Options.",
                "remediation": "Set 'X-Frame-Options: DENY' or 'X-Frame-Options: SAMEORIGIN'.",
                "reference": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Frame-Options",
            })

        # 3. X-Content-Type-Options
        if headers.get("x-content-type-options", "").lower() != "nosniff":
            findings.append({
                "title": "Missing or Weak X-Content-Type-Options Header",
                "vulnerability_type": "MIME_SNIFFING_VULNERABILITY",
                "severity": "LOW",
                "confidence": "CERTAIN",
                "affected_url": target_url,
                "description": "The X-Content-Type-Options header is not set to 'nosniff'. Browsers may perform MIME-type sniffing.",
                "evidence": f"x-content-type-options: {headers.get('x-content-type-options', '[MISSING]')}",
                "remediation": "Add 'X-Content-Type-Options: nosniff' header.",
                "reference": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Content-Type-Options",
            })

        # 4. Strict-Transport-Security (HSTS)
        if scheme == "https" and "strict-transport-security" not in headers:
            findings.append({
                "title": "Missing HTTP Strict Transport Security (HSTS) Header",
                "vulnerability_type": "MISSING_HSTS_HEADER",
                "severity": "LOW",
                "confidence": "CERTAIN",
                "affected_url": target_url,
                "description": "The application does not enforce HTTPS connections using Strict-Transport-Security header.",
                "evidence": "HTTPS connection established without Strict-Transport-Security header.",
                "remediation": "Set 'Strict-Transport-Security: max-age=31536000; includeSubDomains'.",
                "reference": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security",
            })

        # 5. Referrer-Policy
        if "referrer-policy" not in headers:
            findings.append({
                "title": "Missing Referrer-Policy Header",
                "vulnerability_type": "INFORMATION_DISCLOSURE",
                "severity": "INFORMATIONAL",
                "confidence": "CERTAIN",
                "affected_url": target_url,
                "description": "Referrer-Policy header is missing, which may leak referrer information across navigation.",
                "evidence": "Referrer-Policy header absent in HTTP response.",
                "remediation": "Set 'Referrer-Policy: strict-origin-when-cross-origin' or 'no-referrer'.",
                "reference": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Referrer-Policy",
            })

        # 6. Information Disclosure (Server / X-Powered-By)
        if "server" in headers:
            server_val = headers["server"]
            # If server header specifies detailed version like uvicorn, nginx/1.18, Apache/2.4
            if any(char.isdigit() for char in server_val) or "/" in server_val:
                findings.append({
                    "title": "Detailed Web Server Version Disclosure",
                    "vulnerability_type": "INFORMATION_DISCLOSURE",
                    "severity": "LOW",
                    "confidence": "HIGH",
                    "affected_url": target_url,
                    "description": f"The Server header discloses web server software and version: '{server_val}'.",
                    "evidence": f"Server: {server_val}",
                    "remediation": "Suppress or genericize the Server response banner in web server configuration.",
                })

        if "x-powered-by" in headers:
            powered_by = headers["x-powered-by"]
            findings.append({
                "title": "Technology Fingerprint Disclosed via X-Powered-By",
                "vulnerability_type": "INFORMATION_DISCLOSURE",
                "severity": "LOW",
                "confidence": "CERTAIN",
                "affected_url": target_url,
                "description": f"The X-Powered-By header discloses backend technology: '{powered_by}'.",
                "evidence": f"X-Powered-By: {powered_by}",
                "remediation": "Remove the X-Powered-By header from application responses.",
            })

        # 7. Cookie Security Flags
        for cookie_name, cookie_val in resp.cookies.items():
            # Check Set-Cookie headers
            raw_cookies = resp.headers.get_list("set-cookie") if hasattr(resp.headers, "get_list") else [resp.headers.get("set-cookie", "")]
            for raw_c in raw_cookies:
                if not raw_c or cookie_name not in raw_c:
                    continue
                lower_c = raw_c.lower()
                if "httponly" not in lower_c:
                    findings.append({
                        "title": f"Cookie '{cookie_name}' Missing HttpOnly Flag",
                        "vulnerability_type": "COOKIE_MISSING_HTTPONLY",
                        "severity": "MEDIUM",
                        "confidence": "CERTAIN",
                        "affected_url": target_url,
                        "description": f"The cookie '{cookie_name}' is set without the HttpOnly attribute, making it accessible to client-side scripts.",
                        "evidence": f"Set-Cookie: {raw_c}",
                        "remediation": "Set HttpOnly flag on all session and sensitive cookies.",
                    })
                if scheme == "https" and "secure" not in lower_c:
                    findings.append({
                        "title": f"Cookie '{cookie_name}' Missing Secure Flag",
                        "vulnerability_type": "COOKIE_MISSING_SECURE",
                        "severity": "MEDIUM",
                        "confidence": "CERTAIN",
                        "affected_url": target_url,
                        "description": f"The cookie '{cookie_name}' is transmitted over HTTPS without the Secure flag.",
                        "evidence": f"Set-Cookie: {raw_c}",
                        "remediation": "Add the 'Secure' attribute to ensure cookies are only sent over encrypted connections.",
                    })
                if "samesite" not in lower_c:
                    findings.append({
                        "title": f"Cookie '{cookie_name}' Missing SameSite Attribute",
                        "vulnerability_type": "COOKIE_MISSING_SAMESITE",
                        "severity": "LOW",
                        "confidence": "CERTAIN",
                        "affected_url": target_url,
                        "description": f"The cookie '{cookie_name}' lacks SameSite attribute, which protects against Cross-Site Request Forgery (CSRF).",
                        "evidence": f"Set-Cookie: {raw_c}",
                        "remediation": "Set 'SameSite=Lax' or 'SameSite=Strict' on sensitive cookies.",
                    })

        # 8. CORS Configuration Check
        test_client = httpx.Client(timeout=5.0, verify=False)
        try:
            cors_resp = test_client.get(
                target_url,
                headers={"Origin": "https://attacker-controlled.example.com"},
            )
            cors_headers = {k.lower(): v for k, v in cors_resp.headers.items()}
            acao = cors_headers.get("access-control-allow-origin", "")
            acac = cors_headers.get("access-control-allow-credentials", "").lower()

            if acao == "*":
                findings.append({
                    "title": "CORS Policy Allows Wildcard Origin",
                    "vulnerability_type": "CORS_MISCONFIGURATION",
                    "severity": "LOW",
                    "confidence": "HIGH",
                    "affected_url": target_url,
                    "description": "Access-Control-Allow-Origin is set to wildcard '*', allowing any site to access responses.",
                    "evidence": f"Access-Control-Allow-Origin: {acao}",
                    "remediation": "Restrict Access-Control-Allow-Origin to trusted origins.",
                })
            elif "attacker-controlled.example.com" in acao:
                findings.append({
                    "title": "CORS Arbitrary Origin Reflection",
                    "vulnerability_type": "CORS_MISCONFIGURATION",
                    "severity": "HIGH" if acac == "true" else "MEDIUM",
                    "confidence": "CERTAIN",
                    "affected_url": target_url,
                    "description": "The application dynamically reflects arbitrary Origin headers in Access-Control-Allow-Origin.",
                    "evidence": f"Origin: https://attacker-controlled.example.com\nAccess-Control-Allow-Origin: {acao}\nAccess-Control-Allow-Credentials: {acac}",
                    "remediation": "Validate incoming Origin against a strict server-side whitelist.",
                })
        except Exception as exc:
            logger.debug(f"CORS probe skipped: {exc}")
        finally:
            test_client.close()

        return findings

    def _run_safe_local_checks(
        self,
        target_url: str,
        allowed_paths: Optional[str] = None,
        request_budget: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Runs non-destructive checks:
        - HTTP method enumeration (OPTIONS, TRACE)
        - Common sensitive path detection (/robots.txt, /.git/HEAD check, /api/docs)
        Strictly bounded by request_budget.
        """
        findings: List[Dict[str, Any]] = []
        client = httpx.Client(timeout=5.0, verify=False, follow_redirects=False)

        requests_used = 0

        try:
            # 1. HTTP Method Enumeration
            if requests_used < request_budget:
                requests_used += 1
                try:
                    opt_resp = client.options(target_url)
                    allow_header = opt_resp.headers.get("allow", "").upper()
                    if "TRACE" in allow_header:
                        findings.append({
                            "title": "HTTP TRACE Method Enabled",
                            "vulnerability_type": "INSECURE_HTTP_METHOD",
                            "severity": "LOW",
                            "confidence": "CERTAIN",
                            "affected_url": target_url,
                            "description": "The HTTP TRACE method is enabled on the server, which can be leveraged for Cross-Site Tracing (XST).",
                            "evidence": f"Allow: {allow_header}",
                            "remediation": "Disable HTTP TRACE and TRACK methods on the web server.",
                        })
                except Exception as exc:
                    logger.debug(f"OPTIONS method probe failed: {exc}")

            # 2. Sensitive Local Lab Endpoints Discovery (Canary checks)
            canary_paths = [
                ("/robots.txt", "Robots.txt Information File"),
                ("/docs", "FastAPI / Swagger Documentation Exposure"),
                ("/redoc", "ReDoc Documentation Exposure"),
                ("/openapi.json", "OpenAPI Schema Exposure"),
                ("/.env", "Environment File Exposure Check"),
            ]

            parsed_base = urlparse(target_url)
            base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

            for path, check_title in canary_paths:
                if requests_used >= request_budget:
                    break

                if not validate_path_allowed(path, allowed_paths):
                    continue

                test_url = urljoin(base_origin, path)
                requests_used += 1

                try:
                    chk_resp = client.get(test_url)
                    # Check for .env exposure
                    if path == "/.env" and chk_resp.status_code == 200:
                        content_sample = chk_resp.text[:200]
                        if "=" in content_sample and ("KEY" in content_sample or "SECRET" in content_sample or "DATABASE" in content_sample):
                            findings.append({
                                "title": "Exposed Environment Configuration (.env)",
                                "vulnerability_type": "SENSITIVE_DATA_EXPOSURE",
                                "severity": "CRITICAL",
                                "confidence": "CERTAIN",
                                "affected_url": test_url,
                                "description": "The .env file containing environment credentials is publicly accessible.",
                                "evidence": f"HTTP {chk_resp.status_code}\nSample: {content_sample[:100]}",
                                "remediation": "Configure web server to deny access to hidden files and .env files.",
                            })
                    # Check for API docs exposure
                    elif path in ("/docs", "/openapi.json") and chk_resp.status_code == 200:
                        findings.append({
                            "title": f"Public API Documentation Exposed ({path})",
                            "vulnerability_type": "INFORMATION_DISCLOSURE",
                            "severity": "LOW",
                            "confidence": "HIGH",
                            "affected_url": test_url,
                            "description": f"Interactive API documentation is accessible at {path}. While useful for development, production endpoints should restrict access.",
                            "evidence": f"HTTP {chk_resp.status_code} at {test_url}",
                            "remediation": "Disable or restrict access to interactive documentation in production environments.",
                        })
                except Exception as exc:
                    logger.debug(f"Canary path probe {path} failed: {exc}")

        finally:
            client.close()

        return findings

    def _run_deep_eye_subprocess(
        self,
        target_url: str,
        timeout_seconds: int = 60,
    ) -> tuple[List[Dict[str, Any]], str]:
        """
        Invokes Deep Eye CLI safely with controlled arguments and safe temporary config.
        """
        temp_dir = tempfile.mkdtemp(prefix="deep_eye_safe_")
        config_path = os.path.join(temp_dir, "config.yaml")

        safe_config: Dict[str, Any] = {
            "scanner": {
                "target_url": target_url,
                "default_depth": 1,
                "default_threads": 2,
                "ai_provider": "none",
                "enable_recon": False,
                "quick_scan": True,
            },
            "ai_providers": {
                "openai": {"enabled": False},
                "claude": {"enabled": False},
                "grok": {"enabled": False},
                "ollama": {"enabled": False},
            },
        }

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(safe_config, f)

            cmd = [
                self.python_path,
                self.script_path,
                "-u", target_url,
                "-c", config_path,
                "--no-banner",
            ]

            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False,
                cwd=self.root_path,
            )

            stdout = res.stdout or ""
            stderr = res.stderr or ""
            combined = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"

            findings: List[Dict[str, Any]] = []
            return findings, combined
        except subprocess.TimeoutExpired:
            return [], "Deep Eye execution timed out."
        except Exception as exc:
            return [], f"Subprocess error: {exc}"
        finally:
            try:
                if os.path.exists(config_path):
                    os.remove(config_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except Exception:
                pass


# Global singleton adapter instance
deep_eye_adapter = DeepEyeAdapter()

