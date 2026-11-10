'use client';

import { useState, useEffect, use, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import {
  FileText,
  ArrowLeft,
  Download,
  RefreshCw,
  Copy,
  CheckCircle2,
  Clock,
  AlertCircle,
  ShieldCheck,
  Calendar,
  User,
  HardDrive,
  FileCode,
  Eye,
  ExternalLink,
} from 'lucide-react';
import {
  getReport,
  getReportDownloadUrl,
  previewReport,
  regenerateReport,
} from '@/lib/api';
import type { GeneratedReport } from '@/types';
import { formatDateTime } from '@/lib/utils';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

export default function ReportDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const reportId = resolvedParams.id;
  const router = useRouter();

  const [report, setReport] = useState<GeneratedReport | null>(null);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [previewFormat, setPreviewFormat] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [copiedChecksum, setCopiedChecksum] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchReportData = useCallback(async () => {
    try {
      const data = await getReport(reportId);
      setReport(data);

      if (data.generation_status === 'COMPLETED') {
        try {
          setPreviewLoading(true);
          const prev = await previewReport(reportId);
          setPreviewContent(prev.content);
          setPreviewFormat(prev.format);
        } catch (prevErr) {
          console.warn('Preview not available:', prevErr);
        } finally {
          setPreviewLoading(false);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Gagal memuat detail laporan');
    } finally {
      setLoading(false);
    }
  }, [reportId]);

  useEffect(() => {
    fetchReportData();
  }, [fetchReportData]);

  // Polling while RUNNING or PENDING
  useEffect(() => {
    if (!report) return;
    if (report.generation_status === 'RUNNING' || report.generation_status === 'PENDING') {
      const timer = setInterval(() => {
        fetchReportData();
      }, 3000);
      return () => clearInterval(timer);
    }
  }, [report, fetchReportData]);

  const handleCopyChecksum = () => {
    if (!report?.sha256_checksum) return;
    navigator.clipboard.writeText(report.sha256_checksum);
    setCopiedChecksum(true);
    setTimeout(() => setCopiedChecksum(false), 2500);
  };

  const handleRegenerate = async () => {
    if (!report) return;
    try {
      setActionLoading(true);
      const updated = await regenerateReport(report.id);
      setReport(updated);
      setPreviewContent(null);
    } catch (err: any) {
      alert(`Gagal meregenerasi: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  if (loading) {
    return (
      <AppShell>
        <Header title="Memuat Laporan..." />
        <main className="flex-1 flex items-center justify-center p-6">
          <LoadingSpinner label="Mengambil data laporan dan verifikasi checksum..." />
        </main>
      </AppShell>
    );
  }

  if (errorMsg || !report) {
    return (
      <AppShell>
        <Header title="Laporan Tidak Ditemukan" />
        <main className="flex-1 p-6 max-w-4xl mx-auto space-y-4">
          <div className="p-5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-200 flex items-center gap-3">
            <AlertCircle className="h-6 w-6 text-rose-400" />
            <div>
              <h3 className="font-semibold text-white">Gagal Membuka Laporan</h3>
              <p className="text-sm text-rose-300 mt-1">{errorMsg || 'Berkas laporan tidak terdaftar di sistem.'}</p>
            </div>
          </div>
          <Link
            href="/reports"
            className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" /> Kembali ke Pusat Laporan
          </Link>
        </main>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <Header title={`Laporan: ${report.report_id}`} />

      <main className="flex-1 overflow-y-auto p-6 space-y-6 max-w-6xl mx-auto">
        {/* Navigation & Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <Link
              href="/reports"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Kembali ke Pusat Laporan
            </Link>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <FileText className="h-5 w-5 text-emerald-400" />
              {report.title}
            </h1>
            <div className="flex items-center gap-3 text-xs text-slate-400">
              <span className="font-mono text-emerald-400 font-semibold">{report.report_id}</span>
              <span>•</span>
              <span className="capitalize">{report.report_type.toLowerCase().replace('_', ' ')}</span>
              <span>•</span>
              <span className="font-mono font-bold text-slate-300">{report.format}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRegenerate}
              disabled={actionLoading || report.generation_status === 'RUNNING'}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#1E293B] hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${actionLoading ? 'animate-spin' : ''}`} />
              Regenerasi
            </button>

            {report.generation_status === 'COMPLETED' && (
              <a
                href={getReportDownloadUrl(report.id)}
                download
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors shadow-lg shadow-emerald-950/40"
              >
                <Download className="h-3.5 w-3.5" /> Unduh Berkas ({report.format})
              </a>
            )}
          </div>
        </div>

        {/* Status / Processing Banner */}
        {report.generation_status === 'RUNNING' && (
          <div className="p-4 rounded-xl bg-blue-950/50 border border-blue-500/30 text-blue-200 text-sm flex items-center gap-3 animate-pulse">
            <RefreshCw className="h-5 w-5 text-blue-400 animate-spin" />
            <div>
              <span className="font-semibold text-white">Sedang Memproses Laporan: </span>
              Worker sedang mengagregasi data snapshot dan merender berkas format {report.format}...
            </div>
          </div>
        )}

        {report.generation_status === 'PENDING' && (
          <div className="p-4 rounded-xl bg-amber-950/50 border border-amber-500/30 text-amber-200 text-sm flex items-center gap-3">
            <Clock className="h-5 w-5 text-amber-400" />
            <div>
              <span className="font-semibold text-white">Menunggu Antrean Worker: </span>
              Permintaan pembuatan laporan telah dicatat dan menunggu pemrosesan oleh backend worker.
            </div>
          </div>
        )}

        {report.generation_status === 'FAILED' && (
          <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-500/30 text-rose-200 text-sm flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-rose-400 shrink-0" />
            <div>
              <span className="font-semibold text-white">Generasi Laporan Gagal: </span>
              {report.error_message || 'Terjadi kesalahan sistem saat merender laporan.'}
            </div>
          </div>
        )}

        {/* Audit & Integrity Metadata Card */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] space-y-1">
            <div className="text-[11px] font-mono text-slate-400 uppercase flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" /> Integritas Audit
            </div>
            <div className="text-xs font-mono text-slate-200 break-all bg-black/40 p-2 rounded border border-slate-800">
              {report.sha256_checksum ? (
                <div className="flex items-center justify-between gap-1">
                  <span className="truncate">{report.sha256_checksum}</span>
                  <button
                    onClick={handleCopyChecksum}
                    className="p-1 hover:text-emerald-400 text-slate-400 shrink-0"
                    title="Salin Full SHA-256"
                  >
                    {copiedChecksum ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>
              ) : (
                'Menunggu hasil...'
              )}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] space-y-1">
            <div className="text-[11px] font-mono text-slate-400 uppercase flex items-center gap-1.5">
              <HardDrive className="h-3.5 w-3.5 text-sky-400" /> Ukuran Berkas
            </div>
            <div className="text-lg font-bold text-white font-mono">
              {formatFileSize(report.file_size)}
            </div>
            <div className="text-[11px] text-slate-400">
              {report.source_count} item bukti dikompilasi
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] space-y-1">
            <div className="text-[11px] font-mono text-slate-400 uppercase flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-purple-400" /> Waktu Pembuatan
            </div>
            <div className="text-xs font-mono text-slate-200">
              {formatDateTime(report.created_at)}
            </div>
            {report.completed_at && (
              <div className="text-[11px] text-slate-400 font-mono">
                Selesai: {formatDateTime(report.completed_at)}
              </div>
            )}
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] space-y-1">
            <div className="text-[11px] font-mono text-slate-400 uppercase flex items-center gap-1.5">
              <User className="h-3.5 w-3.5 text-amber-400" /> Dibuat Oleh
            </div>
            <div className="text-sm font-semibold text-white truncate">
              {report.generated_by}
            </div>
            <div className="text-[11px] text-slate-400 font-mono">
              Status: {report.generation_status}
            </div>
          </div>
        </div>

        {/* In-Page Preview Container */}
        <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] overflow-hidden">
          <div className="p-4 bg-[#1E293B]/60 border-b border-[rgba(255,255,255,0.06)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Eye className="h-4 w-4 text-emerald-400" />
              <span className="text-xs font-semibold text-white uppercase tracking-wider font-mono">
                Pratinjau Dokumen ({report.format})
              </span>
            </div>

            {report.generation_status === 'COMPLETED' && (
              <a
                href={getReportDownloadUrl(report.id)}
                download
                className="text-xs text-emerald-400 hover:text-emerald-300 font-medium inline-flex items-center gap-1 transition-colors"
              >
                Unduh Berkas <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>

          <div className="p-5">
            {previewLoading ? (
              <div className="flex h-48 items-center justify-center">
                <LoadingSpinner label="Memuat pratinjau dokumen..." />
              </div>
            ) : report.format === 'HTML' && previewContent ? (
              <div className="rounded-lg overflow-hidden border border-slate-800 bg-white">
                <iframe
                  srcDoc={previewContent}
                  title="HTML Report Preview"
                  className="w-full h-[650px] border-0"
                  sandbox="allow-same-origin"
                />
              </div>
            ) : report.format === 'JSON' && previewContent ? (
              <div className="rounded-lg overflow-hidden border border-slate-800 bg-[#090D16] p-4">
                <pre className="font-mono text-xs text-emerald-400 overflow-x-auto max-h-[600px] leading-relaxed">
                  {(() => {
                    try {
                      return JSON.stringify(JSON.parse(previewContent), null, 2);
                    } catch {
                      return previewContent;
                    }
                  })()}
                </pre>
              </div>
            ) : report.format === 'CSV' && previewContent ? (
              <div className="rounded-lg overflow-x-auto border border-slate-800 bg-[#090D16]">
                <table className="w-full text-left text-xs font-mono">
                  <tbody className="divide-y divide-slate-800">
                    {previewContent
                      .split('\n')
                      .filter((row) => row.trim().length > 0)
                      .map((row, idx) => {
                        const cells = row.split(',');
                        if (idx === 0) {
                          return (
                            <tr key={idx} className="bg-slate-800/80 text-emerald-400 font-bold">
                              {cells.map((cell, cidx) => (
                                <th key={cidx} className="px-4 py-2.5 whitespace-nowrap">
                                  {cell.replace(/^"|"$/g, '')}
                                </th>
                              ))}
                            </tr>
                          );
                        }
                        return (
                          <tr key={idx} className="hover:bg-slate-800/30 text-slate-300">
                            {cells.map((cell, cidx) => (
                              <td key={cidx} className="px-4 py-2 whitespace-nowrap">
                                {cell.replace(/^"|"$/g, '')}
                              </td>
                            ))}
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              </div>
            ) : report.format === 'PDF' ? (
              <div className="text-center py-12 space-y-4">
                <div className="p-4 rounded-full bg-red-500/10 text-red-400 inline-block">
                  <FileText className="h-12 w-12" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white">Dokumen PDF Terverifikasi</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
                    Dokumen telah dikompilasi menggunakan ReportLab dengan checksum audit SHA-256. Klik tombol di bawah untuk mengunduh dan membaca PDF.
                  </p>
                </div>
                <div className="pt-2">
                  <a
                    href={getReportDownloadUrl(report.id)}
                    download
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors shadow-lg shadow-emerald-950/40"
                  >
                    <Download className="h-4 w-4" /> Unduh Dokumen PDF ({formatFileSize(report.file_size)})
                  </a>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-xs text-slate-500 font-mono">
                Pratinjau tidak tersedia atau laporan sedang dalam antrean.
              </div>
            )}
          </div>
        </div>
      </main>
    </AppShell>
  );
}

