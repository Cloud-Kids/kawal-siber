'use client';

import { useState, useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import {
  getWebAssessments,
  getWebTargets,
  createWebAssessment,
} from '@/lib/api';
import type { WebAssessment, WebTarget } from '@/types';
import Link from 'next/link';
import {
  ListFilter,
  Play,
  RefreshCw,
  ExternalLink,
  Shield,
  Bug,
  AlertCircle,
  CheckCircle,
  Clock,
  Sparkles,
} from 'lucide-react';

export default function WebAssessmentsPage() {
  const [assessments, setAssessments] = useState<WebAssessment[]>([]);
  const [targets, setTargets] = useState<WebTarget[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Launcher state
  const [selectedTargetId, setSelectedTargetId] = useState<string>('');
  const [selectedProfile, setSelectedProfile] = useState<'PASSIVE' | 'SAFE_LOCAL'>('PASSIVE');
  const [starting, setStarting] = useState(false);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [aData, tData] = await Promise.all([
        getWebAssessments(),
        getWebTargets(),
      ]);
      setAssessments(aData);
      setTargets(tData);
      if (tData.length > 0 && !selectedTargetId) {
        setSelectedTargetId(String(tData[0].id));
      }
    } catch (err: any) {
      setError(err?.message || 'Gagal memuat data asesmen web.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleLaunchAssessment(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedTargetId) {
      setError('Silakan pilih target web terlebih dahulu.');
      return;
    }
    setStarting(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await createWebAssessment({
        web_target_id: Number(selectedTargetId),
        assessment_profile: selectedProfile,
      });
      setSuccessMsg(`Asesmen #${res.id} (${res.assessment_profile}) selesai dieksekusi dengan ${res.total_findings} temuan.`);
      await loadData();
    } catch (err: any) {
      setError(err?.message || 'Gagal memulai asesmen web.');
    } finally {
      setStarting(false);
    }
  }

  const targetMap = new Map<number, WebTarget>(targets.map((t) => [t.id, t]));

  return (
    <AppShell>
      <Header title="Riwayat & Eksekusi Asesmen Web" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Launcher Box */}
        <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-5">
          <h2 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2 mb-3">
            <Sparkles className="h-4 w-4 text-[#3B82F6]" />
            Jalankan Asesmen Keamanan Baru
          </h2>

          <form onSubmit={handleLaunchAssessment} className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs items-end">
            <div className="md:col-span-2">
              <label className="block text-[#94A3B8] font-semibold mb-1">Target Web Terotorisasi</label>
              <select
                value={selectedTargetId}
                onChange={(e) => setSelectedTargetId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] text-[#F8FAFC] focus:outline-none focus:border-[#22C55E]"
              >
                {targets.length === 0 && <option value="">Tidak ada target aktif</option>}
                {targets.map((t) => (
                  <option key={t.id} value={t.id}>
                    #{t.id} {t.name} ({t.target_url})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[#94A3B8] font-semibold mb-1">Profil Asesmen</label>
              <select
                value={selectedProfile}
                onChange={(e) => setSelectedProfile(e.target.value as any)}
                className="w-full px-3 py-2 rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] text-[#F8FAFC] focus:outline-none focus:border-[#22C55E]"
              >
                <option value="PASSIVE">PASSIVE (Header, Cookie, TLS, CORS)</option>
                <option value="SAFE_LOCAL">SAFE LOCAL (Rate-limited, Non-destructive)</option>
              </select>
            </div>

            <div>
              <button
                type="submit"
                disabled={starting || targets.length === 0}
                className="w-full px-4 py-2 rounded-lg bg-[#22C55E] text-[#0F172A] font-bold hover:bg-[#16A34A] transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {starting ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    Menjalankan...
                  </>
                ) : (
                  <>
                    <Play className="h-3.5 w-3.5 fill-current" />
                    Mulai Asesmen
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Alerts */}
        {error && (
          <div className="p-4 rounded-xl bg-[#EF4444]/15 border border-[#EF4444]/30 text-[#EF4444] text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {successMsg && (
          <div className="p-4 rounded-xl bg-[#22C55E]/15 border border-[#22C55E]/30 text-[#22C55E] text-xs flex items-center gap-2">
            <CheckCircle className="h-4 w-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Table Header */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-[#F8FAFC]">Riwayat Seluruh Asesmen</h3>
            <p className="text-xs text-[#94A3B8]">Daftar komprehensif audit keamanan aplikasi web.</p>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#1E293B] text-[#94A3B8] hover:text-[#F8FAFC] border border-[rgba(255,255,255,0.08)] transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Muat Ulang
          </button>
        </div>

        {/* Assessments Table */}
        <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-xs text-[#64748B] flex items-center justify-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin text-[#3B82F6]" />
              Memuat riwayat asesmen...
            </div>
          ) : assessments.length === 0 ? (
            <div className="p-12 text-center text-xs text-[#64748B]">
              Belum ada asesmen yang dijalankan. Gunakan form di atas untuk memulai.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#1E293B]/50 font-mono text-[#94A3B8] border-b border-[rgba(255,255,255,0.06)]">
                  <tr>
                    <th className="p-3">ID</th>
                    <th className="p-3">Target Web</th>
                    <th className="p-3">Profil</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Engine & Versi</th>
                    <th className="p-3">Durasi</th>
                    <th className="p-3">Temuan Kerentanan</th>
                    <th className="p-3">Waktu Pelaksanaan</th>
                    <th className="p-3 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(255,255,255,0.05)] text-[#CBD5E1]">
                  {assessments.map((a) => {
                    const t = targetMap.get(a.web_target_id);
                    return (
                      <tr key={a.id} className="hover:bg-[#1E293B]/30 transition-colors">
                        <td className="p-3 font-mono text-[#64748B]">#{a.id}</td>
                        <td className="p-3">
                          <span className="font-semibold text-[#F8FAFC] block">{t?.name || `Target #${a.web_target_id}`}</span>
                          <span className="text-[11px] font-mono text-[#64748B] truncate block max-w-xs">{t?.target_url}</span>
                        </td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#3B82F6]/10 text-[#60A5FA] border border-[#3B82F6]/20">
                            {a.assessment_profile}
                          </span>
                        </td>
                        <td className="p-3">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                              a.status === 'COMPLETED'
                                ? 'bg-[#22C55E]/15 text-[#22C55E] border border-[#22C55E]/30'
                                : a.status === 'RUNNING'
                                ? 'bg-[#3B82F6]/15 text-[#3B82F6] border border-[#3B82F6]/30 animate-pulse'
                                : 'bg-[#EF4444]/15 text-[#EF4444] border border-[#EF4444]/30'
                            }`}
                          >
                            {a.status}
                          </span>
                        </td>
                        <td className="p-3 font-mono text-[#94A3B8]">
                          {a.tool_name} {a.tool_version || ''}
                        </td>
                        <td className="p-3 font-mono text-[#94A3B8]">{a.duration_ms ? `${a.duration_ms} ms` : '-'}</td>
                        <td className="p-3 font-mono">
                          <span className="font-bold text-[#F8FAFC] mr-2">{a.total_findings}</span>
                          <div className="inline-flex items-center gap-1">
                            {a.critical_count > 0 && (
                              <span className="px-1.5 py-0.2 rounded text-[10px] bg-[#EF4444]/20 text-[#EF4444] font-bold">
                                {a.critical_count}C
                              </span>
                            )}
                            {a.high_count > 0 && (
                              <span className="px-1.5 py-0.2 rounded text-[10px] bg-[#F97316]/20 text-[#F97316] font-bold">
                                {a.high_count}H
                              </span>
                            )}
                            {a.medium_count > 0 && (
                              <span className="px-1.5 py-0.2 rounded text-[10px] bg-[#F59E0B]/20 text-[#F59E0B] font-bold">
                                {a.medium_count}M
                              </span>
                            )}
                            {a.low_count > 0 && (
                              <span className="px-1.5 py-0.2 rounded text-[10px] bg-[#3B82F6]/20 text-[#60A5FA]">
                                {a.low_count}L
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="p-3 font-mono text-[#64748B]">
                          {new Date(a.created_at).toLocaleString('id-ID', {
                            dateStyle: 'short',
                            timeStyle: 'short',
                          })}
                        </td>
                        <td className="p-3 text-right">
                          <Link
                            href={`/web-security/findings?target_id=${a.web_target_id}`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-semibold bg-[#1E293B] text-[#38BDF8] border border-[rgba(255,255,255,0.08)] hover:bg-[#334155] transition-colors"
                          >
                            <Bug className="h-3 w-3" />
                            Temuan
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </AppShell>
  );
}

