'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  FileText,
  Plus,
  RefreshCw,
  Search,
  Download,
  Eye,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileCheck,
  ShieldAlert,
  BarChart2,
  BrainCircuit,
  Globe,
  SlidersHorizontal,
  Copy,
  ExternalLink,
} from 'lucide-react';
import type {
  GeneratedReport,
  PaginatedReports,
  ReportFormat,
  ReportStatistics,
  ReportType,
} from '@/types';
import { getReports, getReportStatistics, getReportDownloadUrl } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import EmptyState from '@/components/ui/EmptyState';

interface ReportsClientProps {
  initialReports: PaginatedReports;
  initialStats: ReportStatistics;
}

export default function ReportsClient({
  initialReports,
  initialStats,
}: ReportsClientProps) {
  const [reports, setReports] = useState<GeneratedReport[]>(initialReports.items);
  const [stats, setStats] = useState<ReportStatistics>(initialStats);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [formatFilter, setFormatFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchLatest = useCallback(async () => {
    try {
      setLoading(true);
      const [reps, st] = await Promise.all([
        getReports({ page_size: 100 }),
        getReportStatistics(),
      ]);
      setReports(reps.items);
      setStats(st);
    } catch (err) {
      console.error('Error refreshing reports:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll if any report is PENDING or RUNNING
  useEffect(() => {
    const hasActiveJobs = reports.some(
      (r) => r.generation_status === 'PENDING' || r.generation_status === 'RUNNING',
    );
    if (!hasActiveJobs) return;

    const timer = setInterval(() => {
      fetchLatest();
    }, 4000);

    return () => clearInterval(timer);
  }, [reports, fetchLatest]);

  const copyChecksum = (hash: string, id: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  const filteredReports = reports.filter((r) => {
    const matchesSearch =
      r.title.toLowerCase().includes(search.toLowerCase()) ||
      r.report_id.toLowerCase().includes(search.toLowerCase()) ||
      r.generated_by.toLowerCase().includes(search.toLowerCase());

    const matchesType = typeFilter === 'ALL' || r.report_type === typeFilter;
    const matchesFormat = formatFilter === 'ALL' || r.format === formatFilter;
    const matchesStatus = statusFilter === 'ALL' || r.generation_status === statusFilter;

    return matchesSearch && matchesType && matchesFormat && matchesStatus;
  });

  const getFormatBadge = (fmt: ReportFormat) => {
    switch (fmt) {
      case 'PDF':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-red-950/50 text-red-400 border border-red-500/30">
            PDF
          </span>
        );
      case 'HTML':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-sky-950/50 text-sky-400 border border-sky-500/30">
            HTML
          </span>
        );
      case 'JSON':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-950/50 text-emerald-400 border border-emerald-500/30">
            JSON
          </span>
        );
      case 'CSV':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-amber-950/50 text-amber-400 border border-amber-500/30">
            CSV
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300">
            {fmt}
          </span>
        );
    }
  };

  const getTypeIcon = (type: ReportType) => {
    switch (type) {
      case 'EXECUTIVE':
        return <FileCheck className="h-4 w-4 text-purple-400" />;
      case 'TECHNICAL':
        return <ShieldAlert className="h-4 w-4 text-rose-400" />;
      case 'ASSESSMENT':
        return <Globe className="h-4 w-4 text-sky-400" />;
      case 'OPERATIONS':
        return <BarChart2 className="h-4 w-4 text-emerald-400" />;
      case 'AI_INTELLIGENCE':
        return <BrainCircuit className="h-4 w-4 text-amber-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="h-3.5 w-3.5" /> Selesai
          </span>
        );
      case 'RUNNING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-950/60 text-blue-400 border border-blue-500/30 animate-pulse">
            <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Memproses
          </span>
        );
      case 'PENDING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
            <Clock className="h-3.5 w-3.5" /> Antrean
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-950/60 text-rose-400 border border-rose-500/30">
            <AlertCircle className="h-3.5 w-3.5" /> Gagal
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-400">
            {status}
          </span>
        );
    }
  };

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="space-y-6">
      {/* Top Action & Summary Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400 font-mono uppercase tracking-wider">
              Total Laporan
            </div>
            <div className="text-2xl font-bold text-white mt-1">
              {stats.total_reports}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-400">
            <FileText className="h-6 w-6" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400 font-mono uppercase tracking-wider">
              Laporan Selesai
            </div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">
              {stats.completed_reports}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-400">
            <CheckCircle2 className="h-6 w-6" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400 font-mono uppercase tracking-wider">
              Dalam Antrean
            </div>
            <div className="text-2xl font-bold text-amber-400 mt-1">
              {stats.pending_reports}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-amber-500/10 text-amber-400">
            <Clock className="h-6 w-6" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400 font-mono uppercase tracking-wider">
              Gagal Generate
            </div>
            <div className="text-2xl font-bold text-rose-400 mt-1">
              {stats.failed_reports}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-rose-500/10 text-rose-400">
            <AlertCircle className="h-6 w-6" />
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-1 flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Cari laporan berdasarkan judul, ID, atau operator..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-lg bg-[#1E293B] border border-slate-700 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-emerald-500 transition-colors"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-3 py-2 rounded-lg bg-[#1E293B] border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="ALL">Semua Tipe</option>
              <option value="EXECUTIVE">Eksekutif</option>
              <option value="TECHNICAL">Teknis Insiden</option>
              <option value="ASSESSMENT">Asesmen Keamanan</option>
              <option value="OPERATIONS">Operasional SOC</option>
              <option value="AI_INTELLIGENCE">AI Intelligence</option>
            </select>

            <select
              value={formatFilter}
              onChange={(e) => setFormatFilter(e.target.value)}
              className="px-3 py-2 rounded-lg bg-[#1E293B] border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="ALL">Semua Format</option>
              <option value="PDF">PDF</option>
              <option value="HTML">HTML</option>
              <option value="JSON">JSON</option>
              <option value="CSV">CSV</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 rounded-lg bg-[#1E293B] border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="ALL">Semua Status</option>
              <option value="COMPLETED">Selesai</option>
              <option value="PENDING">Antrean</option>
              <option value="RUNNING">Memproses</option>
              <option value="FAILED">Gagal</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchLatest}
            disabled={loading}
            className="p-2.5 rounded-lg bg-[#1E293B] hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-colors disabled:opacity-50"
            title="Refresh Laporan"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <Link
            href="/reports/create"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors shadow-lg shadow-emerald-950/40"
          >
            <Plus className="h-4 w-4" /> Buat Laporan Baru
          </Link>
        </div>
      </div>

      {/* Reports Table */}
      {filteredReports.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="Tidak Ada Laporan Ditemukan"
          description={
            search || typeFilter !== 'ALL' || formatFilter !== 'ALL' || statusFilter !== 'ALL'
              ? 'Tidak ada laporan yang sesuai dengan kriteria filter saat ini.'
              : 'Belum ada laporan keamanan yang dibuat. Klik tombol di bawah untuk membuat laporan pertama Anda.'
          }
          action={
            <Link
              href="/reports/create"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors"
            >
              <Plus className="h-4 w-4" /> Buat Laporan Sekarang
            </Link>
          }
        />
      ) : (
        <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#1E293B]/70 border-b border-[rgba(255,255,255,0.06)] text-xs text-slate-400 uppercase tracking-wider font-mono">
                <tr>
                  <th className="px-5 py-3">ID / Tipe Laporan</th>
                  <th className="px-5 py-3">Judul Laporan</th>
                  <th className="px-5 py-3">Format</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Ukuran & Sumber</th>
                  <th className="px-5 py-3">Audit Checksum (SHA-256)</th>
                  <th className="px-5 py-3">Waktu Dibuat</th>
                  <th className="px-5 py-3 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(255,255,255,0.04)] text-slate-300">
                {filteredReports.map((r) => (
                  <tr
                    key={r.id}
                    className="hover:bg-[#1E293B]/40 transition-colors"
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        {getTypeIcon(r.report_type)}
                        <div>
                          <div className="font-mono text-xs text-white font-medium">
                            {r.report_id}
                          </div>
                          <div className="text-[11px] text-slate-400 capitalize">
                            {r.report_type.toLowerCase().replace('_', ' ')}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="px-5 py-4">
                      <Link
                        href={`/reports/${r.id}`}
                        className="font-medium text-white hover:text-emerald-400 transition-colors line-clamp-1"
                      >
                        {r.title}
                      </Link>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        Oleh: <span className="text-slate-300">{r.generated_by}</span>
                      </div>
                    </td>

                    <td className="px-5 py-4">{getFormatBadge(r.format)}</td>

                    <td className="px-5 py-4">{getStatusBadge(r.generation_status)}</td>

                    <td className="px-5 py-4">
                      <div className="text-xs font-mono text-slate-200">
                        {formatFileSize(r.file_size)}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {r.source_count} item bukti
                      </div>
                    </td>

                    <td className="px-5 py-4">
                      {r.sha256_checksum ? (
                        <div className="flex items-center gap-1.5">
                          <code
                            className="text-[11px] font-mono text-slate-400 bg-black/40 px-1.5 py-0.5 rounded border border-slate-800"
                            title={r.sha256_checksum}
                          >
                            {r.sha256_checksum.slice(0, 10)}…{r.sha256_checksum.slice(-6)}
                          </code>
                          <button
                            onClick={() => copyChecksum(r.sha256_checksum!, String(r.id))}
                            className="p-1 hover:text-emerald-400 text-slate-500 transition-colors"
                            title="Salin Checksum SHA-256"
                          >
                            {copiedId === String(r.id) ? (
                              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="h-3.5 w-3.5" />
                            )}
                          </button>
                        </div>
                      ) : (
                        <span className="text-slate-500 text-xs font-mono">—</span>
                      )}
                    </td>

                    <td className="px-5 py-4 text-xs text-slate-400 font-mono whitespace-nowrap">
                      {formatDateTime(r.created_at)}
                    </td>

                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/reports/${r.id}`}
                          className="p-1.5 rounded-lg bg-[#1E293B] hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                          title="Lihat Detail & Pratinjau"
                        >
                          <Eye className="h-4 w-4" />
                        </Link>

                        {r.generation_status === 'COMPLETED' && (
                          <a
                            href={getReportDownloadUrl(r.id)}
                            download
                            className="p-1.5 rounded-lg bg-emerald-950/60 hover:bg-emerald-900 border border-emerald-500/30 text-emerald-400 hover:text-emerald-300 transition-colors"
                            title="Unduh Berkas Laporan"
                          >
                            <Download className="h-4 w-4" />
                          </a>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
