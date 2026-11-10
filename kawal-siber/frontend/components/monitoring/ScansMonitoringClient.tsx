'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Radar,
  RefreshCw,
  Search,
  ExternalLink,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Info,
  Server,
} from 'lucide-react';
import type { Asset, ScanJob, ScanResult } from '@/types';
import ScanJobStatusBadge from '@/components/ui/ScanJobStatusBadge';
import EmptyState from '@/components/ui/EmptyState';
import { getScanResults, getScans } from '@/lib/api';
import { formatDateTime, formatResponseTime } from '@/lib/utils';

interface ScansMonitoringClientProps {
  initialJobs: ScanJob[];
  assets: Asset[];
}

export default function ScansMonitoringClient({
  initialJobs,
  assets,
}: ScansMonitoringClientProps) {
  const router = useRouter();
  const [jobs, setJobs] = useState<ScanJob[]>(initialJobs);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Selected job for results viewing
  const [selectedJob, setSelectedJob] = useState<ScanJob | null>(null);
  const [selectedResults, setSelectedResults] = useState<ScanResult[]>([]);
  const [isLoadingResults, setIsLoadingResults] = useState(false);

  const refreshJobs = async () => {
    setIsRefreshing(true);
    try {
      const updated = await getScans({ limit: 100 });
      setJobs(updated);
    } catch (err) {
      console.error('Failed to poll scans:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Auto-polling when there are active jobs (PENDING or RUNNING)
  useEffect(() => {
    const hasActiveJobs = jobs.some(
      (j) => j.status === 'PENDING' || j.status === 'RUNNING'
    );
    if (!hasActiveJobs) return;

    const interval = setInterval(() => {
      refreshJobs();
    }, 4000);

    return () => clearInterval(interval);
  }, [jobs]);

  const handleViewResults = async (job: ScanJob) => {
    setSelectedJob(job);
    setIsLoadingResults(true);
    try {
      const findings = await getScanResults(job.id);
      setSelectedResults(findings);
    } catch (err) {
      console.error('Failed to fetch findings for job', job.id, err);
      setSelectedResults([]);
    } finally {
      setIsLoadingResults(false);
    }
  };

  const filteredJobs = jobs.filter((job) => {
    const asset = assets.find((a) => a.id === job.asset_id);
    const assetName = asset?.name || '';
    const matchSearch =
      String(job.id).includes(search) ||
      assetName.toLowerCase().includes(search.toLowerCase()) ||
      (job.resolved_ip && job.resolved_ip.includes(search));
    const matchStatus = statusFilter === 'ALL' || job.status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <div className="space-y-6">
      {/* Control Bar */}
      <div className="glass-card rounded-xl border border-[rgba(255,255,255,0.08)] p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#64748B]" />
            <input
              type="text"
              placeholder="Cari Job ID, nama aset, atau IP hasil resolusi..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg bg-[#0F172A] border border-[rgba(255,255,255,0.1)] py-2.5 pl-10 pr-4 text-sm text-[#F8FAFC] placeholder-[#64748B] focus:border-[#22C55E] focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg bg-[#0F172A] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-xs font-mono text-[#CBD5E1] focus:border-[#22C55E] focus:outline-none"
            >
              <option value="ALL">Semua Status Pekerjaan</option>
              <option value="PENDING">PENDING (Menunggu)</option>
              <option value="RUNNING">RUNNING (Memindai)</option>
              <option value="COMPLETED">COMPLETED (Selesai)</option>
              <option value="FAILED">FAILED (Gagal)</option>
            </select>

            <button
              onClick={refreshJobs}
              disabled={isRefreshing}
              className="inline-flex items-center gap-2 rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3.5 py-2 text-xs font-medium text-[#CBD5E1] hover:bg-[#334155] transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin text-[#22C55E]' : ''}`} />
              Segarkan
            </button>
          </div>
        </div>
      </div>

      {/* Jobs Table */}
      <div className="glass-card rounded-xl border border-[rgba(255,255,255,0.08)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.08)] bg-[#0F172A]/70 font-mono text-[#94A3B8] uppercase tracking-wider">
                <th className="px-5 py-3.5">Job ID</th>
                <th className="px-5 py-3.5">Target Aset</th>
                <th className="px-5 py-3.5">Status Pekerjaan</th>
                <th className="px-5 py-3.5">IP Terverifikasi</th>
                <th className="px-5 py-3.5">Durasi</th>
                <th className="px-5 py-3.5">Waktu Antrean</th>
                <th className="px-5 py-3.5">Versi Scanner</th>
                <th className="px-5 py-3.5 text-right">Temuan</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255,255,255,0.04)] font-mono">
              {filteredJobs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-5 py-12 text-center">
                    <EmptyState
                      icon={Radar}
                      title="Tidak Ada Riwayat Pemindaian"
                      description="Belum ada pemindaian yang dijalankan atau cocok dengan filter yang dipilih."
                    />
                  </td>
                </tr>
              ) : (
                filteredJobs.map((job) => {
                  const asset = assets.find((a) => a.id === job.asset_id);
                  return (
                    <tr key={job.id} className="hover:bg-[#1E293B]/40 transition-colors">
                      <td className="px-5 py-3.5 font-bold text-[#F8FAFC]">
                        #{job.id}
                      </td>

                      <td className="px-5 py-3.5 font-sans">
                        {asset ? (
                          <Link
                            href={`/assets/${asset.id}`}
                            className="font-medium text-[#F8FAFC] hover:text-[#22C55E] flex items-center gap-1.5 transition-colors"
                          >
                            <span>{asset.name}</span>
                            <span className="font-mono text-[11px] text-[#64748B]">
                              (:{asset.port})
                            </span>
                          </Link>
                        ) : (
                          <span className="text-[#64748B] italic">Aset #{job.asset_id}</span>
                        )}
                      </td>

                      <td className="px-5 py-3.5">
                        <ScanJobStatusBadge status={job.status} />
                      </td>

                      <td className="px-5 py-3.5 text-[#38BDF8]">
                        {job.resolved_ip || '—'}
                      </td>

                      <td className="px-5 py-3.5 text-[#CBD5E1]">
                        {formatResponseTime(job.duration_ms)}
                      </td>

                      <td className="px-5 py-3.5 text-[#94A3B8]">
                        {formatDateTime(job.created_at)}
                      </td>

                      <td className="px-5 py-3.5 text-[11px] text-[#64748B]">
                        {job.scanner_version || '—'}
                      </td>

                      <td className="px-5 py-3.5 text-right">
                        {job.status === 'COMPLETED' ? (
                          <button
                            onClick={() => handleViewResults(job)}
                            className="inline-flex items-center gap-1 rounded bg-[#1E293B] border border-[rgba(255,255,255,0.08)] px-2.5 py-1 text-xs text-[#38BDF8] hover:bg-[#334155] transition-colors"
                          >
                            <Info className="h-3.5 w-3.5" />
                            Hasil
                          </button>
                        ) : job.status === 'FAILED' ? (
                          <span
                            className="text-rose-400 text-[11px] truncate max-w-[120px] inline-block"
                            title={job.error_message || job.error_code || 'Gagal'}
                          >
                            {job.error_code || 'Gagal'}
                          </span>
                        ) : (
                          <span className="text-amber-400 text-[11px] animate-pulse">
                            Memproses...
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Results Detail Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="glass-card w-full max-w-2xl rounded-xl border border-[rgba(255,255,255,0.12)] p-6 shadow-2xl bg-[#0F172A] space-y-4">
            <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.08)] pb-3">
              <div>
                <span className="font-mono text-xs text-[#22C55E]">
                  Hasil Scan #{selectedJob.id}
                </span>
                <h3 className="text-base font-bold text-[#F8FAFC]">
                  Temuan Port & Deteksi Layanan
                </h3>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="text-[#64748B] hover:text-[#F8FAFC]"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-3 gap-3 font-mono text-xs">
              <div className="rounded bg-[#1E293B] p-2.5">
                <span className="text-[#64748B] block text-[10px]">Target IP</span>
                <span className="text-[#38BDF8] font-bold">{selectedJob.resolved_ip}</span>
              </div>
              <div className="rounded bg-[#1E293B] p-2.5">
                <span className="text-[#64748B] block text-[10px]">Durasi Eksekusi</span>
                <span className="text-[#CBD5E1] font-bold">
                  {formatResponseTime(selectedJob.duration_ms)}
                </span>
              </div>
              <div className="rounded bg-[#1E293B] p-2.5">
                <span className="text-[#64748B] block text-[10px]">Status Scan</span>
                <span className="text-emerald-400 font-bold">{selectedJob.status}</span>
              </div>
            </div>

            {/* Findings Table */}
            <div className="rounded-lg border border-[rgba(255,255,255,0.08)] overflow-hidden">
              <table className="w-full border-collapse text-left text-xs font-mono">
                <thead>
                  <tr className="bg-[#1E293B]/70 border-b border-[rgba(255,255,255,0.06)] text-[#94A3B8]">
                    <th className="p-3">Port</th>
                    <th className="p-3">State</th>
                    <th className="p-3">Service</th>
                    <th className="p-3">Product / Version</th>
                    <th className="p-3">Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(255,255,255,0.04)]">
                  {isLoadingResults ? (
                    <tr>
                      <td colSpan={5} className="p-6 text-center text-[#64748B]">
                        Memuat data temuan...
                      </td>
                    </tr>
                  ) : selectedResults.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-6 text-center text-[#64748B]">
                        Tidak ada port terbuka yang ditemukan atau port ditutup oleh target host.
                      </td>
                    </tr>
                  ) : (
                    selectedResults.map((r) => (
                      <tr key={r.id} className="hover:bg-[#1E293B]/30">
                        <td className="p-3 font-bold text-[#38BDF8]">
                          {r.port}/{r.protocol}
                        </td>
                        <td className="p-3">
                          <span
                            className={`inline-block rounded px-2 py-0.5 text-[10px] font-bold ${
                              r.state === 'open'
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : 'bg-slate-500/20 text-slate-400'
                            }`}
                          >
                            {r.state.toUpperCase()}
                          </span>
                        </td>
                        <td className="p-3 text-[#F8FAFC]">{r.service_name || '—'}</td>
                        <td className="p-3 text-[#CBD5E1]">
                          {r.product ? `${r.product} ${r.version || ''}` : '—'}
                        </td>
                        <td className="p-3 text-[#64748B]">{r.reason || '—'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setSelectedJob(null)}
                className="rounded-lg bg-[#1E293B] px-4 py-2 text-xs font-medium text-[#CBD5E1] hover:bg-[#334155] transition-colors"
              >
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
