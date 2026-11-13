import type {
  AIHealthResponse,
  AITriageRun,
  Asset,
  AssetStatus,
  AvailabilityStatus,
  DashboardStats,
  GeneratedReport,
  HealthResponse,
  Incident,
  IncidentDetail,
  IncidentEvidence,
  IncidentIntelligenceOverview,
  IncidentTimelineEvent,
  MonitoringStatistics,
  PaginatedIncidents,
  PaginatedReports,
  PaginatedSecurityEvents,
  PcapAnalysis,
  ReportCreateRequest,
  ReportFormat,
  ReportStatistics,
  ReportType,
  ScanJob,
  ScanJobStatus,
  ScanResult,
  ScanScope,
  SecurityEvent,
  Severity,
  WebAssessment,
  WebFinding,
  WebSecurityStatistics,
  WebTarget,
} from '@/types';

/** Public API URL used by client-side fetches (browser → Next.js rewrites → backend) */
const PUBLIC_API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';

/**
 * Internal API URL used by Server Components (localhost-first with Docker env override).
 * Normalizes host to guarantee `/api/v1` prefix whether API_INTERNAL_URL contains it or not.
 */
function resolveInternalApiUrl(): string {
  const raw = process.env.API_INTERNAL_URL ?? 'http://127.0.0.1:8000';
  const clean = raw.replace(/\/+$/, '');
  return clean.endsWith('/api/v1') ? clean : `${clean}/api/v1`;
}

const INTERNAL_API_URL = resolveInternalApiUrl();

/**
 * Determine the base URL based on the execution context.
 * Server Components use the internal URL; Client Components use the public URL.
 */
function getBaseUrl(): string {
  if (typeof window === 'undefined') {
    return INTERNAL_API_URL;
  }
  return PUBLIC_API_URL;
}

/** Build a full endpoint URL */
function endpoint(path: string): string {
  return `${getBaseUrl()}${path}`;
}

/** Generic fetch wrapper that throws on non-OK responses */
async function apiFetch<T>(
  url: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(url, {
    cache: 'no-store',
    ...options,
    headers: {
      ...(options?.body ? { 'Content-Type': 'application/json' } : {}),
      ...options?.headers,
    },
  });
  if (!response.ok) {
    let errorDetail = `${response.status} ${response.statusText}`;
    try {
      const errBody = await response.json();
      if (errBody.detail) {
        errorDetail = typeof errBody.detail === 'string'
          ? errBody.detail
          : JSON.stringify(errBody.detail);
      }
    } catch {
      // Body not JSON
    }
    throw new Error(`API error: ${errorDetail} — ${url}`);
  }
  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>(endpoint('/health'));
}

// ---------------------------------------------------------------------------
// Assets
// ---------------------------------------------------------------------------

export async function getAssets(params?: {
  status?: AssetStatus;
  availability_status?: AvailabilityStatus;
  scope_id?: number;
  search?: string;
  target_type?: 'ip' | 'hostname';
  skip?: number;
  limit?: number;
}): Promise<Asset[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.availability_status) query.set('availability_status', params.availability_status);
  if (params?.scope_id !== undefined) query.set('scope_id', String(params.scope_id));
  if (params?.search) query.set('search', params.search);
  if (params?.target_type) query.set('target_type', params.target_type);
  if (params?.skip !== undefined) query.set('skip', String(params.skip));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<Asset[]>(endpoint(`/assets${qs}`));
}

export async function getAsset(id: number): Promise<Asset> {
  return apiFetch<Asset>(endpoint(`/assets/${id}`));
}

export async function createAsset(
  data: {
    name: string;
    target_ip: string;
    port: number;
    status?: AssetStatus;
    availability_status?: AvailabilityStatus;
    scope_id?: number | null;
  },
): Promise<Asset> {
  return apiFetch<Asset>(endpoint('/assets'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function updateAsset(
  id: number,
  data: Partial<Asset>,
): Promise<Asset> {
  return apiFetch<Asset>(endpoint(`/assets/${id}`), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function deleteAsset(id: number): Promise<Asset> {
  return apiFetch<Asset>(endpoint(`/assets/${id}`), {
    method: 'DELETE',
  });
}

// ---------------------------------------------------------------------------
// Scan Scopes
// ---------------------------------------------------------------------------

export async function getScanScopes(params?: {
  enabled?: boolean;
  skip?: number;
  limit?: number;
}): Promise<ScanScope[]> {
  const query = new URLSearchParams();
  if (params?.enabled !== undefined) query.set('enabled', String(params.enabled));
  if (params?.skip !== undefined) query.set('skip', String(params.skip));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<ScanScope[]>(endpoint(`/scan-scopes${qs}`));
}

export async function getScanScope(id: number): Promise<ScanScope> {
  return apiFetch<ScanScope>(endpoint(`/scan-scopes/${id}`));
}

export async function createScanScope(
  data: {
    name: string;
    cidr: string;
    description?: string | null;
    authorization_reference: string;
    enabled?: boolean;
    expires_at: string;
  },
): Promise<ScanScope> {
  return apiFetch<ScanScope>(endpoint('/scan-scopes'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function updateScanScope(
  id: number,
  data: Partial<ScanScope>,
): Promise<ScanScope> {
  return apiFetch<ScanScope>(endpoint(`/scan-scopes/${id}`), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// Network Scans
// ---------------------------------------------------------------------------

export async function createAssetScan(assetId: number): Promise<ScanJob> {
  return apiFetch<ScanJob>(endpoint(`/assets/${assetId}/scans`), {
    method: 'POST',
  });
}

export async function getScans(params?: {
  status?: ScanJobStatus;
  asset_id?: number;
  skip?: number;
  limit?: number;
}): Promise<ScanJob[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.asset_id !== undefined) query.set('asset_id', String(params.asset_id));
  if (params?.skip !== undefined) query.set('skip', String(params.skip));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<ScanJob[]>(endpoint(`/scans${qs}`));
}

export async function getScan(id: number): Promise<ScanJob> {
  return apiFetch<ScanJob>(endpoint(`/scans/${id}`));
}

export async function getScanResults(id: number): Promise<ScanResult[]> {
  return apiFetch<ScanResult[]>(endpoint(`/scans/${id}/results`));
}

export async function getAssetScans(assetId: number): Promise<ScanJob[]> {
  return apiFetch<ScanJob[]>(endpoint(`/assets/${assetId}/scans`));
}

// ---------------------------------------------------------------------------
// Incidents
// ---------------------------------------------------------------------------

export async function getIncidents(params?: {
  asset_id?: number;
  severity?: Severity;
  page?: number;
  page_size?: number;
}): Promise<PaginatedIncidents> {
  const query = new URLSearchParams();
  if (params?.asset_id !== undefined)
    query.set('asset_id', String(params.asset_id));
  if (params?.severity) query.set('severity', params.severity);
  if (params?.page !== undefined) query.set('page', String(params.page));
  if (params?.page_size !== undefined)
    query.set('page_size', String(params.page_size));
  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<PaginatedIncidents>(endpoint(`/incidents${qs}`));
}

export async function getIncident(id: number): Promise<Incident> {
  return apiFetch<Incident>(endpoint(`/incidents/${id}`));
}

export async function createIncident(
  data: Omit<Incident, 'id'>,
): Promise<Incident> {
  return apiFetch<Incident>(endpoint('/incidents'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function updateIncident(
  id: number,
  data: { is_mitigated?: boolean; ai_analysis?: string },
): Promise<Incident> {
  return apiFetch<Incident>(endpoint(`/incidents/${id}`), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// Dashboard Stats (computed server-side from assets + incidents)
// ---------------------------------------------------------------------------

export async function getDashboardStats(): Promise<DashboardStats> {
  const [assets, incidents] = await Promise.all([
    getAssets(),
    getIncidents({ page_size: 1000 }),
  ]);

  const totalAssets = assets.length;
  const safeAssets = assets.filter((a) => a.status === 'SAFE').length;
  const assetsUnderAttack = assets.filter(
    (a) => a.status === 'UNDER_ATTACK',
  ).length;
  const assetsDown = assets.filter((a) => a.status === 'DOWN').length;

  const allIncidents = incidents.items;
  const totalIncidents = incidents.total;
  const criticalIncidents = allIncidents.filter(
    (i) => i.severity === 'CRITICAL',
  ).length;
  const unresolvedIncidents = allIncidents.filter(
    (i) => !i.is_mitigated,
  ).length;

  return {
    totalAssets,
    safeAssets,
    assetsUnderAttack,
    assetsDown,
    totalIncidents,
    criticalIncidents,
    unresolvedIncidents,
  };
}

// ---------------------------------------------------------------------------
// Phase 3: Suricata & PCAP Monitoring
// ---------------------------------------------------------------------------

export async function getMonitoringStatistics(): Promise<MonitoringStatistics> {
  return apiFetch<MonitoringStatistics>(endpoint('/monitoring/statistics'));
}

export async function getPcapAnalyses(params?: {
  skip?: number;
  limit?: number;
}): Promise<PcapAnalysis[]> {
  const query = new URLSearchParams();
  if (params?.skip !== undefined) query.set('skip', String(params.skip));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<PcapAnalysis[]>(endpoint(`/monitoring/pcap${qs}`));
}

export async function getPcapAnalysis(id: number): Promise<PcapAnalysis> {
  return apiFetch<PcapAnalysis>(endpoint(`/monitoring/pcap/${id}`));
}

export async function createPcapAnalysis(filename: string): Promise<PcapAnalysis> {
  return apiFetch<PcapAnalysis>(endpoint('/monitoring/pcap'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  });
}

export async function uploadPcapFile(formData: FormData): Promise<PcapAnalysis> {
  return apiFetch<PcapAnalysis>(endpoint('/monitoring/pcap'), {
    method: 'POST',
    body: formData,
  });
}

export async function getSecurityEvents(params?: {
  event_type?: string;
  asset_id?: number;
  severity?: number;
  protocol?: string;
  pcap_analysis_id?: number;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedSecurityEvents> {
  const query = new URLSearchParams();
  if (params?.event_type) query.set('event_type', params.event_type);
  if (params?.asset_id !== undefined) query.set('asset_id', String(params.asset_id));
  if (params?.severity !== undefined) query.set('severity', String(params.severity));
  if (params?.protocol) query.set('protocol', params.protocol);
  if (params?.pcap_analysis_id !== undefined) query.set('pcap_analysis_id', String(params.pcap_analysis_id));
  if (params?.search) query.set('search', params.search);
  if (params?.page !== undefined) query.set('page', String(params.page));
  if (params?.page_size !== undefined) query.set('page_size', String(params.page_size));
  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<PaginatedSecurityEvents>(endpoint(`/security-events${qs}`));
}

export async function getSecurityAlerts(params?: {
  asset_id?: number;
  severity?: number;
  category?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedSecurityEvents> {
  const query = new URLSearchParams();
  if (params?.asset_id !== undefined) query.set('asset_id', String(params.asset_id));
  if (params?.severity !== undefined) query.set('severity', String(params.severity));
  if (params?.category) query.set('category', params.category);
  if (params?.search) query.set('search', params.search);
  if (params?.page !== undefined) query.set('page', String(params.page));
  if (params?.page_size !== undefined) query.set('page_size', String(params.page_size));
  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<PaginatedSecurityEvents>(endpoint(`/security-alerts${qs}`));
}

export async function getSecurityEvent(idOrEventId: string | number): Promise<SecurityEvent> {
  return apiFetch<SecurityEvent>(endpoint(`/security-events/${idOrEventId}`));
}

// ---------------------------------------------------------------------------
// Phase 4: Web Security & Deep Eye API functions
// ---------------------------------------------------------------------------

export async function getWebTargets(params?: {
  enabled?: boolean;
  asset_id?: number;
}): Promise<WebTarget[]> {
  const query = new URLSearchParams();
  if (params?.enabled !== undefined) query.set('enabled', String(params.enabled));
  if (params?.asset_id !== undefined) query.set('asset_id', String(params.asset_id));
  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<WebTarget[]>(endpoint(`/web-targets${qs}`));
}

export async function createWebTarget(data: {
  name: string;
  target_url: string;
  asset_id?: number | null;
  scope_id?: number | null;
  allowed_paths?: string;
  authorization_reference?: string;
  enabled?: boolean;
}): Promise<WebTarget> {
  return apiFetch<WebTarget>(endpoint('/web-targets'), {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getWebTarget(id: number): Promise<WebTarget> {
  return apiFetch<WebTarget>(endpoint(`/web-targets/${id}`));
}

export async function updateWebTarget(
  id: number,
  data: Partial<WebTarget>,
): Promise<WebTarget> {
  return apiFetch<WebTarget>(endpoint(`/web-targets/${id}`), {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteWebTarget(id: number): Promise<void> {
  return apiFetch<void>(endpoint(`/web-targets/${id}`), {
    method: 'DELETE',
  });
}

export async function createWebAssessment(
  data: {
    web_target_id: number;
    assessment_profile: string;
  },
  runImmediate: boolean = true,
): Promise<WebAssessment> {
  return apiFetch<WebAssessment>(
    endpoint(`/web-assessments?run_immediate=${runImmediate}`),
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
  );
}

export async function getWebAssessments(params?: {
  web_target_id?: number;
  status?: string;
}): Promise<WebAssessment[]> {
  const query = new URLSearchParams();
  if (params?.web_target_id !== undefined) query.set('web_target_id', String(params.web_target_id));
  if (params?.status) query.set('status', params.status);
  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<WebAssessment[]>(endpoint(`/web-assessments${qs}`));
}

export async function getWebAssessment(id: number): Promise<WebAssessment> {
  return apiFetch<WebAssessment>(endpoint(`/web-assessments/${id}`));
}

export async function getAssessmentFindings(id: number): Promise<WebFinding[]> {
  return apiFetch<WebFinding[]>(endpoint(`/web-assessments/${id}/findings`));
}

export async function getWebFindings(params?: {
  severity?: string;
  finding_status?: string;
  web_target_id?: number;
  vulnerability_type?: string;
  search?: string;
}): Promise<WebFinding[]> {
  const query = new URLSearchParams();
  if (params?.severity) query.set('severity', params.severity);
  if (params?.finding_status) query.set('finding_status', params.finding_status);
  if (params?.web_target_id !== undefined) query.set('web_target_id', String(params.web_target_id));
  if (params?.vulnerability_type) query.set('vulnerability_type', params.vulnerability_type);
  if (params?.search) query.set('search', params.search);
  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<WebFinding[]>(endpoint(`/web-findings${qs}`));
}

export async function getWebFinding(id: number): Promise<WebFinding> {
  return apiFetch<WebFinding>(endpoint(`/web-findings/${id}`));
}

export async function updateWebFindingStatus(
  id: number,
  findingStatus: string,
): Promise<WebFinding> {
  return apiFetch<WebFinding>(endpoint(`/web-findings/${id}`), {
    method: 'PATCH',
    body: JSON.stringify({ finding_status: findingStatus }),
  });
}

export async function getWebSecurityStatistics(): Promise<WebSecurityStatistics> {
  return apiFetch<WebSecurityStatistics>(endpoint('/web-security/statistics'));
}


// ---------------------------------------------------------------------------
// Phase 5: AI Triage & Incident Intelligence API
// ---------------------------------------------------------------------------

export async function getAIHealth(): Promise<AIHealthResponse> {
  return apiFetch<AIHealthResponse>(endpoint('/ai/health'));
}

export async function getIncidentIntelligenceOverview(): Promise<IncidentIntelligenceOverview> {
  return apiFetch<IncidentIntelligenceOverview>(endpoint('/incident-intelligence/overview'));
}

export async function getIncidentDetail(id: number): Promise<IncidentDetail> {
  return apiFetch<IncidentDetail>(endpoint(`/incidents/${id}/detail`));
}

export async function requestIncidentTriage(id: number): Promise<AITriageRun> {
  return apiFetch<AITriageRun>(endpoint(`/incidents/${id}/triage`), {
    method: 'POST',
  });
}

export async function getIncidentTriageRuns(id: number): Promise<AITriageRun[]> {
  return apiFetch<AITriageRun[]>(endpoint(`/incidents/${id}/triage`));
}

export async function getIncidentEvidence(id: number): Promise<IncidentEvidence[]> {
  return apiFetch<IncidentEvidence[]>(endpoint(`/incidents/${id}/evidence`));
}

export async function getIncidentTimeline(id: number): Promise<IncidentTimelineEvent[]> {
  return apiFetch<IncidentTimelineEvent[]>(endpoint(`/incidents/${id}/timeline`));
}

export async function correlateIncident(id: number): Promise<{
  incident_id: number;
  suricata_matches: number;
  web_finding_matches: number;
  nmap_matches: number;
  evidence_created: number;
  timeline_events_created: number;
  confidence_score: number;
  correlation_notes: string;
}> {
  return apiFetch(endpoint(`/incidents/${id}/correlate`), {
    method: 'POST',
  });
}

export async function updateIncidentStatus(
  id: number,
  newStatus: string,
  reason?: string,
  resolutionNotes?: string,
): Promise<{
  incident_id: number;
  previous_status: string;
  new_status: string;
  timestamp: string;
}> {
  return apiFetch(endpoint(`/incidents/${id}/status`), {
    method: 'PATCH',
    body: JSON.stringify({
      new_status: newStatus,
      reason,
      resolution_notes: resolutionNotes,
    }),
  });
}

// ---------------------------------------------------------------------------
// Phase 6: Automated Reporting & Platform Analytics
// ---------------------------------------------------------------------------

export async function getReports(params?: {
  report_type?: ReportType;
  format?: ReportFormat;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedReports> {
  const query = new URLSearchParams();
  if (params?.report_type) query.set('report_type', params.report_type);
  if (params?.format) query.set('format', params.format);
  if (params?.status) query.set('status', params.status);
  if (params?.page !== undefined) query.set('page', String(params.page));
  if (params?.page_size !== undefined)
    query.set('page_size', String(params.page_size));
  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<PaginatedReports>(endpoint(`/reports${qs}`));
}

export async function getReport(id: string | number): Promise<GeneratedReport> {
  return apiFetch<GeneratedReport>(endpoint(`/reports/${id}`));
}

export async function createReport(
  data: ReportCreateRequest,
): Promise<GeneratedReport> {
  return apiFetch<GeneratedReport>(endpoint('/reports'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export function getReportDownloadUrl(id: string | number): string {
  return `${PUBLIC_API_URL}/reports/${id}/download`;
}

export async function previewReport(id: string | number): Promise<{
  report_id: string;
  format: string;
  title: string;
  content: string;
}> {
  return apiFetch(endpoint(`/reports/${id}/preview`));
}

export async function regenerateReport(
  id: string | number,
): Promise<GeneratedReport> {
  return apiFetch<GeneratedReport>(endpoint(`/reports/${id}/regenerate`), {
    method: 'POST',
  });
}

export async function getReportStatistics(): Promise<ReportStatistics> {
  return apiFetch<ReportStatistics>(endpoint('/reports/statistics'));
}

