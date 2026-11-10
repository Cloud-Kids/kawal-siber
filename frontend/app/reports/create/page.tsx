'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import {
  FileText,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  FileCheck,
  ShieldAlert,
  Globe,
  BarChart2,
  BrainCircuit,
  Calendar,
  Sparkles,
  Send,
  Loader2,
} from 'lucide-react';
import { createReport } from '@/lib/api';
import type { ReportFormat, ReportType } from '@/types';

export default function CreateReportPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form State
  const [reportType, setReportType] = useState<ReportType>('EXECUTIVE');
  const [format, setFormat] = useState<ReportFormat>('PDF');
  const [title, setTitle] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [includeAiNarrative, setIncludeAiNarrative] = useState(true);
  const [customNotes, setCustomNotes] = useState('');
  const [generatedBy, setGeneratedBy] = useState('Operator SOC KAWAL SIBER');

  const reportTypes = [
    {
      id: 'EXECUTIVE' as ReportType,
      name: 'Laporan Eksekutif',
      icon: FileCheck,
      color: 'purple',
      badge: 'C-Level & Komando',
      description:
        'Ringkasan strategis postur keamanan, tren insiden teratas, status ketersediaan aset, dan ringkasan risiko makro.',
    },
    {
      id: 'TECHNICAL' as ReportType,
      name: 'Laporan Teknis Insiden',
      icon: ShieldAlert,
      color: 'rose',
      badge: 'Investigasi & DFIR',
      description:
        'Analisis forensik mendalam seluruh insiden siber, korelasi bukti multi-sumber, IOC, payload, dan timeline kejadian.',
    },
    {
      id: 'ASSESSMENT' as ReportType,
      name: 'Laporan Asesmen Keamanan',
      icon: Globe,
      color: 'sky',
      badge: 'Vulnerability Management',
      description:
        'Kompilasi komprehensif hasil temuan Deep Eye, pemindaian port Nmap, audit HTTP headers, dan matriks kelemahan.',
    },
    {
      id: 'OPERATIONS' as ReportType,
      name: 'Laporan Operasional SOC',
      icon: BarChart2,
      color: 'emerald',
      badge: 'Telemetry & Monitoring',
      description:
        'Metrik operasional telemetri Suricata IDS, volume event, throughput jaringan, efektivitas penanganan, dan MTTR.',
    },
    {
      id: 'AI_INTELLIGENCE' as ReportType,
      name: 'Laporan AI Intelligence',
      icon: BrainCircuit,
      color: 'amber',
      badge: 'Threat Intelligence',
      description:
        'Hasil triage mesin inferensi AI/heuristic, klasifikasi taktik ancaman, skor prioritas, dan rekomendasi mitigasi terkurasi.',
    },
  ];

  const formats: { id: ReportFormat; label: string; desc: string }[] = [
    { id: 'PDF', label: 'PDF Document', desc: 'Standar dokumen formal audit dan cetak (ReportLab)' },
    { id: 'HTML', label: 'HTML Interactive', desc: 'Tampilan web responsif dengan styling KAWAL SIBER' },
    { id: 'JSON', label: 'JSON Machine-Readable', desc: 'Format data terstruktur untuk integrasi SIEM / API eksternal' },
    { id: 'CSV', label: 'CSV Spreadsheet', desc: 'Format tabular tabular dengan sanitasi formula injection' },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setErrorMsg(null);

      await createReport({
        report_type: reportType,
        format,
        title: title.trim() || undefined,
        period_start: periodStart ? new Date(periodStart).toISOString() : undefined,
        period_end: periodEnd ? new Date(periodEnd).toISOString() : undefined,
        include_ai_narrative: includeAiNarrative,
        custom_notes: customNotes.trim() || undefined,
        generated_by: generatedBy.trim() || 'Operator SOC KAWAL SIBER',
      });

      router.push('/reports');
    } catch (err: any) {
      console.error('Failed to create report:', err);
      setErrorMsg(err.message || 'Gagal mengirim permintaan pembuatan laporan');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AppShell>
      <Header title="Report Builder — Buat Laporan Keamanan Otomatis" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6 max-w-5xl mx-auto">
        <div className="flex items-center gap-3">
          <Link
            href="/reports"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Kembali ke Pusat Laporan
          </Link>
        </div>

        {errorMsg && (
          <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-500/30 text-rose-200 text-sm flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-rose-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Step 1: Pilih Tipe Laporan */}
          <div className="p-5 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider font-mono">
                1. Pilih Jenis Laporan Keamanan
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Setiap jenis laporan mengompilasi dan mengagregasi data snapshot yang berbeda secara otomatis.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {reportTypes.map((t) => {
                const Icon = t.icon;
                const isSelected = reportType === t.id;
                return (
                  <div
                    key={t.id}
                    onClick={() => setReportType(t.id)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all duration-150 flex flex-col justify-between ${
                      isSelected
                        ? 'border-emerald-500 bg-emerald-950/20 shadow-md shadow-emerald-950/30'
                        : 'border-slate-800 bg-[#1E293B]/40 hover:bg-[#1E293B]/80 hover:border-slate-700'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div
                          className={`p-2 rounded-lg ${
                            isSelected
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          <Icon className="h-5 w-5" />
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/40 text-slate-400 border border-slate-800">
                          {t.badge}
                        </span>
                      </div>
                      <h3 className="text-sm font-semibold text-white">{t.name}</h3>
                      <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                        {t.description}
                      </p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-[rgba(255,255,255,0.04)] flex items-center justify-between text-xs">
                      <span className="text-[11px] font-mono text-slate-400">
                        {isSelected ? 'Terpilih' : 'Pilih'}
                      </span>
                      {isSelected && (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Step 2: Pilih Format Output */}
          <div className="p-5 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider font-mono">
                2. Pilih Format Berkas Ekspor
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Semua berkas akan dihitung checksum SHA-256 dan disimpan dalam media penyimpanan audit.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {formats.map((f) => {
                const isSelected = format === f.id;
                return (
                  <div
                    key={f.id}
                    onClick={() => setFormat(f.id)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'border-emerald-500 bg-emerald-950/20'
                        : 'border-slate-800 bg-[#1E293B]/40 hover:bg-[#1E293B]/80'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-bold text-white font-mono">{f.label}</span>
                      {isSelected && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                    </div>
                    <p className="text-xs text-slate-400">{f.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Step 3: Parameter & Metadata Laporan */}
          <div className="p-5 rounded-xl bg-[#0F172A] border border-[rgba(255,255,255,0.06)] space-y-4">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider font-mono">
              3. Parameter & Metadata Laporan
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Judul Kustom (Opsional)
                </label>
                <input
                  type="text"
                  placeholder="Misal: Laporan Audit Keamanan Kuartal IV"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#1E293B] border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Nama Petugas / Operator
                </label>
                <input
                  type="text"
                  value={generatedBy}
                  onChange={(e) => setGeneratedBy(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#1E293B] border border-slate-700 text-sm text-white focus:outline-none focus:border-emerald-500 font-mono"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Periode Awal (Opsional)
                </label>
                <input
                  type="date"
                  value={periodStart}
                  onChange={(e) => setPeriodStart(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#1E293B] border border-slate-700 text-sm text-white focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Periode Akhir (Opsional)
                </label>
                <input
                  type="date"
                  value={periodEnd}
                  onChange={(e) => setPeriodEnd(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#1E293B] border border-slate-700 text-sm text-white focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Catatan Eksekutif Tambahan / Keterangan Auditor (Opsional)
              </label>
              <textarea
                rows={3}
                placeholder="Tambahkan catatan kontekstual yang akan disisipkan ke dalam laporan..."
                value={customNotes}
                onChange={(e) => setCustomNotes(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#1E293B] border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="pt-2 flex items-center gap-3">
              <input
                type="checkbox"
                id="aiNarrativeToggle"
                checked={includeAiNarrative}
                onChange={(e) => setIncludeAiNarrative(e.target.checked)}
                className="h-4 w-4 rounded border-slate-700 bg-[#1E293B] text-emerald-600 focus:ring-emerald-500"
              />
              <label
                htmlFor="aiNarrativeToggle"
                className="text-xs text-slate-300 flex items-center gap-1.5 cursor-pointer"
              >
                <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                Sertakan narasi analisis intelijen AI terkurasi dalam laporan
              </label>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <Link
              href="/reports"
              className="px-5 py-2.5 rounded-lg bg-[#1E293B] hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors"
            >
              Batal
            </Link>

            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors disabled:opacity-50 shadow-lg shadow-emerald-950/40"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Mendaftarkan Antrean...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" /> Mulai Generate Laporan
                </>
              )}
            </button>
          </div>
        </form>
      </main>
    </AppShell>
  );
}

