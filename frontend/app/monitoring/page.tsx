import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import { getMonitoringStatistics } from '@/lib/api';
import type { MonitoringStatistics } from '@/types';
import Link from 'next/link';
import {
  ShieldAlert,
  Activity,
  Radio,
  FileSearch,
  ExternalLink,
  Flame,
  CheckCircle2,
  AlertOctagon,
} from 'lucide-react';

export const dynamic = 'force-dynamic';

export default async function MonitoringPage() {
  let stats: MonitoringStatistics = {
    total_events: 0,
    total_alerts: 0,
    total_pcap_analyses: 0,
    severity_distribution: { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 },
    protocol_distribution: {},
    event_type_distribution: {},
    top_signatures: [],
    correlated_incidents_count: 0,
  };

  try {
    const s = await getMonitoringStatistics();
    stats = s;
  } catch {
    // Graceful fallback if backend just restarted
  }

  const sevCrit = stats.severity_distribution['CRITICAL'] || 0;
  const sevHigh = stats.severity_distribution['HIGH'] || 0;
  const sevMed = stats.severity_distribution['MEDIUM'] || 0;
  const sevLow = stats.severity_distribution['LOW'] || 0;
  const totalSev = sevCrit + sevHigh + sevMed + sevLow || 1;

  return (
    <AppShell>
      <Header title="Monitoring Ancaman Jaringan — Suricata IDS" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Banner Status IDS Engine */}
        <div className="rounded-xl border border-[#22C55E]/30 bg-gradient-to-r from-[#0F172A] via-[#1E293B] to-[#0F172A] p-5 shadow-lg">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#22C55E]/20 text-[#22C55E] border border-[#22C55E]/40">
                <Radio className="h-5 w-5 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-[#F8FAFC]">Suricata IDS Engine (Offline PCAP Analyzer)</h2>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-[#22C55E]/20 text-[#22C55E] border border-[#22C55E]/30">
                    AKTIF & TERVALIDASI
                  </span>
                </div>
                <p className="text-xs text-[#94A3B8]">
                  Mesin pendeteksi ancaman jaringan berbasis signature dan inspeksi protokol EVE JSON v8.0.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/monitoring/pcap"
                className="inline-flex items-center gap-2 rounded-lg bg-[#22C55E] px-4 py-2 text-xs font-semibold text-[#0F172A] hover:bg-[#16A34A] transition-colors shadow-sm"
              >
                <FileSearch className="h-4 w-4" />
                Analisis PCAP Baru
              </Link>
              <Link
                href="/monitoring/alerts"
                className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.1)] bg-[#1E293B] px-4 py-2 text-xs font-semibold text-[#CBD5E1] hover:bg-[#334155] transition-colors"
              >
                <ShieldAlert className="h-4 w-4 text-[#EF4444]" />
                Lihat Peringatan
              </Link>
            </div>
          </div>
        </div>

        {/* 4 KPI Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 p-4 backdrop-blur-sm">
            <span className="text-xs font-mono text-[#94A3B8] uppercase">Total Event Telemetri</span>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-2xl font-bold font-mono text-[#F8FAFC]">{stats.total_events}</span>
              <Activity className="h-5 w-5 text-[#38BDF8]" />
            </div>
            <p className="mt-1 text-[11px] text-[#64748B]">Semua protokol (Flow, DNS, HTTP, TLS)</p>
          </div>

          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 p-4 backdrop-blur-sm">
            <span className="text-xs font-mono text-[#94A3B8] uppercase">Peringatan Siber (Alerts)</span>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-2xl font-bold font-mono text-[#EF4444]">{stats.total_alerts}</span>
              <ShieldAlert className="h-5 w-5 text-[#EF4444]" />
            </div>
            <p className="mt-1 text-[11px] text-[#64748B]">Ancaman terdeteksi oleh signature</p>
          </div>

          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 p-4 backdrop-blur-sm">
            <span className="text-xs font-mono text-[#94A3B8] uppercase">Analisis PCAP Selesai</span>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-2xl font-bold font-mono text-[#22C55E]">{stats.total_pcap_analyses}</span>
              <FileSearch className="h-5 w-5 text-[#22C55E]" />
            </div>
            <p className="mt-1 text-[11px] text-[#64748B]">Berkas lalu lintas dianalisis</p>
          </div>

          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 p-4 backdrop-blur-sm">
            <span className="text-xs font-mono text-[#94A3B8] uppercase">Korelasi Insiden Aset</span>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-2xl font-bold font-mono text-[#F59E0B]">{stats.correlated_incidents_count}</span>
              <AlertOctagon className="h-5 w-5 text-[#F59E0B]" />
            </div>
            <p className="mt-1 text-[11px] text-[#64748B]">Dihubungkan ke inventori aset</p>
          </div>
        </div>

        {/* Severity Distribution & Protocol Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Severity Meter */}
          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 p-5">
            <h3 className="text-sm font-semibold text-[#F8FAFC] mb-4 flex items-center gap-2">
              <Flame className="h-4 w-4 text-[#F59E0B]" />
              Distribusi Tingkat Keparahan Ancaman
            </h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-[#EF4444] font-semibold">CRITICAL (Kritis)</span>
                  <span className="text-[#CBD5E1]">{sevCrit} ({Math.round((sevCrit / totalSev) * 100)}%)</span>
                </div>
                <div className="w-full h-2 rounded-full bg-[#334155] overflow-hidden">
                  <div className="h-full bg-[#EF4444]" style={{ width: `${(sevCrit / totalSev) * 100}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-[#F97316] font-semibold">HIGH (Tinggi)</span>
                  <span className="text-[#CBD5E1]">{sevHigh} ({Math.round((sevHigh / totalSev) * 100)}%)</span>
                </div>
                <div className="w-full h-2 rounded-full bg-[#334155] overflow-hidden">
                  <div className="h-full bg-[#F97316]" style={{ width: `${(sevHigh / totalSev) * 100}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-[#F59E0B] font-semibold">MEDIUM (Sedang)</span>
                  <span className="text-[#CBD5E1]">{sevMed} ({Math.round((sevMed / totalSev) * 100)}%)</span>
                </div>
                <div className="w-full h-2 rounded-full bg-[#334155] overflow-hidden">
                  <div className="h-full bg-[#F59E0B]" style={{ width: `${(sevMed / totalSev) * 100}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-[#38BDF8] font-semibold">LOW / INFORMATIONAL (Rendah)</span>
                  <span className="text-[#CBD5E1]">{sevLow} ({Math.round((sevLow / totalSev) * 100)}%)</span>
                </div>
                <div className="w-full h-2 rounded-full bg-[#334155] overflow-hidden">
                  <div className="h-full bg-[#38BDF8]" style={{ width: `${(sevLow / totalSev) * 100}%` }} />
                </div>
              </div>
            </div>
          </div>

          {/* Protocol Distribution */}
          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 p-5">
            <h3 className="text-sm font-semibold text-[#F8FAFC] mb-4 flex items-center gap-2">
              <Activity className="h-4 w-4 text-[#38BDF8]" />
              Sebaran Protokol Jaringan Terdeteksi
            </h3>
            {Object.keys(stats.protocol_distribution).length === 0 ? (
              <p className="text-xs text-[#64748B] py-6 text-center">Belum ada telemetri protokol tercatat.</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {Object.entries(stats.protocol_distribution).map(([proto, count]) => (
                  <div key={proto} className="rounded-lg bg-[#0F172A]/70 border border-[rgba(255,255,255,0.04)] p-3">
                    <span className="block text-[11px] font-mono text-[#94A3B8]">{proto}</span>
                    <span className="text-lg font-bold font-mono text-[#F8FAFC]">{count as number}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Top Detected Signatures */}
        <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[#F8FAFC] flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-[#EF4444]" />
              Top 10 Signature Ancaman Terdeteksi
            </h3>
            <Link href="/monitoring/alerts" className="text-xs text-[#38BDF8] hover:underline flex items-center gap-1">
              Semua Peringatan <ExternalLink className="h-3 w-3" />
            </Link>
          </div>

          {stats.top_signatures.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle2 className="h-8 w-8 text-[#22C55E] mx-auto mb-2 opacity-80" />
              <p className="text-xs text-[#94A3B8]">Tidak ada peringatan aktif. Jalankan analisis PCAP untuk mendeteksi ancaman.</p>
            </div>
          ) : (
            <div className="divide-y divide-[rgba(255,255,255,0.04)] overflow-x-auto">
              {stats.top_signatures.map((sig, idx) => (
                <div key={idx} className="py-2.5 flex items-center justify-between gap-4 text-xs">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-[#E2E8F0] truncate">{sig.signature}</p>
                    <span className="text-[11px] text-[#64748B] font-mono">{sig.category || 'Unclassified'}</span>
                  </div>
                  <span className="px-2 py-0.5 rounded font-mono font-bold bg-[#EF4444]/15 text-[#EF4444] border border-[#EF4444]/30 shrink-0">
                    {sig.count}x terdeteksi
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </AppShell>
  );
}
