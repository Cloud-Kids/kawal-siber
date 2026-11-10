"""
schemas.py — Pydantic 2.x request/response schemas for KAWAL SIBER.
"""
from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AssetStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    SAFE = "SAFE"
    WARNING = "WARNING"
    UNDER_ATTACK = "UNDER_ATTACK"
    DOWN = "DOWN"


class AvailabilityStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    UP = "UP"
    DOWN = "DOWN"


class ScanJobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AttackType(str, Enum):
    BRUTE_FORCE = "BRUTE_FORCE"
    SQL_INJECTION = "SQL_INJECTION"
    XSS = "XSS"
    PORT_SCAN = "PORT_SCAN"
    ANOMALY_TRAFFIC = "ANOMALY_TRAFFIC"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    PENDING = "PENDING"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
# RFC 1123 hostname label pattern
_HOSTNAME_LABEL_RE = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")


def _validate_ip_or_hostname(value: str) -> str:
    """Accept a valid IPv4, IPv6, or RFC-1123 hostname."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("IP address or hostname must not be empty")

    # If it looks like an IPv4 dotted decimal (4 numeric segments separated by dots), it MUST be a valid IP!
    parts = stripped.split(".")
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        try:
            ipaddress.ip_address(stripped)
            return stripped
        except ValueError as exc:
            raise ValueError(f"{stripped!r} is not a valid IPv4 address") from exc

    # Try parsing as IP first
    try:
        ipaddress.ip_address(stripped)
        return stripped
    except ValueError:
        pass

    # Validate as hostname (RFC 1123)
    hostname = stripped.rstrip(".")
    if len(hostname) > 253:
        raise ValueError("Hostname exceeds 253 characters")
    labels = hostname.split(".")
    for label in labels:
        if not _HOSTNAME_LABEL_RE.match(label):
            raise ValueError(
                f"Invalid hostname label {label!r}; must match RFC 1123"
            )
    return stripped


def _validate_strict_ip(value: str) -> str:
    """Accept only a valid IPv4 or IPv6 address (no hostnames)."""
    stripped = value.strip()
    try:
        ipaddress.ip_address(stripped)
        return stripped
    except ValueError:
        raise ValueError(f"{stripped!r} is not a valid IP address")


def _validate_cidr(value: str) -> str:
    """Validate that the value is a valid IPv4 or IPv6 CIDR."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("CIDR must not be empty")
    try:
        net = ipaddress.ip_network(stripped, strict=False)
        return str(net)
    except ValueError as exc:
        raise ValueError(f"Invalid CIDR notation {stripped!r}: {exc}") from exc


# ---------------------------------------------------------------------------
# Scan Scope schemas
# ---------------------------------------------------------------------------

class ScanScopeCreate(BaseModel):
    """Schema for registering a new authorized scan scope."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=255)
    cidr: str = Field(..., description="Valid IPv4 or IPv6 CIDR network notation")
    description: Optional[str] = Field(default=None)
    authorization_reference: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Formal audit, ticket, or authorization reference",
    )
    enabled: bool = Field(default=True)
    expires_at: datetime = Field(
        ...,
        description="UTC expiration timestamp for authorized testing",
    )

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("name must not be empty or whitespace-only")
        return v

    @field_validator("cidr", mode="before")
    @classmethod
    def validate_cidr_field(cls, v: str) -> str:
        return _validate_cidr(v)

    @field_validator("authorization_reference", mode="before")
    @classmethod
    def strip_auth_ref(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("authorization_reference must not be empty")
        return v

    @field_validator("expires_at")
    @classmethod
    def validate_future_expiry(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc)
        target = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if target <= now:
            raise ValueError("expires_at must be in the future")
        return v


class ScanScopeUpdate(BaseModel):
    """Schema for updating a scan scope (e.g. enabling/disabling or extending expiry)."""

    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    authorization_reference: Optional[str] = Field(default=None, min_length=1, max_length=255)
    enabled: Optional[bool] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v


class ScanScopeResponse(BaseModel):
    """Schema returned for a scan scope resource."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    cidr: str
    description: Optional[str]
    authorization_reference: str
    enabled: bool
    expires_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Asset schemas
# ---------------------------------------------------------------------------

class AssetCreate(BaseModel):
    """Schema for creating a new asset."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=255)
    target_ip: str = Field(..., description="Valid IPv4, IPv6, or RFC-1123 hostname")
    port: int = Field(..., ge=1, le=65535)
    status: AssetStatus = Field(default=AssetStatus.UNKNOWN)
    availability_status: AvailabilityStatus = Field(default=AvailabilityStatus.UNKNOWN)
    scope_id: Optional[int] = Field(default=None, gt=0)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("name must not be empty or whitespace-only")
        return v

    @field_validator("target_ip", mode="before")
    @classmethod
    def validate_target_ip(cls, v: str) -> str:
        return _validate_ip_or_hostname(v)


class AssetUpdate(BaseModel):
    """Schema for partially updating an asset."""

    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    target_ip: Optional[str] = Field(default=None)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    status: Optional[AssetStatus] = Field(default=None)
    availability_status: Optional[AvailabilityStatus] = Field(default=None)
    scope_id: Optional[int] = Field(default=None)
    response_time_ms: Optional[float] = Field(default=None, ge=0)
    last_scanned: Optional[datetime] = Field(default=None)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("name must not be empty or whitespace-only")
        return v

    @field_validator("target_ip", mode="before")
    @classmethod
    def validate_target_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_ip_or_hostname(v)


class AssetResponse(BaseModel):
    """Schema returned for an asset resource."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    target_ip: str
    port: int
    status: str
    availability_status: str
    scope_id: Optional[int] = None
    response_time_ms: Optional[float] = None
    last_scanned: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Incident schemas
# ---------------------------------------------------------------------------

class IncidentCreate(BaseModel):
    """Schema for creating a new incident."""

    model_config = ConfigDict(from_attributes=True)

    asset_id: int = Field(..., gt=0)
    source_ip: str = Field(..., description="Valid IPv4 or IPv6 address")
    attack_type: AttackType
    payload: Optional[str] = Field(default=None, max_length=65536)
    severity: Severity
    ai_analysis: Optional[str] = Field(default=None)

    @field_validator("source_ip", mode="before")
    @classmethod
    def validate_source_ip(cls, v: str) -> str:
        return _validate_strict_ip(v)


class IncidentUpdate(BaseModel):
    """Schema for partially updating an incident (mitigated flag and analysis)."""

    model_config = ConfigDict(from_attributes=True)

    is_mitigated: Optional[bool] = Field(default=None)
    ai_analysis: Optional[str] = Field(default=None)


class IncidentResponse(BaseModel):
    """Schema returned for an incident resource."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    timestamp: datetime
    source_ip: str
    attack_type: str
    payload: Optional[str]
    severity: str
    ai_analysis: Optional[str]
    is_mitigated: bool
    # Phase 5: lifecycle fields (default for backward compat with existing records)
    lifecycle_status: str = "OPEN"
    acknowledged_at: Optional[datetime] = None
    investigated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Scan Result schemas
# ---------------------------------------------------------------------------

class ScanResultResponse(BaseModel):
    """Schema representing an individual port discovery finding."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_job_id: int
    protocol: str
    port: int
    state: str
    service_name: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    extra_info: Optional[str] = None
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Scan Job schemas
# ---------------------------------------------------------------------------

class ScanJobCreate(BaseModel):
    """Schema to request a scan job for an asset."""

    model_config = ConfigDict(from_attributes=True)

    asset_id: int = Field(..., gt=0)


class ScanJobResponse(BaseModel):
    """Schema returned for a scan job."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    resolved_ip: Optional[str] = None
    scanner_version: Optional[str] = None
    attempts: int
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    results: List[ScanResultResponse] = []


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginatedIncidents(BaseModel):
    """Paginated list of incidents."""

    model_config = ConfigDict(from_attributes=True)

    items: List[IncidentResponse]
    total: int
    page: int
    page_size: int


class PaginatedScanJobs(BaseModel):
    """Paginated list of scan jobs."""

    model_config = ConfigDict(from_attributes=True)

    items: List[ScanJobResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Health-check response schema."""

    status: str
    database: str
    version: str


# ---------------------------------------------------------------------------
# Phase 3: Suricata & PCAP Monitoring Schemas
# ---------------------------------------------------------------------------

class PcapAnalysisCreate(BaseModel):
    """Schema for requesting a PCAP file analysis."""

    filename: str = Field(..., min_length=1, max_length=512, description="Filename within authorized storage/pcaps/")


class PcapAnalysisResponse(BaseModel):
    """Summary of a PCAP file analysis job."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_hash: str
    file_size_bytes: Optional[int] = None
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    event_count: int
    alert_count: int
    error_message: Optional[str] = None
    created_at: datetime


class SecurityEventResponse(BaseModel):
    """Schema for an individual Suricata EVE security event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    pcap_analysis_id: Optional[int] = None
    asset_id: Optional[int] = None
    timestamp: datetime
    event_type: str
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    source_port: Optional[int] = None
    destination_port: Optional[int] = None
    protocol: Optional[str] = None
    signature_id: Optional[int] = None
    signature: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[int] = None
    confidence: Optional[str] = None
    raw_event: Optional[str] = None
    created_at: datetime


class PaginatedSecurityEvents(BaseModel):
    """Paginated list of security events."""

    model_config = ConfigDict(from_attributes=True)

    items: List[SecurityEventResponse]
    total: int
    page: int
    page_size: int


class MonitoringStatisticsResponse(BaseModel):
    """Aggregated threat detection metrics and telemetry distribution."""

    model_config = ConfigDict(from_attributes=True)

    total_events: int
    total_alerts: int
    total_pcap_analyses: int
    severity_distribution: Dict[str, int]  # e.g. {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 5, "LOW": 3, "INFO": 10}
    protocol_distribution: Dict[str, int]  # e.g. {"TCP": 15, "UDP": 4, "ICMP": 2}
    event_type_distribution: Dict[str, int]  # e.g. {"alert": 8, "flow": 12, "dns": 5}
    top_signatures: List[Dict[str, Any]]
    correlated_incidents_count: int


# ---------------------------------------------------------------------------
# Phase 4: Web Security & Deep Eye Schemas
# ---------------------------------------------------------------------------

class WebTargetCreate(BaseModel):
    """Schema for creating a new authorized web assessment target."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=255)
    target_url: str = Field(..., min_length=5, max_length=1024)
    asset_id: Optional[int] = Field(default=None, gt=0)
    scope_id: Optional[int] = Field(default=None, gt=0)
    allowed_paths: Optional[str] = Field(default="/*", max_length=2000)
    authorization_reference: Optional[str] = Field(default=None, max_length=255)
    enabled: bool = Field(default=True)


class WebTargetUpdate(BaseModel):
    """Schema for updating target properties."""

    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    allowed_paths: Optional[str] = Field(default=None, max_length=2000)
    authorization_reference: Optional[str] = Field(default=None, max_length=255)
    enabled: Optional[bool] = Field(default=None)


class WebTargetResponse(BaseModel):
    """Schema returned for a WebTarget resource."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: Optional[int] = None
    name: str
    target_url: str
    hostname: str
    protocol: str
    port: int
    allowed_paths: Optional[str] = None
    scope_id: Optional[int] = None
    enabled: bool
    authorization_reference: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class WebAssessmentCreate(BaseModel):
    """Schema for initiating or enqueuing a web security assessment."""

    model_config = ConfigDict(from_attributes=True)

    web_target_id: int = Field(..., gt=0)
    assessment_profile: str = Field(default="PASSIVE", description="'PASSIVE' or 'SAFE_LOCAL'")


class WebAssessmentResponse(BaseModel):
    """Schema returned for a WebAssessment job."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    web_target_id: int
    assessment_profile: str
    status: str
    tool_name: str
    tool_version: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    output_reference: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime


class WebFindingResponse(BaseModel):
    """Schema returned for an individual WebFinding."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: int
    web_target_id: int
    title: str
    vulnerability_type: str
    severity: str
    confidence: str
    finding_status: str
    affected_url: str
    description: str
    evidence: Optional[str] = None
    remediation: Optional[str] = None
    reference: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    fingerprint: str
    created_at: datetime


class WebFindingUpdate(BaseModel):
    """Schema for updating a finding status / triaging."""

    model_config = ConfigDict(from_attributes=True)

    finding_status: str = Field(
        ...,
        description="'UNVERIFIED', 'NEEDS_REVIEW', 'CONFIRMED', 'FALSE_POSITIVE', or 'ACCEPTED_RISK'"
    )


class WebSecurityStatisticsResponse(BaseModel):
    """Aggregated statistics for web security assessments and findings."""

    model_config = ConfigDict(from_attributes=True)

    total_targets: int
    total_assessments: int
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    informational_findings: int
    severity_distribution: Dict[str, int]
    status_distribution: Dict[str, int]
    top_vulnerabilities: List[Dict[str, Any]]



# ---------------------------------------------------------------------------
# Phase 5: AI Triage & Incident Intelligence Schemas
# ---------------------------------------------------------------------------


class IncidentLifecycleStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class TriageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class IncidentLifecycleUpdate(BaseModel):
    """Schema for operator-initiated lifecycle status transitions."""

    new_status: IncidentLifecycleStatus
    reason: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Operator notes explaining the status change",
    )
    resolution_notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Resolution notes (required when resolving or marking FALSE_POSITIVE)",
    )


class AITriageRunCreate(BaseModel):
    """Schema for requesting a new triage run for an incident."""

    model_config = ConfigDict(from_attributes=True)
    incident_id: int = Field(..., gt=0)


class AITriageRunResponse(BaseModel):
    """Schema returned for an AI/rule-based triage run."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    provider: str
    model_name: Optional[str] = None
    prompt_version: str
    status: str
    input_fingerprint: Optional[str] = None
    result_json: Optional[str] = None
    confidence_score: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime


class IncidentEvidenceResponse(BaseModel):
    """Schema returned for a correlated evidence record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    source_type: str
    source_record_id: Optional[int] = None
    relationship_type: Optional[str] = None
    evidence_summary: Optional[str] = None
    evidence_timestamp: Optional[datetime] = None
    created_at: datetime


class IncidentTimelineEventResponse(BaseModel):
    """Schema returned for a single incident timeline event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    event_type: str
    description: Optional[str] = None
    source_type: Optional[str] = None
    source_record_id: Optional[int] = None
    timestamp: datetime
    created_at: datetime


class IncidentDetailResponse(BaseModel):
    """Extended incident response including triage, evidence, and timeline."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    timestamp: datetime
    source_ip: str
    attack_type: str
    payload: Optional[str] = None
    severity: str
    ai_analysis: Optional[str] = None
    is_mitigated: bool
    lifecycle_status: str = "OPEN"
    acknowledged_at: Optional[datetime] = None
    investigated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    # Extended detail
    triage_runs: List[AITriageRunResponse] = []
    evidence_items: List[IncidentEvidenceResponse] = []
    timeline_events: List[IncidentTimelineEventResponse] = []


class AIHealthResponse(BaseModel):
    """AI subsystem health status."""

    model_config = ConfigDict(from_attributes=True)

    ai_enabled: bool
    configured_provider: str
    ollama_url: str
    ollama_model: str
    ollama_available: bool
    active_provider: str
    fallback_available: bool


class IncidentIntelligenceOverview(BaseModel):
    """High-level statistics for the AI Intelligence Center."""

    model_config = ConfigDict(from_attributes=True)

    total_incidents: int
    open_incidents: int
    critical_incidents: int
    high_incidents: int
    incidents_with_triage: int
    pending_triage: int
    completed_triage: int
    failed_triage: int
    total_evidence_items: int
    suricata_evidence: int
    web_finding_evidence: int
    nmap_evidence: int
    ai_provider_status: str
    lifecycle_distribution: Dict[str, int]
    severity_distribution: Dict[str, int]
    attack_type_distribution: Dict[str, int]


# ---------------------------------------------------------------------------
# Phase 6: Automated Security Reporting Schemas
# ---------------------------------------------------------------------------


class ReportType(str, Enum):
    EXECUTIVE = "EXECUTIVE"
    TECHNICAL = "TECHNICAL"
    ASSESSMENT = "ASSESSMENT"
    OPERATIONS = "OPERATIONS"
    AI_INTELLIGENCE = "AI_INTELLIGENCE"


class ReportFormat(str, Enum):
    PDF = "PDF"
    HTML = "HTML"
    JSON = "JSON"
    CSV = "CSV"


class ReportGenerationStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReportCreate(BaseModel):
    """Schema for requesting a new security report generation job."""

    model_config = ConfigDict(from_attributes=True)

    report_type: ReportType = Field(..., description="Type of report to generate")
    title: Optional[str] = Field(default=None, max_length=255, description="Custom report title")
    format: ReportFormat = Field(default=ReportFormat.PDF, description="Output export format")
    period_start: Optional[datetime] = Field(default=None, description="Start timestamp of audit period")
    period_end: Optional[datetime] = Field(default=None, description="End timestamp of audit period")
    asset_id: Optional[int] = Field(default=None, description="Optional asset filter")
    incident_id: Optional[int] = Field(default=None, description="Optional incident ID for technical reports")
    include_ai_narrative: bool = Field(default=True, description="Whether to include AI analysis narrative")


class ReportResponse(BaseModel):
    """Schema returned for a GeneratedReport record.

    Security: file_path is NOT exposed in this schema to prevent absolute
    filesystem path leakage. Clients use the /download endpoint to retrieve files.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: str
    report_type: str
    title: str
    format: str
    # file_path intentionally excluded — absolute filesystem path must not be exposed via API
    file_uuid: Optional[str] = None  # UUID filename identifier (not full path)
    file_size: Optional[int] = None
    sha256_checksum: Optional[str] = None
    generation_status: str
    generated_by: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    source_count: int
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    # Addendum fields
    retry_count: int = 0
    download_count: int = 0
    template_version: str = "1.0"
    data_schema_version: str = "1.0"


class PaginatedReports(BaseModel):
    """Paginated list of reports."""

    model_config = ConfigDict(from_attributes=True)

    items: List[ReportResponse]
    total: int
    page: int
    page_size: int


class ReportStatisticsResponse(BaseModel):
    """Aggregated statistics for reporting subsystem."""

    model_config = ConfigDict(from_attributes=True)

    total_reports: int
    completed_reports: int
    pending_reports: int
    failed_reports: int
    type_distribution: Dict[str, int] = Field(default_factory=dict)
    format_distribution: Dict[str, int] = Field(default_factory=dict)
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_format: Dict[str, int] = Field(default_factory=dict)
