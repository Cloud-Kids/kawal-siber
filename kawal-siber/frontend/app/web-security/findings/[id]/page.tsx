'use client';

import { useState, useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import { getWebFinding, updateWebFindingStatus } from '@/lib/api';
import type { WebFinding } from '@/types';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Bug,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  FileCode,
  ExternalLink,
  Fingerprint,
  Clock,
  Layers,
} from 'lucide-react';

export default function WebFindingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const findingId = Number(params?.id);

  const [finding, setFinding] = useState<WebFinding | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingStatus, setSavingStatus] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  async function loadFinding() {
    if (!findingId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getWebFinding(findingId);
      setFinding(data);
      setSelectedStatus(data.finding_status);
    } catch (err: any) {
      setError(err?.message || 'Gagal memuat detail temuan kerentanan.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFinding();
  }, [findingId]);

  async function handleUpdateStatus() {
    if (!finding || !selectedStatus) return;
    setSavingStatus(true);
    setSuccessMsg(null);
    setError(null);
    try {
      const updated = await updateWebFindingStatus(finding.id, selectedStatus);
      setFinding(updated);
      setSuccessMsg(`Status triase berhasil diperbarui menjadi ${updated.finding_status}.`);
    } catch (err: any) {
      setError(err?.message || 'Gagal memperbarui status temuan.');
    } finally {
      setSavingStatus(false);
    }
  }

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return 'bg-[#EF4444]/20 text-[#EF4444] border-[#EF4444]/40';
      case 'HIGH':
        return 'bg-[#F97316]/20 text-[#F97316] border-[#F97316]/40';
      case 'MEDIUM':
        return 'bg-[#F59E0B]/20 text-[#F59E0B] border-[#F59E0B]/40';
      case 'LOW':
        return 'bg-[#3B82F6]/20 text-[#60A5FA] border-[#3B82F6]/40';
      default:
        return 'bg-[#64748B]/20 text-[#94A3B8] border-[#64748B]/40';
    }
  };

  return (
    <AppShell>
      <Header title="Detail Temuan Kerentanan Web" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Back Link */}
        <div>
          <Link
            href="/web-security/findings"
            className="inline-flex items-center gap-1.5 text-xs text-[#94A3B8] hover:text-[#F8FAFC] transition-colors font-medium"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Kembali ke Katalog Temuan
          </Link>
        </div>

        {/* Notifications */}
        {error && (
          <div className="p-4 rounded-xl bg-[#EF4444]/15 border border-[#EF4444]/30 text-[#EF4444] text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {successMsg && (
          <div className="p-4 rounded-xl bg-[#22C55E]/15 border border-[#22C55E]/30 text-[#22C55E] text-xs flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {loading ? (
          <div className="p-16 text-center text-xs text-[#64748B]">Memuat detail kerentanan...</div>
        ) : !finding ? (
          <div className="p-16 text-center text-xs text-[#EF4444]">Temuan kerentanan tidak ditemukan.</div>
        ) : (
          <div className="space-y-6">
            {/* Header Card */}
            <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-6 space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2.5 py-0.5 rounded text-[11px] font-mono font-bold border ${getSeverityBadge(
                        finding.severity,
                      )}`}
                    >
                      {finding.severity}
                    </span>
                    <span className="px-2.5 py-0.5 rounded text-[11px] font-mono bg-[#1E293B] text-[#94A3B8] border border-[rgba(255,255,255,0.08)]">
                      {finding.vulnerability_type}
                    </span>
                    <span className="px-2.5 py-0.5 rounded text-[11px] font-mono bg-[#3B82F6]/15 text-[#60A5FA]">
                      Confidence: {finding.confidence}
                    </span>
                  </div>
                  <h1 className="text-xl font-bold text-[#F8FAFC]">{finding.title}</h1>
                  <p className="text-xs font-mono text-[#38BDF8] break-all">{finding.affected_url}</p>
                </div>

                {/* Triage Status Control Box */}
                <div className="p-3 rounded-xl bg-[#1E293B]/60 border border-[rgba(255,255,255,0.06)] space-y-2 min-w-[240px]">
                  <label className="block text-[11px] font-semibold text-[#CBD5E1]">Triase / Status Temuan</label>
                  <div className="flex items-center gap-2">
                    <select
                      value={selectedStatus}
                      onChange={(e) => setSelectedStatus(e.target.value)}
                      className="flex-1 px-2.5 py-1.5 rounded-lg bg-[#0F172A] border border-[rgba(255,255,255,0.1)] text-xs text-[#F8FAFC] focus:outline-none focus:border-[#22C55E]"
                    >
                      <option value="UNVERIFIED">UNVERIFIED</option>
                      <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
                      <option value="CONFIRMED">CONFIRMED</option>
                      <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
                      <option value="ACCEPTED_RISK">ACCEPTED_RISK</option>
                    </select>
                    <button
                      onClick={handleUpdateStatus}
                      disabled={savingStatus || selectedStatus === finding.finding_status}
                      className="px-3 py-1.5 rounded-lg text-xs font-bold bg-[#22C55E] text-[#0F172A] hover:bg-[#16A34A] transition-colors disabled:opacity-40"
                    >
                      {savingStatus ? '...' : 'Simpan'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Metadata strip */}
              <div className="pt-3 border-t border-[rgba(255,255,255,0.06)] grid grid-cols-1 sm:grid-cols-3 gap-3 text-[11px] font-mono text-[#64748B]">
                <div className="flex items-center gap-1.5">
                  <Fingerprint className="h-3.5 w-3.5 text-[#A855F7]" />
                  <span className="truncate">FP: {finding.fingerprint}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5 text-[#3B82F6]" />
                  <span>Pertama Dilihat: {new Date(finding.first_seen).toLocaleDateString('id-ID')}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Layers className="h-3.5 w-3.5 text-[#22C55E]" />
                  <span>Asesmen ID #{finding.assessment_id}</span>
                </div>
              </div>
            </div>

            {/* Description & Impact */}
            <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-5 space-y-3">
              <h2 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
                <Bug className="h-4 w-4 text-[#F59E0B]" />
                Deskripsi Temuan Kerentanan
              </h2>
              <p className="text-xs text-[#CBD5E1] leading-relaxed whitespace-pre-wrap">{finding.description}</p>
            </div>

            {/* Sanitized Evidence */}
            {finding.evidence && (
              <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
                    <FileCode className="h-4 w-4 text-[#38BDF8]" />
                    Bukti Respon / Evidence (Tersanitasi)
                  </h2>
                  <span className="text-[10px] font-mono text-[#64748B]">
                    Token, kredensial, dan cookie otomatis disensor
                  </span>
                </div>
                <pre className="p-4 rounded-lg bg-[#050B14] border border-[rgba(255,255,255,0.06)] text-xs font-mono text-[#A7F3D0] overflow-x-auto whitespace-pre-wrap">
                  {finding.evidence}
                </pre>
              </div>
            )}

            {/* Remediation & Mitigation */}
            <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-5 space-y-3">
              <h2 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-[#22C55E]" />
                Rekomendasi Remediasi
              </h2>
              <p className="text-xs text-[#CBD5E1] leading-relaxed">
                {finding.remediation || 'Tinjau konfigurasi web server dan headers aplikasi terkait.'}
              </p>

              {finding.reference && (
                <div className="pt-2">
                  <a
                    href={finding.reference}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-[#38BDF8] hover:underline"
                  >
                    Dokumentasi / Referensi Terkait <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </AppShell>
  );
}

