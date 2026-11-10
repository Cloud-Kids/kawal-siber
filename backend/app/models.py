"""
models.py — SQLAlchemy 2.x ORM models for KAWAL SIBER.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Constants (keep in sync with schemas.py)
# ---------------------------------------------------------------------------
VALID_ASSET_STATUSES = ("UNKNOWN", "SAFE", "WARNING", "UNDER_ATTACK", "DOWN")
VALID_AVAILABILITY_STATUSES = ("UNKNOWN", "UP", "DOWN")
VALID_SCAN_JOB_STATUSES = ("PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED")
VALID_ATTACK_TYPES = (
    "BRUTE_FORCE",
    "SQL_INJECTION",
    "XSS",
    "PORT_SCAN",
    "ANOMALY_TRAFFIC",
)
VALID_SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "PENDING")

# Phase 5 constants
VALID_LIFECYCLE_STATUSES = (
    "OPEN", "ACKNOWLEDGED", "INVESTIGATING", "MITIGATED", "RESOLVED", "FALSE_POSITIVE"
)
VALID_TRIAGE_STATUSES = (
    "PENDING", "RUNNING", "COMPLETED", "FAILED", "REQUIRES_REVIEW"
)
VALID_EVIDENCE_SOURCE_TYPES = (
    "SURICATA_EVENT", "WEB_FINDING", "NMAP_RESULT", "MANUAL_EVIDENCE"
)

# Phase 6 constants
VALID_REPORT_TYPES = (
    "EXECUTIVE", "TECHNICAL", "ASSESSMENT", "OPERATIONS", "AI_INTELLIGENCE"
)
VALID_REPORT_FORMATS = ("PDF", "HTML", "JSON", "CSV")
VALID_REPORT_STATUSES = ("PENDING", "RUNNING", "COMPLETED", "FAILED")

_lifecycle_status_list = "', '".join(VALID_LIFECYCLE_STATUSES)
_triage_status_list = "', '".join(VALID_TRIAGE_STATUSES)
_evidence_source_type_list = "', '".join(VALID_EVIDENCE_SOURCE_TYPES)
_report_type_list = "', '".join(VALID_REPORT_TYPES)
_report_format_list = "', '".join(VALID_REPORT_FORMATS)
_report_status_list = "', '".join(VALID_REPORT_STATUSES)

_asset_status_list = "', '".join(VALID_ASSET_STATUSES)
_availability_status_list = "', '".join(VALID_AVAILABILITY_STATUSES)
_scan_job_status_list = "', '".join(VALID_SCAN_JOB_STATUSES)
_attack_type_list = "', '".join(VALID_ATTACK_TYPES)
_severity_list = "', '".join(VALID_SEVERITIES)


# ---------------------------------------------------------------------------
# ScanScope model
# ---------------------------------------------------------------------------
class ScanScope(Base):
    """
    Represents an authorized network scanning scope.
    Scanning is only permitted against targets within active, non-expired scopes.
    """

    __tablename__ = "scan_scopes"
    __table_args__ = (
        CheckConstraint("length(cidr) > 0", name="ck_scan_scopes_cidr_non_empty"),
        CheckConstraint(
            "length(authorization_reference) > 0",
            name="ck_scan_scopes_auth_ref_non_empty",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cidr: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authorization_reference: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    assets: Mapped[List["Asset"]] = relationship(
        "Asset",
        back_populates="scope",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<ScanScope id={self.id} name={self.name!r} cidr={self.cidr} enabled={self.enabled}>"


# ---------------------------------------------------------------------------
# Asset model
# ---------------------------------------------------------------------------
class Asset(Base):
    """Represents a monitored network asset."""

    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("port >= 1 AND port <= 65535", name="ck_assets_port_range"),
        CheckConstraint(
            f"status IN ('{_asset_status_list}')",
            name="ck_assets_status_valid",
        ),
        CheckConstraint(
            f"availability_status IN ('{_availability_status_list}')",
            name="ck_assets_availability_status_valid",
        ),
        CheckConstraint(
            "response_time_ms IS NULL OR response_time_ms >= 0",
            name="ck_assets_response_time_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_ip: Mapped[str] = mapped_column(String(253), nullable=False, index=True)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNKNOWN", index=True
    )
    availability_status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="UNKNOWN", index=True
    )
    scope_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("scan_scopes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_scanned: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    scope: Mapped[Optional["ScanScope"]] = relationship(
        "ScanScope",
        back_populates="assets",
        lazy="select",
    )
    incidents: Mapped[List["Incident"]] = relationship(
        "Incident",
        back_populates="asset",
        lazy="select",
    )
    scan_jobs: Mapped[List["ScanJob"]] = relationship(
        "ScanJob",
        back_populates="asset",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Asset id={self.id} name={self.name!r} status={self.status} "
            f"availability={self.availability_status}>"
        )


# ---------------------------------------------------------------------------
# Incident model
# ---------------------------------------------------------------------------
class Incident(Base):
    """Represents a detected security incident linked to an asset."""

    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            f"attack_type IN ('{_attack_type_list}')",
            name="ck_incidents_attack_type_valid",
        ),
        CheckConstraint(
            f"severity IN ('{_severity_list}')",
            name="ck_incidents_severity_valid",
        ),
        CheckConstraint(
            "payload IS NULL OR length(payload) <= 65536",
            name="ck_incidents_payload_length",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    source_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    attack_type: Mapped[str] = mapped_column(String(30), nullable=False)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    ai_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_mitigated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Phase 5: Lifecycle tracking
    lifecycle_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OPEN", index=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    investigated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="incidents")
    triage_runs: Mapped[List["AITriageRun"]] = relationship(
        "AITriageRun",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="select",
    )
    evidence_items: Mapped[List["IncidentEvidence"]] = relationship(
        "IncidentEvidence",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="select",
    )
    timeline_events: Mapped[List["IncidentTimelineEvent"]] = relationship(
        "IncidentTimelineEvent",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Incident id={self.id} asset_id={self.asset_id} "
            f"severity={self.severity} attack_type={self.attack_type} "
            f"lifecycle={self.lifecycle_status}>"
        )


# ---------------------------------------------------------------------------
# ScanJob model
# ---------------------------------------------------------------------------
class ScanJob(Base):
    """
    Represents an authorized network discovery / port scanning job.
    Managed via an atomic SQLite job queue.
    """

    __tablename__ = "scan_jobs"
    __table_args__ = (
        CheckConstraint(
            f"status IN ('{_scan_job_status_list}')",
            name="ck_scan_jobs_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resolved_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    scanner_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="scan_jobs")
    results: Mapped[List["ScanResult"]] = relationship(
        "ScanResult",
        back_populates="scan_job",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<ScanJob id={self.id} asset_id={self.asset_id} status={self.status}>"


# ---------------------------------------------------------------------------
# ScanResult model
# ---------------------------------------------------------------------------
class ScanResult(Base):
    """
    Represents structured port scan result findings extracted from Nmap XML.
    """

    __tablename__ = "scan_results"
    __table_args__ = (
        CheckConstraint("port >= 1 AND port <= 65535", name="ck_scan_results_port_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("scan_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    protocol: Mapped[str] = mapped_column(String(10), default="tcp", nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)  # open, closed, filtered
    service_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    product: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extra_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    scan_job: Mapped["ScanJob"] = relationship("ScanJob", back_populates="results")

    def __repr__(self) -> str:
        return (
            f"<ScanResult id={self.id} job_id={self.scan_job_id} "
            f"port={self.port}/{self.protocol} state={self.state}>"
        )


# ---------------------------------------------------------------------------
# Phase 3: PcapAnalysis model
# ---------------------------------------------------------------------------
VALID_PCAP_STATUSES = ("PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED")
_pcap_status_list = "', '".join(VALID_PCAP_STATUSES)


class PcapAnalysis(Base):
    """
    Represents an offline PCAP analysis execution via Suricata IDS.
    """

    __tablename__ = "pcap_analyses"
    __table_args__ = (
        CheckConstraint(
            f"status IN ('{_pcap_status_list}')",
            name="ck_pcap_analyses_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    alert_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    events: Mapped[List["SecurityEvent"]] = relationship(
        "SecurityEvent",
        back_populates="pcap_analysis",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<PcapAnalysis id={self.id} file={self.filename!r} status={self.status}>"


# ---------------------------------------------------------------------------
# Phase 3: SecurityEvent model
# ---------------------------------------------------------------------------
class SecurityEvent(Base):
    """
    Structured Suricata EVE JSON event record (alerts, anomalies, protocols, flows).
    """

    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    pcap_analysis_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("pcap_analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    asset_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)
    destination_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)
    source_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    destination_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    protocol: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    signature_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    signature: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    severity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    raw_event: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # sanitized JSON
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    pcap_analysis: Mapped[Optional["PcapAnalysis"]] = relationship(
        "PcapAnalysis", back_populates="events"
    )
    asset: Mapped[Optional["Asset"]] = relationship("Asset")

    def __repr__(self) -> str:
        return (
            f"<SecurityEvent id={self.id} event_id={self.event_id!r} "
            f"type={self.event_type} sig={self.signature!r}>"
        )


# ---------------------------------------------------------------------------
# Phase 4: Web Security Models (Deep Eye Integration)
# ---------------------------------------------------------------------------
VALID_WEB_ASSESSMENT_PROFILES = ("PASSIVE", "SAFE_LOCAL")
VALID_WEB_ASSESSMENT_STATUSES = ("PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED")
VALID_WEB_FINDING_SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL")
VALID_WEB_FINDING_STATUSES = ("UNVERIFIED", "NEEDS_REVIEW", "CONFIRMED", "FALSE_POSITIVE", "ACCEPTED_RISK")

_web_profile_list = "', '".join(VALID_WEB_ASSESSMENT_PROFILES)
_web_assessment_status_list = "', '".join(VALID_WEB_ASSESSMENT_STATUSES)
_web_finding_severity_list = "', '".join(VALID_WEB_FINDING_SEVERITIES)
_web_finding_status_list = "', '".join(VALID_WEB_FINDING_STATUSES)


class WebTarget(Base):
    """Represents an authorized target web application or API service."""

    __tablename__ = "web_targets"
    __table_args__ = (
        CheckConstraint("port >= 1 AND port <= 65535", name="ck_web_targets_port_range"),
        CheckConstraint("protocol IN ('http', 'https')", name="ck_web_targets_protocol_valid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    protocol: Mapped[str] = mapped_column(String(10), nullable=False, default="http")
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    allowed_paths: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="/*")
    scope_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("scan_scopes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    authorization_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )

    # Relationships
    asset: Mapped[Optional["Asset"]] = relationship("Asset")
    scope: Mapped[Optional["ScanScope"]] = relationship("ScanScope")
    assessments: Mapped[List["WebAssessment"]] = relationship(
        "WebAssessment",
        back_populates="web_target",
        cascade="all, delete-orphan",
        lazy="select",
    )
    findings: Mapped[List["WebFinding"]] = relationship(
        "WebFinding",
        back_populates="web_target",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<WebTarget id={self.id} name={self.name!r} url={self.target_url!r}>"


class WebAssessment(Base):
    """Represents a Web Application Security Assessment execution."""

    __tablename__ = "web_assessments"
    __table_args__ = (
        CheckConstraint(
            f"assessment_profile IN ('{_web_profile_list}')",
            name="ck_web_assessments_profile_valid",
        ),
        CheckConstraint(
            f"status IN ('{_web_assessment_status_list}')",
            name="ck_web_assessments_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    web_target_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("web_targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_profile: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PASSIVE"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), default="Deep Eye", nullable=False)
    tool_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    high_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    medium_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_reference: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    web_target: Mapped["WebTarget"] = relationship("WebTarget", back_populates="assessments")
    findings: Mapped[List["WebFinding"]] = relationship(
        "WebFinding",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<WebAssessment id={self.id} target_id={self.web_target_id} "
            f"profile={self.assessment_profile} status={self.status}>"
        )


class WebFinding(Base):
    """Represents a normalized web vulnerability finding from assessment."""

    __tablename__ = "web_findings"
    __table_args__ = (
        CheckConstraint(
            f"severity IN ('{_web_finding_severity_list}')",
            name="ck_web_findings_severity_valid",
        ),
        CheckConstraint(
            f"finding_status IN ('{_web_finding_status_list}')",
            name="ck_web_findings_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("web_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    web_target_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("web_targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    vulnerability_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    finding_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNVERIFIED", index=True
    )
    affected_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remediation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    assessment: Mapped["WebAssessment"] = relationship("WebAssessment", back_populates="findings")
    web_target: Mapped["WebTarget"] = relationship("WebTarget", back_populates="findings")

    def __repr__(self) -> str:
        return f"<WebFinding id={self.id} vuln={self.vulnerability_type} sev={self.severity}>"


# ---------------------------------------------------------------------------
# Phase 5: AI Triage & Incident Correlation Models
# ---------------------------------------------------------------------------


class AITriageRun(Base):
    """
    Represents a single AI or rule-based triage analysis run for an Incident.
    Stores input fingerprint, provider used, result JSON, and confidence score.
    """

    __tablename__ = "ai_triage_runs"
    __table_args__ = (
        CheckConstraint(
            f"status IN ('{_triage_status_list}')",
            name="ck_ai_triage_runs_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="v1"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", index=True
    )
    input_fingerprint: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="triage_runs")

    def __repr__(self) -> str:
        return (
            f"<AITriageRun id={self.id} incident_id={self.incident_id} "
            f"provider={self.provider} status={self.status}>"
        )


class IncidentEvidence(Base):
    """
    Traceable evidence record linking an Incident to a specific security data source.
    Deduplication enforced via UNIQUE(incident_id, source_type, source_record_id).
    """

    __tablename__ = "incident_evidence"
    __table_args__ = (
        CheckConstraint(
            f"source_type IN ('{_evidence_source_type_list}')",
            name="ck_incident_evidence_source_type_valid",
        ),
        Index(
            "uq_incident_evidence_incident_source",
            "incident_id",
            "source_type",
            "source_record_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_record_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    relationship_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    evidence_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="evidence_items")

    def __repr__(self) -> str:
        return (
            f"<IncidentEvidence id={self.id} incident_id={self.incident_id} "
            f"source={self.source_type} record_id={self.source_record_id}>"
        )


class IncidentTimelineEvent(Base):
    """
    Ordered log of significant events in the lifecycle of an Incident.
    Used to build the full incident timeline visible to operators.
    """

    __tablename__ = "incident_timeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    source_record_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="timeline_events")

    def __repr__(self) -> str:
        return (
            f"<IncidentTimelineEvent id={self.id} incident_id={self.incident_id} "
            f"type={self.event_type}>"
        )



# ---------------------------------------------------------------------------
# Phase 6: Automated Security Reporting Models
# ---------------------------------------------------------------------------


class GeneratedReport(Base):
    """
    Represents an immutable, audited security report generated by the reporting engine.
    Stores metadata, period bounds, generation status, file path, and SHA-256 checksum.
    """

    __tablename__ = "generated_reports"
    __table_args__ = (
        CheckConstraint(
            f"generation_status IN ('{_report_status_list}')",
            name="ck_generated_reports_status_valid",
        ),
        CheckConstraint(
            f"report_type IN ('{_report_type_list}')",
            name="ck_generated_reports_type_valid",
        ),
        CheckConstraint(
            f"format IN ('{_report_format_list}')",
            name="ck_generated_reports_format_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_uuid: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sha256_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    generation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", index=True
    )
    generated_by: Mapped[str] = mapped_column(String(100), default="Operator", nullable=False)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parameters_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # --- Phase 6 Addendum fields ---
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    job_priority: Mapped[int] = mapped_column(Integer, default=5, server_default="5", nullable=False)
    last_downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    audit_log_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    template_version: Mapped[str] = mapped_column(String(20), default="1.0", server_default="1.0", nullable=False)
    data_schema_version: Mapped[str] = mapped_column(String(20), default="1.0", server_default="1.0", nullable=False)
    source_record_refs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<GeneratedReport id={self.id} report_id={self.report_id!r} "
            f"type={self.report_type} format={self.format} status={self.generation_status}>"
        )


# ---------------------------------------------------------------------------
# Phase 6 Final Refinement: Append-Only Report Audit Event Model
# ---------------------------------------------------------------------------
class ReportAuditEvent(Base):
    """
    Append-only report audit event record with cryptographic hash chaining.
    Each event stores SHA-256(previous_event_hash | report_id | event_type | actor | timestamp | details).

    DISCLAIMER: This table provides application-level append-only hash chaining.
    It does NOT provide absolute physical immutability without dedicated OS/DB
    WORM filesystem or hardware security module (HSM) protections.
    """

    __tablename__ = "report_audit_events"
    __table_args__ = (
        Index("ix_report_audit_events_report_id_id", "report_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), default="system", server_default="system", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    event_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    previous_event_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="GENESIS")
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<ReportAuditEvent id={self.id} report_id={self.report_id!r} "
            f"type={self.event_type} hash={self.event_hash[:8]}...>"
        )
