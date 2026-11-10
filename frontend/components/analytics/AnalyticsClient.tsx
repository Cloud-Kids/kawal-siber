'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  BarChart3,
  ShieldAlert,
  Server,
  Globe,
  Radio,
  BrainCircuit,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Activity,
  ArrowUpRight,
  TrendingUp,
  Cpu,
  Layers,
  Sparkles,
  PieChart,
} from 'lucide-react';
import type {
  Asset,
  Incident,
  IncidentIntelligenceOverview,
  MonitoringStatistics,
  ReportStatistics,
  WebSecurityStatistics,
} from '@/types';

interface AnalyticsClientProps {
  assets: Asset[];
  incidents: Incident[];
  monitoringStats: MonitoringStatistics | null;
  webStats: WebSecurityStatistics | null;
  intelOverview: IncidentIntelligenceOverview | null;
  reportStats: ReportStatistics | null;
}

export default function AnalyticsClient({
  assets,
  incidents,
  monitoringStats,
  webStats,
  intelOverview,
  reportStats,
}: AnalyticsClientProps) {
  // Aggregate Metrics
  const totalAssets = assets.length;
  const upAssets = assets.filter((a) => a.availability_status === 'UP').length;
  const downAssets = assets.filter((a) => a.availability_status === 'DOWN').length;

  const totalIncidents = incidents.length;
  const criticalIncidents = incidents.filter((i) => i.severity === 'CRITICAL').length;
  const highIncidents = incidents.filter((i) => i.severity === 'HIGH').length;
  const mediumIncidents = incidents.filter((i) => i.severity === 'MEDIUM').length;
  const lowIncidents = incidents.filter((i) => i.severity === 'LOW').length;

  const mitigatedIncidents = incidents.filter(
    (i) => i.is_mitigated || i.lifecycle_status === 'RESOLVED' || i.lifecycle_status === 'MITIGATED',
  ).length;
  const mitigationRate = totalIncidents > 0 ? Math.round((mitigatedIncidents / totalIncidents) * 100) : 100;

  // Attack Type Breakdown
  const attackTypes: Record<string, number> = {};
  for (const inc of incidents) {
    const at = inc.attack_type || 'UNKNOWN';
    attackTypes[at] = (attackTypes[at] || 0) + 1;
  }

  // Lifecycle Breakdown
  const lifecycles: Record<string, number> = {};
  for (const inc of incidents) {
    const lc = inc.lifecycle_status || 'OPEN';
    lifecycles[lc] = (lifecycles[lc] || 0) + 1;
  }

  return (
    <div className="space-y-6">
      {/* Top Banner with Quick Actions */}
      <div className="p-5 rounded-xl border border-emerald-500/20 bg-gradient-to-r from-emerald-950/30 via-[#0F172A] to-[#0F172A] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
            <BarChart3 className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">
              Pusat Intelijen & Metrik Pertahanan Siber
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Konsolidasi data telemetri Nmap, Suricata IDS, Deep Eye Web Scanner, dan AI Triage.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/reports/create?type=OPERATIONS"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#1E293B] hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition-colors"
          >
            <FileText className="h-3.5 w-3.5" /> Laporan Operasional
          </Link>
          <Link
            href="/reports/create?type=EXECUTIVE"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors shadow-lg shadow-emerald-950/40"
          >
            <ArrowUpRight className="h-3.5 w-3.5" /> Ekspor Eksekutif
          </Link>
        </div>
      </div>

      {/* KPI Cards Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400 font-mono uppercase tracking-wider">
              Total Insiden Siber
            </div>
            <div className="text-2xl font-bold text-white mt-1">{totalIncidents}</div>
            <div className="text-[11px] text-rose-400 mt-1">
              {criticalIncidents} Kritis • {highIncidents} Tinggi
            </div>
          </div>
          <div className="p-3 rounded-lg bg-rose-500/10 text-rose-400">
            <ShieldAlert className="h-6 w-6" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400 font-mono uppercase tracking-wider">
              Tingkat Mitigasi (SLA)
            </div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">{mitigationRate}%</div>
            <div className="text-[11px] text-slate-400 mt-1">
              {mitigatedIncidents} dari {totalIncidents} tertangani
            </div>
          </div>
          <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-400">
            <CheckCircle2 className="h-6 w-6" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400 font-mono uppercase tracking-wider">
              Postur Aset Terpantau
            </div>
            <div className="text-2xl font-bold text-sky-400 mt-1">{totalAssets}</div>
            <div className="text-[11px] text-slate-400 mt-1">
              {upAssets} Aktif (UP) • {downAssets} Gangguan (DOWN)
            </div>
          </div>
          <div className="p-3 rounded-lg bg-sky-500/10 text-sky-400">
            <Server className="h-6 w-6" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400 font-mono uppercase tracking-wider">
              Telemetri IDS Suricata
            </div>
            <div className="text-2xl font-bold text-purple-400 mt-1">
              {monitoringStats?.total_events ?? 0}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {monitoringStats?.total_alerts ?? 0} Alert terdeteksi
            </div>
          </div>
          <div className="p-3 rounded-lg bg-purple-500/10 text-purple-400">
            <Radio className="h-6 w-6" />
          </div>
        </div>
      </div>

      {/* Analytics Grid: Threat Vectors & Lifecycle */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Threat Classification & Attack Vectors */}
        <div className="p-5 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider font-mono flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-rose-400" /> Distribusi Vektor Serangan
            </h3>
            <span className="text-xs font-mono text-slate-400">{Object.keys(attackTypes).length} Vektor</span>
          </div>

          <div className="space-y-3 pt-2">
            {Object.keys(attackTypes).length === 0 ? (
              <div className="text-xs text-slate-500 font-mono py-6 text-center">
                Belum ada data serangan tercatat.
              </div>
            ) : (
              Object.entries(attackTypes).map(([type, count]) => {
                const pct = totalIncidents > 0 ? Math.round((count / totalIncidents) * 100) : 0;
                return (
                  <div key={type} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono text-slate-200">{type}</span>
                      <span className="font-mono text-slate-400">
                        {count} ({pct}%)
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-rose-500 to-amber-500 transition-all duration-300"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Severity Matrix & Lifecycle Status */}
        <div className="p-5 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider font-mono flex items-center gap-2">
              <Activity className="h-4 w-4 text-amber-400" /> Matriks Keparahan & Siklus Hidup
            </h3>
            <span className="text-xs font-mono text-slate-400">SOC Pipeline</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2">
            <div className="p-3 rounded-lg bg-rose-950/30 border border-rose-500/20 text-center">
              <div className="text-[10px] font-mono text-rose-400 uppercase">CRITICAL</div>
              <div className="text-xl font-bold text-rose-400 mt-1">{criticalIncidents}</div>
            </div>
            <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-500/20 text-center">
              <div className="text-[10px] font-mono text-amber-400 uppercase">HIGH</div>
              <div className="text-xl font-bold text-amber-400 mt-1">{highIncidents}</div>
            </div>
            <div className="p-3 rounded-lg bg-yellow-950/30 border border-yellow-500/20 text-center">
              <div className="text-[10px] font-mono text-yellow-400 uppercase">MEDIUM</div>
              <div className="text-xl font-bold text-yellow-400 mt-1">{mediumIncidents}</div>
            </div>
            <div className="p-3 rounded-lg bg-sky-950/30 border border-sky-500/20 text-center">
              <div className="text-[10px] font-mono text-sky-400 uppercase">LOW</div>
              <div className="text-xl font-bold text-sky-400 mt-1">{lowIncidents}</div>
            </div>
          </div>

          <div className="pt-3 border-t border-[rgba(255,255,255,0.04)] space-y-2">
            <div className="text-xs font-medium text-slate-300">Pipeline Status Operasional:</div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              {['OPEN', 'INVESTIGATING', 'RESOLVED'].map((status) => {
                const count = lifecycles[status] || 0;
                return (
                  <div
                    key={status}
                    className="p-2 rounded bg-[#1E293B] border border-slate-700/60 flex items-center justify-between"
                  >
                    <span className="font-mono text-slate-400 text-[11px]">{status}</span>
                    <span className="font-mono font-bold text-white">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Multi-Engine Correlation & Security Health Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Nmap Engine */}
        <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] space-y-2">
          <div className="flex items-center gap-2 text-xs font-mono text-sky-400 uppercase">
            <Server className="h-4 w-4" /> Discovery & Port Engine
          </div>
          <div className="text-sm font-semibold text-white">Nmap Network Scanner</div>
          <div className="text-xs text-slate-400 space-y-1 pt-1 font-mono">
            <div>Aset Terdaftar: {totalAssets}</div>
            <div>Aset Aktif (UP): {upAssets}</div>
            <div>Status Otorisasi: Valid CIDR</div>
          </div>
        </div>

        {/* Deep Eye Engine */}
        <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] space-y-2">
          <div className="flex items-center gap-2 text-xs font-mono text-purple-400 uppercase">
            <Globe className="h-4 w-4" /> Web App Security Engine
          </div>
          <div className="text-sm font-semibold text-white">Deep Eye Inspector</div>
          <div className="text-xs text-slate-400 space-y-1 pt-1 font-mono">
            <div>Target Web: {webStats?.total_targets ?? 0}</div>
            <div>Temuan Kerentanan: {webStats?.total_findings ?? 0}</div>
            <div>Kritis / Tinggi: {webStats?.critical_findings ?? 0} / {webStats?.high_findings ?? 0}</div>
          </div>
        </div>

        {/* AI Triage Subsystem */}
        <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] space-y-2">
          <div className="flex items-center gap-2 text-xs font-mono text-amber-400 uppercase">
            <BrainCircuit className="h-4 w-4" /> AI Triage & Correlation
          </div>
          <div className="text-sm font-semibold text-white">Security Intelligence Engine</div>
          <div className="text-xs text-slate-400 space-y-1 pt-1 font-mono">
            <div>Bukti Terkorelasi: {intelOverview?.total_evidence_items ?? 0}</div>
            <div>Triage Berjalan: {intelOverview?.incidents_with_triage ?? 0}</div>
            <div>Mode Inferensi: {intelOverview?.ai_provider_status ?? 'rule_based'}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
