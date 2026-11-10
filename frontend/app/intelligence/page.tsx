import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import { getAIHealth, getIncidentIntelligenceOverview } from '@/lib/api';
import type { AIHealthResponse, IncidentIntelligenceOverview } from '@/types';
import Link from 'next/link';
import {
  BrainCircuit,
  Cpu,
  ShieldAlert,
  Radio,
  Bug,
  Server,
  Activity,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  PieChart,
  Layers,
} from 'lucide-react';

export const dynamic = 'force-dynamic';

export default async function IntelligencePage() {
  let health: AIHealthResponse = {
    ai_enabled: true,
    configured_provider: 'auto',
    ollama_url: 'http://127.0.0.1:11434',
    ollama_model: 'llama3',
    ollama_available: false,
    active_provider: 'rule_based',
    fallback_available: true,
  };

  let overview: IncidentIntelligenceOverview = {
    total_incidents: 0,
    open_incidents: 0,
    critical_incidents: 0,
    high_incidents: 0,
    incidents_with_triage: 0,
    pending_triage: 0,
    completed_triage: 0,
    failed_triage: 0,
    total_evidence_items: 0,
    suricata_evidence: 0,
    web_finding_evidence: 0,
    nmap_evidence: 0,
    ai_provider_status: 'rule_based',
    lifecycle_distribution: {},
    severity_distribution: {},
    attack_type_distribution: {},
  };

  try {
    const [h, o] = await Promise.all([
      getAIHealth().catch(() => health),
      getIncidentIntelligenceOverview().catch(() => overview),
    ]);
    health = h;
    overview = o;
  } catch {
    // fallback
  }

  const isOllama = health.active_provider === 'ollama';

  return (
    <AppShell>
      <Header title="Pusat Intelijen AI & Korelasi Ancaman Siber" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Banner: AI Provider Status */}
        <div className="p-5 rounded-xl border border-emerald-500/20 bg-gradient-to-r from-emerald-950/30 via-[#0F172A] to-[#0F172A] flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
              <BrainCircuit className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-white">AI Triage & Correlation Subsystem</h2>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                    isOllama
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                  }`}
                >
                  {isOllama ? 'OLLAMA LLM ONLINE' : 'DETERMINISTIC RULE-BASED ACTIVE'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Penyedia aktif: <span className="font-mono text-slate-300 font-semibold">{health.active_provider}</span> ({health.ollama_model}). Fallback deterministik selalu siap (100% ketersediaan).
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/incidents"
              className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
            >
              Lihat Pusat Insiden
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>

        {/* AI Engine Telemetry Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl border border-slate-800 bg-[#0F172A]/70">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase">
              <span>Insiden Ter-Triage</span>
              <BrainCircuit className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="mt-2 text-2xl font-bold font-mono text-white">
              {overview.incidents_with_triage}
            </div>
            <span className="text-[10px] text-slate-500">dari total {overview.total_incidents} insiden</span>
          </div>

          <div className="p-4 rounded-xl border border-slate-800 bg-[#0F172A]/70">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase">
              <span>Bukti Terkorelasi</span>
              <Layers className="h-4 w-4 text-blue-400" />
            </div>
            <div className="mt-2 text-2xl font-bold font-mono text-white">
              {overview.total_evidence_items}
            </div>
            <span className="text-[10px] text-slate-500">artefak telemetri terhubung</span>
          </div>

          <div className="p-4 rounded-xl border border-slate-800 bg-[#0F172A]/70">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase">
              <span>Triage Selesai</span>
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="mt-2 text-2xl font-bold font-mono text-white">
              {overview.completed_triage}
            </div>
            <span className="text-[10px] text-slate-500">{overview.pending_triage} antrean tertunda</span>
          </div>

          <div className="p-4 rounded-xl border border-slate-800 bg-[#0F172A]/70">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase">
              <span>Model & Presisi</span>
              <Cpu className="h-4 w-4 text-purple-400" />
            </div>
            <div className="mt-2 text-lg font-bold font-mono text-white truncate">
              {health.active_provider === 'ollama' ? health.ollama_model : 'Deterministic v1'}
            </div>
            <span className="text-[10px] text-slate-500">Pydantic strict schema</span>
          </div>
        </div>

        {/* Multi-Source Correlation Matrix */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Suricata Box */}
          <div className="p-5 rounded-xl border border-purple-500/20 bg-[#0F172A]/80 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Radio className="h-4 w-4 text-purple-400" />
                <h3 className="text-sm font-semibold text-white">Suricata IDS</h3>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
                Network Threat
              </span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {overview.suricata_evidence} Bukti
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Dideteksi melalui analisis telemetri EVE JSON dan PCAP offline dengan threshold & deduplikasi sidik jari.
            </p>
          </div>

          {/* Deep Eye Box */}
          <div className="p-5 rounded-xl border border-orange-500/20 bg-[#0F172A]/80 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bug className="h-4 w-4 text-orange-400" />
                <h3 className="text-sm font-semibold text-white">Deep Eye Web Sec</h3>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-orange-500/10 text-orange-400 border border-orange-500/20">
                Web App
              </span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {overview.web_finding_evidence} Bukti
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Temuan kerentanan web seperti SQLi, XSS, dan miskonfigurasi keamanan dari asesmen profil SAFE_LOCAL.
            </p>
          </div>

          {/* Nmap Box */}
          <div className="p-5 rounded-xl border border-cyan-500/20 bg-[#0F172A]/80 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="h-4 w-4 text-cyan-400" />
                <h3 className="text-sm font-semibold text-white">Nmap Discovery</h3>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                Port & Service
              </span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {overview.nmap_evidence} Bukti
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Konteks port terbuka, service footprint, dan surface attack yang sah sesuai otorisasi scope lab.
            </p>
          </div>
        </div>

        {/* Distributions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Lifecycle Status Distribution */}
          <div className="p-5 rounded-xl border border-slate-800 bg-[#0F172A]/80 space-y-4">
            <h3 className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
              Distribusi Status Siklus Insiden
            </h3>
            <div className="space-y-2 text-xs font-mono">
              {Object.keys(overview.lifecycle_distribution || {}).length === 0 ? (
                <div className="text-slate-500 text-center py-4">Belum ada data distribusi.</div>
              ) : (
                Object.entries(overview.lifecycle_distribution).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between p-2 rounded bg-slate-900/50">
                    <span className="text-slate-300">{status}</span>
                    <span className="font-bold text-white px-2 py-0.5 rounded bg-slate-800">
                      {count}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Severity Distribution */}
          <div className="p-5 rounded-xl border border-slate-800 bg-[#0F172A]/80 space-y-4">
            <h3 className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
              Distribusi Tingkat Keparahan
            </h3>
            <div className="space-y-2 text-xs font-mono">
              {Object.keys(overview.severity_distribution || {}).length === 0 ? (
                <div className="text-slate-500 text-center py-4">Belum ada data distribusi.</div>
              ) : (
                Object.entries(overview.severity_distribution).map(([sev, count]) => (
                  <div key={sev} className="flex items-center justify-between p-2 rounded bg-slate-900/50">
                    <span
                      className={`font-semibold ${
                        sev === 'CRITICAL'
                          ? 'text-red-400'
                          : sev === 'HIGH'
                          ? 'text-orange-400'
                          : 'text-yellow-400'
                      }`}
                    >
                      {sev}
                    </span>
                    <span className="font-bold text-white px-2 py-0.5 rounded bg-slate-800">
                      {count}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </AppShell>
  );
}

