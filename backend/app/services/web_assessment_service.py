"""
Web Application Security Assessment Service.
Coordinates target registration, assessment lifecycle, finding persistence, deduplication,
and incident correlation for KAWAL SIBER.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session

from app.integrations.deep_eye.adapter import deep_eye_adapter
from app.integrations.deep_eye.validator import (
    parse_and_validate_target_url,
    validate_path_allowed,
    TargetOutOfScopeError,
    InvalidTargetURLError,
)
from app.models import (
    Asset,
    Incident,
    ScanScope,
    WebAssessment,
    WebFinding,
    WebTarget,
)
from app.services.scope_validator import validate_scope_active

logger = logging.getLogger(__name__)


def map_vuln_to_attack_type(vuln_type: str, title: str) -> str:
    """Maps web vulnerability types to Incident attack_type enum."""
    combined = f"{vuln_type} {title}".upper()
    if "SQL" in combined:
        return "SQL_INJECTION"
    if "XSS" in combined or "SCRIPT" in combined:
        return "XSS"
    if "BRUTE" in combined or "AUTH" in combined:
        return "BRUTE_FORCE"
    return "ANOMALY_TRAFFIC"


class WebAssessmentService:
    """Service handling all Web Security Assessment operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_web_target(
        self,
        name: str,
        target_url: str,
        asset_id: Optional[int] = None,
        scope_id: Optional[int] = None,
        allowed_paths: Optional[str] = "/*",
        authorization_reference: Optional[str] = None,
        enabled: bool = True,
    ) -> WebTarget:
        """
        Validates target parameters and persists a new WebTarget.
        """
        # If asset_id is provided, verify asset existence
        asset = None
        extra_hosts = set()
        if asset_id:
            asset = self.db.get(Asset, asset_id)
            if not asset:
                raise InvalidTargetURLError(f"Referenced Asset ID {asset_id} does not exist.")
            extra_hosts.add(asset.target_ip)

        # If scope_id is provided, verify scope is active
        if scope_id:
            scope = self.db.get(ScanScope, scope_id)
            if not scope:
                raise TargetOutOfScopeError(f"Referenced ScanScope ID {scope_id} does not exist.")
            validate_scope_active(scope.enabled, scope.expires_at)

        # Validate URL and resolve components
        try:
            protocol, hostname, port, normalized_url = parse_and_validate_target_url(
                target_url=target_url,
                extra_allowed_hosts=extra_hosts,
            )
        except TargetOutOfScopeError as exc:
            if not asset_id:
                raise TargetOutOfScopeError(
                    f"{exc} To authorize a non-localhost host, register it as an "
                    "Asset first (Manajemen Aset) and link it via asset_id."
                ) from exc
            raise

        web_target = WebTarget(
            asset_id=asset_id,
            name=name.strip(),
            target_url=normalized_url,
            hostname=hostname,
            protocol=protocol,
            port=port,
            allowed_paths=allowed_paths or "/*",
            scope_id=scope_id,
            enabled=enabled,
            authorization_reference=authorization_reference,
        )

        self.db.add(web_target)
        self.db.commit()
        self.db.refresh(web_target)
        return web_target

    def enqueue_assessment(
        self,
        web_target_id: int,
        assessment_profile: str = "PASSIVE",
    ) -> WebAssessment:
        """
        Validates target authorization and creates a PENDING assessment job.
        """
        target = self.db.get(WebTarget, web_target_id)
        if not target:
            raise InvalidTargetURLError(f"Web target ID {web_target_id} not found.")

        if not target.enabled:
            raise TargetOutOfScopeError(f"Web target '{target.name}' is currently disabled.")

        # If bound to a scan scope, verify scope validity
        if target.scope_id:
            scope = self.db.get(ScanScope, target.scope_id)
            if scope:
                validate_scope_active(scope.enabled, scope.expires_at)

        profile = assessment_profile.upper().strip()
        if profile not in ("PASSIVE", "SAFE_LOCAL"):
            profile = "PASSIVE"

        assessment = WebAssessment(
            web_target_id=target.id,
            assessment_profile=profile,
            status="PENDING",
            tool_name="Deep Eye",
            tool_version=deep_eye_adapter.get_version(),
        )

        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        return assessment

    def execute_assessment_job(self, assessment_id: int) -> WebAssessment:
        """
        Executes a pending assessment, records findings, and correlates incidents.
        """
        assessment = self.db.get(WebAssessment, assessment_id)
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found.")

        target = self.db.get(WebTarget, assessment.web_target_id)
        if not target:
            assessment.status = "FAILED"
            assessment.error_message = "Associated WebTarget not found."
            self.db.commit()
            return assessment

        assessment.status = "RUNNING"
        assessment.started_at = datetime.now(timezone.utc)
        self.db.commit()

        try:
            # Re-derive authorization context at execution time: only the
            # asset actually linked to this target may extend scope —
            # mirrors create_web_target() authorization, nothing broader.
            extra_hosts: set = set()
            if target.asset_id and target.asset and target.asset.target_ip:
                extra_hosts.add(target.asset.target_ip)

            exec_result = deep_eye_adapter.execute_assessment(
                target_url=target.target_url,
                profile=assessment.assessment_profile,
                allowed_paths=target.allowed_paths,
                web_target_id=target.id,
                extra_allowed_hosts=extra_hosts or None,
            )

            if not exec_result.success:
                assessment.status = "FAILED"
                assessment.error_message = exec_result.error_message
                assessment.completed_at = datetime.now(timezone.utc)
                assessment.duration_ms = exec_result.duration_ms
                self.db.commit()
                return assessment

            # Process and persist findings
            now = datetime.now(timezone.utc)
            crit_cnt = 0
            high_cnt = 0
            med_cnt = 0
            low_cnt = 0

            persisted_findings: List[WebFinding] = []

            for item in exec_result.findings:
                fp = item["fingerprint"]
                sev = item["severity"]

                if sev == "CRITICAL":
                    crit_cnt += 1
                elif sev == "HIGH":
                    high_cnt += 1
                elif sev == "MEDIUM":
                    med_cnt += 1
                elif sev == "LOW":
                    low_cnt += 1

                # Check if finding already exists (deduplication)
                existing = self.db.execute(
                    select(WebFinding).where(WebFinding.fingerprint == fp)
                ).scalars().first()

                if existing:
                    existing.last_seen = now
                    existing.evidence = item.get("evidence") or existing.evidence
                    existing.confidence = item.get("confidence") or existing.confidence
                    persisted_findings.append(existing)
                else:
                    new_finding = WebFinding(
                        assessment_id=assessment.id,
                        web_target_id=target.id,
                        title=item["title"],
                        vulnerability_type=item["vulnerability_type"],
                        severity=sev,
                        confidence=item.get("confidence", "MEDIUM"),
                        finding_status=item.get("finding_status", "UNVERIFIED"),
                        affected_url=item["affected_url"],
                        description=item["description"],
                        evidence=item.get("evidence"),
                        remediation=item.get("remediation"),
                        reference=item.get("reference"),
                        fingerprint=fp,
                        first_seen=now,
                        last_seen=now,
                    )
                    self.db.add(new_finding)
                    persisted_findings.append(new_finding)

            # Update assessment record
            assessment.status = "COMPLETED"
            assessment.completed_at = now
            assessment.duration_ms = exec_result.duration_ms
            assessment.total_findings = len(exec_result.findings)
            assessment.critical_count = crit_cnt
            assessment.high_count = high_cnt
            assessment.medium_count = med_cnt
            assessment.low_count = low_cnt
            assessment.output_reference = f"Parsed {len(exec_result.findings)} findings."
            assessment.error_message = None

            # Correlate incidents for Critical and High findings
            self._correlate_findings_to_incidents(
                target=target,
                findings=persisted_findings,
            )

            self.db.commit()
            self.db.refresh(assessment)
            return assessment

        except Exception as exc:
            logger.exception(f"Assessment job {assessment_id} execution error: {exc}")
            assessment.status = "FAILED"
            assessment.error_message = str(exc)
            assessment.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            return assessment

    def _correlate_findings_to_incidents(
        self,
        target: WebTarget,
        findings: List[WebFinding],
    ) -> None:
        """
        Maps CRITICAL and HIGH findings to the monitored Asset's incidents table.
        Prevents duplicate storms by checking unmitigated incidents within 60 minutes.
        """
        if not target.asset_id:
            # Try to resolve asset by hostname / port
            matched = self.db.execute(
                select(Asset).where(
                    Asset.target_ip == target.hostname,
                    Asset.port == target.port,
                )
            ).scalars().first()
            if not matched:
                return
            target_asset = matched
        else:
            target_asset = self.db.get(Asset, target.asset_id)
            if not target_asset:
                return

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=60)

        for finding in findings:
            if finding.severity not in ("CRITICAL", "HIGH"):
                continue

            attack_type = map_vuln_to_attack_type(finding.vulnerability_type, finding.title)

            # Deduplication: check for recent unmitigated incident on this asset with same attack_type
            dup = self.db.execute(
                select(Incident).where(
                    Incident.asset_id == target_asset.id,
                    Incident.attack_type == attack_type,
                    Incident.is_mitigated.is_(False),
                    Incident.timestamp >= cutoff,
                )
            ).scalars().first()

            if dup:
                logger.debug(f"Incident duplicate suppressed for asset {target_asset.id} / {attack_type}")
                continue

            # Create new correlated incident
            incident = Incident(
                asset_id=target_asset.id,
                timestamp=now,
                source_ip="127.0.0.1",
                attack_type=attack_type,
                payload=finding.evidence[:1000] if finding.evidence else None,
                severity=finding.severity,
                ai_analysis=f"Deep Eye Web Security Assessment detected {finding.title} on {finding.affected_url}. "
                            f"Remediation: {finding.remediation or 'Review application configuration.'}",
                is_mitigated=False,
            )
            self.db.add(incident)

            # Conditionally elevate asset security status
            if finding.severity == "CRITICAL":
                target_asset.status = "UNDER_ATTACK"
            elif finding.severity == "HIGH" and target_asset.status not in ("UNDER_ATTACK", "DOWN"):
                target_asset.status = "WARNING"

