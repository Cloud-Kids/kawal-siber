import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import { getIncidents, getIncidentIntelligenceOverview } from '@/lib/api';
import type { Incident, IncidentIntelligenceOverview } from '@/types';
import Link from 'next/link';
import {
  Siren,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  BrainCircuit,
  Eye,
  Filter,
  ArrowRight,
  Flame,
  Activity,
} from 'lucide-react';

export const dynamic = 'force-dynamic';

function getSeverityBadge(severity: string) {
  switch (severity) {
    case 'CRITICAL':
      return 'bg-red-500/10 text-red-400 border-red-500/30';
    case 'HIGH':
      return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
    case 'MEDIUM':
      return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
    case 'LOW':
      return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
    default:
      return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
  }
}

function getLifecycleBadge(status?: string) {
  switch (status) {
    case 'OPEN':
      return 'bg-red-500/15 text-red-400 border-red-500/30';
    case 'ACKNOWLEDGED':
      return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
    case 'INVESTIGATING':
      return 'bg-blue-500/15 text-blue-400 border-blue-500/30';
    case 'MITIGATED':
      return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    case 'RESOLVED':
      return 'bg-green-500/15 text-green-400 border-green-500/30';
    case 'FALSE_POSITIVE':
      return 'bg-slate-500/15 text-slate-400 border-slate-500/30';
    default:
      return 'bg-slate-500/15 text-slate-400 border-slate-500/30';
  }
}

export default async function IncidentsPage() {
  let incidents: Incident[] = [];
  let overview: IncidentIntelligenceOverview | null = null;

  try {
    const [incidentsResp, overviewResp] = await Promise.all([
      getIncidents({ page_size: 100 }),
      getIncidentIntelligenceOverview().catch(() => null),
    ]);
    incidents = incidentsResp.items || [];
    overview = overviewResp;
  } catch {
    // fallback
  }

  const totalIncidents = overview?.total_incidents ?? incidents.length;
  const openIncidents = overview?.open_incidents ?? incidents.filter((i) => !i.is_mitigated).length;
  const criticalIncidents = overview?.critical_incidents ?? incidents.filter((i) => i.severity === 'CRITICAL').length;
  const highIncidents = overview?.high_incidents ?? incidents.filter((i) => i.severity === 'HIGH').length;

  return (
    <AppShell>
      <Header title="Pusat Insiden Siber & Respon Teritorial" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Banner Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-xl border border-red-500/20 bg-gradient-to-r from-red-950/30 via-[#0F172A] to-[#0F172A]">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
              <Siren className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Unified Incident Command</h2>
              <p className="text-xs text-slate-400">
                Pusat orkestrasi insiden terintegrasi dengan korelasi multi-sumber (Nmap, Suricata, Deep Eye) dan asistensi AI Triage.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/intelligence"
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
            >
              <BrainCircuit className="h-4 w-4" />
              AI Intelligence Center
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl border border-slate-800 bg-[#0F172A]/70">
            <span className="text-xs font-mono text-slate-400 uppercase">Total Insiden</span>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-2xl font-bold font-mono text-white">{totalIncidents}</span>
              <Activity className="h-4 w-4 text-slate-500" />
            </div>
          </div>

          <div className="p-4 rounded-xl border border-amber-500/20 bg-[#0F172A]/70">
            <span className="text-xs font-mono text-amber-400 uppercase">Insiden Terbuka</span>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-2xl font-bold font-mono text-amber-400">{openIncidents}</span>
              <AlertTriangle className="h-4 w-4 text-amber-400" />
            </div>
          </div>

          <div className="p-4 rounded-xl border border-red-500/20 bg-[#0F172A]/70">
            <span className="text-xs font-mono text-red-400 uppercase">Kritis (Critical)</span>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-2xl font-bold font-mono text-red-400">{criticalIncidents}</span>
              <Flame className="h-4 w-4 text-red-400" />
            </div>
          </div>

          <div className="p-4 rounded-xl border border-orange-500/20 bg-[#0F172A]/70">
            <span className="text-xs font-mono text-orange-400 uppercase">Tinggi (High)</span>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-2xl font-bold font-mono text-orange-400">{highIncidents}</span>
              <ShieldAlert className="h-4 w-4 text-orange-400" />
            </div>
          </div>
        </div>

        {/* Incident Table */}
        <div className="rounded-xl border border-slate-800 bg-[#0F172A]/80 overflow-hidden">
          <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Siren className="h-4 w-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-white">Daftar Insiden Aktif & Riwayat</h3>
            </div>
            <span className="text-xs font-mono text-slate-400">
              {incidents.length} entri ditemukan
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#1E293B]/60 text-slate-400 font-mono border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Waktu</th>
                  <th className="px-4 py-3">Sumber Serangan</th>
                  <th className="px-4 py-3">Jenis Serangan</th>
                  <th className="px-4 py-3">Keparahan</th>
                  <th className="px-4 py-3">Status Siklus</th>
                  <th className="px-4 py-3">Analisis AI</th>
                  <th className="px-4 py-3 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {incidents.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-slate-500 font-sans">
                      Tidak ada insiden tercatat saat ini.
                    </td>
                  </tr>
                ) : (
                  incidents.map((incident) => (
                    <tr key={incident.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 text-slate-300 font-bold">#{incident.id}</td>
                      <td className="px-4 py-3 text-slate-400">
                        {incident.timestamp ? new Date(incident.timestamp).toLocaleString('id-ID') : '-'}
                      </td>
                      <td className="px-4 py-3 text-slate-300">{incident.source_ip}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded text-[11px] bg-slate-800 text-slate-300 border border-slate-700">
                          {incident.attack_type}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getSeverityBadge(
                            incident.severity
                          )}`}
                        >
                          {incident.severity}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getLifecycleBadge(
                            incident.lifecycle_status
                          )}`}
                        >
                          {incident.lifecycle_status || (incident.is_mitigated ? 'RESOLVED' : 'OPEN')}
                        </span>
                      </td>
                      <td className="px-4 py-3 max-w-xs truncate text-slate-400 font-sans">
                        {incident.ai_analysis ? (
                          <span className="text-emerald-400/90 flex items-center gap-1 text-[11px]">
                            <BrainCircuit className="h-3 w-3 shrink-0 text-emerald-400" />
                            {incident.ai_analysis.slice(0, 45)}...
                          </span>
                        ) : (
                          <span className="text-slate-600 text-[11px]">Belum ditriage</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/incidents/${incident.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-sans font-medium rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                        >
                          <Eye className="h-3 w-3" />
                          Detail & Triage
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </AppShell>
  );
}

