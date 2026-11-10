export type AssetStatus = 'UNKNOWN' | 'SAFE' | 'WARNING' | 'UNDER_ATTACK' | 'DOWN';
export type AvailabilityStatus = 'UNKNOWN' | 'UP' | 'DOWN';
export type ScanJobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export type AttackType =
  | 'BRUTE_FORCE'
  | 'SQL_INJECTION'
  | 'XSS'
  | 'PORT_SCAN'
  | 'ANOMALY_TRAFFIC';

export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'PENDING';

export interface ScanScope {
  id: number;
  name: string;
  cidr: string;
  description: string | null;
  authorization_reference: string;
  enabled: boolean;
  expires_at: string;
  created_at: string;
  updated_at: string | null;
}

export interface Asset {
  id: number;
  name: string;
  target_ip: string;
  port: number;
  status: AssetStatus;
  availability_status: AvailabilityStatus;
  scope_id: number | null;
  response_time_ms: number | null;
  last_scanned: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface ScanResult {
  id: number;
  scan_job_id: number;
  protocol: string;
  port: number;
  state: string;
  service_name: string | null;
  product: string | null;
  version: string | null;
  extra_info: string | null;
  reason: string | null;
}

export interface ScanJob {
  id: number;
  asset_id: number;
  status: ScanJobStatus;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  resolved_ip: string | null;
  scanner_version: string | null;
  attempts: number;
  error_code: string | null;
  error_message: string | null;
  results?: ScanResult[];
}

export type IncidentLifecycleStatus =
  | 'OPEN'
  | 'ACKNOWLEDGED'
  | 'INVESTIGATING'
  | 'MITIGATED'
  | 'RESOLVED'
  | 'FALSE_POSITIVE';

export interface Incident {
  id: number;
  asset_id: number;
  timestamp: string;
  source_ip: string;
  attack_type: AttackType;
  payload: string | null;
  severity: Severity;
  ai_analysis: string | null;
  is_mitigated: boolean;
  lifecycle_status?: IncidentLifecycleStatus;
  acknowledged_at?: string | null;
  investigated_at?: string | null;
  resolved_at?: string | null;
  resolution_notes?: string | null;
}

export interface PaginatedIncidents {
  items: Incident[];
  total: number;
  page: number;
  page_size: number;
}

export interface HealthResponse {
  status: string;
  database: string;
  version: string;
}

export interface DashboardStats {
  totalAssets: number;
  safeAssets: number;
  assetsUnderAttack: number;
  assetsDown: number;
  totalIncidents: number;
  criticalIncidents: number;
  unresolvedIncidents: number;
}

export type PcapAnalysisStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export interface PcapAnalysis {
  id: number;
  filename: string;
  file_hash: string;
  file_size_bytes: number | null;
  status: PcapAnalysisStatus;
  started_at: string | null;
  completed_at: string | null;
  event_count: number;
  alert_count: number;
  error_message: string | null;
  created_at: string;
}

export interface SecurityEvent {
  id: number;
  event_id: string;
  pcap_analysis_id: number | null;
  asset_id: number | null;
  timestamp: string;
  event_type: string;
  source_ip: string | null;
  destination_ip: string | null;
  source_port: number | null;
  destination_port: number | null;
  protocol: string | null;
  signature_id: number | null;
  signature: string | null;
  category: string | null;
  severity: number | null; // 1=Critical, 2=High, 3=Medium, 4=Low
  confidence: string | null;
  raw_event: string | null;
  created_at: string;
}

export interface PaginatedSecurityEvents {
  items: SecurityEvent[];
  total: number;
  page: number;
  page_size: number;
}

export interface MonitoringStatistics {
  total_events: number;
  total_alerts: number;
  total_pcap_analyses: number;
  severity_distribution: Record<string, number>;
  protocol_distribution: Record<string, number>;
  event_type_distribution: Record<string, number>;
  top_signatures: Array<{
    signature: string;
    category: string | null;
    count: number;
  }>;
  correlated_incidents_count: number;
}

// ---------------------------------------------------------------------------
// Phase 4: Web Security & Deep Eye Types
// ---------------------------------------------------------------------------

export type WebAssessmentProfile = 'PASSIVE' | 'SAFE_LOCAL';
export type WebAssessmentStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type WebFindingSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
export type WebFindingStatus = 'UNVERIFIED' | 'NEEDS_REVIEW' | 'CONFIRMED' | 'FALSE_POSITIVE' | 'ACCEPTED_RISK';

export interface WebTarget {
  id: number;
  asset_id: number | null;
  name: string;
  target_url: string;
  hostname: string;
  protocol: string;
  port: number;
  allowed_paths: string | null;
  scope_id: number | null;
  enabled: boolean;
  authorization_reference: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface WebAssessment {
  id: number;
  web_target_id: number;
  assessment_profile: WebAssessmentProfile;
  status: WebAssessmentStatus;
  tool_name: string;
  tool_version: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  output_reference: string | null;
  error_message: string | null;
  created_at: string;
}

export interface WebFinding {
  id: number;
  assessment_id: number;
  web_target_id: number;
  title: string;
  vulnerability_type: string;
  severity: WebFindingSeverity;
  confidence: string;
  finding_status: WebFindingStatus;
  affected_url: string;
  description: string;
  evidence: string | null;
  remediation: string | null;
  reference: string | null;
  first_seen: string;
  last_seen: string;
  fingerprint: string;
  created_at: string;
}

export interface WebSecurityStatistics {
  total_targets: number;
  total_assessments: number;
  total_findings: number;
  critical_findings: number;
  high_findings: number;
  medium_findings: number;
  low_findings: number;
  informational_findings: number;
  severity_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
  top_vulnerabilities: Array<{ type: string; count: number }>;
}


// ---------------------------------------------------------------------------
// Phase 5: AI Triage & Incident Intelligence
// ---------------------------------------------------------------------------

export type TriageRunStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'REQUIRES_REVIEW';
export type EvidenceSourceType = 'SURICATA_EVENT' | 'WEB_FINDING' | 'NMAP_RESULT' | 'MANUAL_EVIDENCE';

export interface AITriageRun {
  id: number;
  incident_id: number;
  provider: string;
  model_name: string | null;
  prompt_version: string;
  status: TriageRunStatus;
  input_fingerprint: string | null;
  result_json: string | null;
  confidence_score: number | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface IncidentEvidence {
  id: number;
  incident_id: number;
  source_type: EvidenceSourceType;
  source_record_id: number | null;
  relationship_type: string | null;
  evidence_summary: string | null;
  evidence_timestamp: string | null;
  created_at: string;
}

export interface IncidentTimelineEvent {
  id: number;
  incident_id: number;
  event_type: string;
  description: string | null;
  source_type: string | null;
  source_record_id: number | null;
  timestamp: string;
  created_at: string;
}

export interface IncidentDetail extends Incident {
  triage_runs: AITriageRun[];
  evidence_items: IncidentEvidence[];
  timeline_events: IncidentTimelineEvent[];
}

export interface AIHealthResponse {
  ai_enabled: boolean;
  configured_provider: string;
  ollama_url: string;
  ollama_model: string;
  ollama_available: boolean;
  active_provider: string;
  fallback_available: boolean;
}

export interface IncidentIntelligenceOverview {
  total_incidents: number;
  open_incidents: number;
  critical_incidents: number;
  high_incidents: number;
  incidents_with_triage: number;
  pending_triage: number;
  completed_triage: number;
  failed_triage: number;
  total_evidence_items: number;
  suricata_evidence: number;
  web_finding_evidence: number;
  nmap_evidence: number;
  ai_provider_status: string;
  lifecycle_distribution: Record<string, number>;
  severity_distribution: Record<string, number>;
  attack_type_distribution: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Phase 6: Automated Reporting & Platform Analytics Types
// ---------------------------------------------------------------------------

export type ReportType =
  | 'EXECUTIVE'
  | 'TECHNICAL'
  | 'ASSESSMENT'
  | 'OPERATIONS'
  | 'AI_INTELLIGENCE';

export type ReportFormat = 'PDF' | 'HTML' | 'JSON' | 'CSV';

export type ReportGenerationStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface GeneratedReport {
  id: number;
  report_id: string;
  report_type: ReportType;
  title: string;
  format: ReportFormat;
  file_path: string | null;
  file_size: number | null;
  sha256_checksum: string | null;
  generation_status: ReportGenerationStatus;
  generated_by: string;
  period_start: string | null;
  period_end: string | null;
  source_count: number;
  parameters_json: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface PaginatedReports {
  items: GeneratedReport[];
  total: number;
  page: number;
  page_size: number;
}

export interface ReportCreateRequest {
  report_type: ReportType;
  format: ReportFormat;
  title?: string;
  period_start?: string;
  period_end?: string;
  asset_id?: number;
  incident_id?: number;
  include_ai_narrative?: boolean;
  custom_notes?: string;
  generated_by?: string;
}

export interface ReportStatistics {
  total_reports: number;
  completed_reports: number;
  failed_reports: number;
  pending_reports: number;
  by_type: Record<string, number>;
  by_format: Record<string, number>;
  latest_report: GeneratedReport | null;
}

