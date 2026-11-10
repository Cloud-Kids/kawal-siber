'use client';

import { useState, useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import {
  getWebTargets,
  createWebTarget,
  deleteWebTarget,
  updateWebTarget,
  createWebAssessment,
  getAssets,
} from '@/lib/api';
import type { WebTarget, Asset } from '@/types';
import {
  Crosshair,
  Plus,
  Play,
  Trash2,
  CheckCircle,
  XCircle,
  RefreshCw,
  ExternalLink,
  Shield,
  AlertCircle,
} from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function WebTargetsPage() {
  const router = useRouter();
  const [targets, setTargets] = useState<WebTarget[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal form states
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    target_url: 'http://127.0.0.1:8000',
    asset_id: '',
    allowed_paths: '/*',
    authorization_reference: 'SURAT-TUGAS-KCH2026-LAB',
  });
  const [submitting, setSubmitting] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [tData, aData] = await Promise.all([
        getWebTargets(),
        getAssets().catch(() => []),
      ]);
      setTargets(tData);
      setAssets(aData);
    } catch (err: any) {
      setError(err?.message || 'Gagal memuat target web.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleCreateTarget(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createWebTarget({
        name: formData.name,
        target_url: formData.target_url,
        asset_id: formData.asset_id ? Number(formData.asset_id) : null,
        allowed_paths: formData.allowed_paths,
        authorization_reference: formData.authorization_reference,
        enabled: true,
      });
      setShowModal(false);
      setFormData({
        name: '',
        target_url: 'http://127.0.0.1:8000',
        asset_id: '',
        allowed_paths: '/*',
        authorization_reference: 'SURAT-TUGAS-KCH2026-LAB',
      });
      setSuccessMsg('Target web berhasil didaftarkan dan diotorisasi.');
      await loadData();
    } catch (err: any) {
      setError(err?.message || 'Gagal mendaftarkan target web.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleEnabled(target: WebTarget) {
    try {
      await updateWebTarget(target.id, { enabled: !target.enabled });
      await loadData();
    } catch (err: any) {
      setError(err?.message || 'Gagal mengubah status target.');
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Yakin ingin menghapus target web ini dan seluruh riwayat asesmennya?')) return;
    try {
      await deleteWebTarget(id);
      setSuccessMsg('Target web berhasil dihapus.');
      await loadData();
    } catch (err: any) {
      setError(err?.message || 'Gagal menghapus target.');
    }
  }

  async function handleRunAssessment(targetId: number, profile: 'PASSIVE' | 'SAFE_LOCAL') {
    setActionLoadingId(targetId);
    setError(null);
    try {
      await createWebAssessment({
        web_target_id: targetId,
        assessment_profile: profile,
      });
      setSuccessMsg(`Asesmen ${profile} berhasil dijalankan.`);
      router.push('/web-security/assessments');
    } catch (err: any) {
      setError(err?.message || 'Gagal menjalankan asesmen web.');
      setActionLoadingId(null);
    }
  }

  return (
    <AppShell>
      <Header title="Manajemen Target Asesmen Web" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Top Control Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-[#F8FAFC]">Daftar Target Web Terotorisasi</h2>
            <p className="text-xs text-[#94A3B8]">
              Target web dibatasi secara ketat pada laboratorium localhost dan aset berotorisasi aktif.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadData}
              disabled={loading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#1E293B] text-[#94A3B8] hover:text-[#F8FAFC] border border-[rgba(255,255,255,0.08)] transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#22C55E] text-[#0F172A] hover:bg-[#16A34A] transition-colors shadow-sm"
            >
              <Plus className="h-3.5 w-3.5" />
              Tambah Target Web
            </button>
          </div>
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

        {/* Targets Table */}
        <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-xs text-[#64748B] flex items-center justify-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin text-[#3B82F6]" />
              Memuat target web...
            </div>
          ) : targets.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <Crosshair className="h-8 w-8 text-[#475569] mx-auto" />
              <p className="text-xs text-[#94A3B8]">Belum ada target web terdaftar.</p>
              <button
                onClick={() => setShowModal(true)}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#3B82F6] text-white hover:bg-[#2563EB]"
              >
                Daftarkan Target Pertama
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#1E293B]/50 font-mono text-[#94A3B8] border-b border-[rgba(255,255,255,0.06)]">
                  <tr>
                    <th className="p-3">ID</th>
                    <th className="p-3">Nama Target</th>
                    <th className="p-3">URL & Endpoint</th>
                    <th className="p-3">Host:Port</th>
                    <th className="p-3">Allowed Paths</th>
                    <th className="p-3">Otorisasi</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Aksi Asesmen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(255,255,255,0.05)] text-[#CBD5E1]">
                  {targets.map((t) => (
                    <tr key={t.id} className="hover:bg-[#1E293B]/30 transition-colors">
                      <td className="p-3 font-mono text-[#64748B]">#{t.id}</td>
                      <td className="p-3">
                        <span className="font-semibold text-[#F8FAFC]">{t.name}</span>
                        {t.asset_id && (
                          <span className="block text-[10px] text-[#3B82F6] font-mono">
                            Aset Terkait ID #{t.asset_id}
                          </span>
                        )}
                      </td>
                      <td className="p-3 font-mono text-[#38BDF8] max-w-xs truncate">
                        {t.target_url}
                      </td>
                      <td className="p-3 font-mono text-[#94A3B8]">
                        {t.hostname}:{t.port}
                      </td>
                      <td className="p-3 font-mono text-[#A855F7]">
                        {t.allowed_paths || '/*'}
                      </td>
                      <td className="p-3 text-[11px] text-[#64748B] font-mono">
                        {t.authorization_reference || 'DEFAULT'}
                      </td>
                      <td className="p-3">
                        <button
                          onClick={() => handleToggleEnabled(t)}
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-colors ${
                            t.enabled
                              ? 'bg-[#22C55E]/15 text-[#22C55E] border border-[#22C55E]/30'
                              : 'bg-[#64748B]/15 text-[#94A3B8] border border-[#64748B]/30'
                          }`}
                        >
                          {t.enabled ? 'AKTIF' : 'NONAKTIF'}
                        </button>
                      </td>
                      <td className="p-3 text-right space-x-1.5 whitespace-nowrap">
                        <button
                          onClick={() => handleRunAssessment(t.id, 'PASSIVE')}
                          disabled={!t.enabled || actionLoadingId === t.id}
                          className="px-2.5 py-1 rounded text-[11px] font-semibold bg-[#3B82F6]/20 text-[#60A5FA] border border-[#3B82F6]/40 hover:bg-[#3B82F6]/30 disabled:opacity-40"
                          title="Audit Header, Cookie, CORS, TLS non-intrusif"
                        >
                          {actionLoadingId === t.id ? 'Memproses...' : 'Passive Scan'}
                        </button>
                        <button
                          onClick={() => handleRunAssessment(t.id, 'SAFE_LOCAL')}
                          disabled={!t.enabled || actionLoadingId === t.id}
                          className="px-2.5 py-1 rounded text-[11px] font-semibold bg-[#22C55E]/20 text-[#22C55E] border border-[#22C55E]/40 hover:bg-[#22C55E]/30 disabled:opacity-40"
                          title="Deep Eye Safe Local Assessment (rate-limited)"
                        >
                          Safe Local Scan
                        </button>
                        <button
                          onClick={() => handleDelete(t.id)}
                          className="p-1 rounded text-[#64748B] hover:text-[#EF4444] transition-colors"
                          title="Hapus Target"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Modal Tambah Target */}
        {showModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="w-full max-w-lg rounded-xl border border-[rgba(255,255,255,0.1)] bg-[#0F172A] p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.06)] pb-3">
                <h3 className="text-base font-bold text-[#F8FAFC] flex items-center gap-2">
                  <Crosshair className="h-4 w-4 text-[#22C55E]" />
                  Daftarkan Target Asesmen Web
                </h3>
                <button
                  onClick={() => setShowModal(false)}
                  className="text-[#64748B] hover:text-[#CBD5E1]"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateTarget} className="space-y-4 text-xs">
                <div>
                  <label className="block font-semibold text-[#CBD5E1] mb-1">Nama Target Web</label>
                  <input
                    type="text"
                    required
                    placeholder="Contoh: Backend FastAPI Lab 8000"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] text-[#F8FAFC] focus:outline-none focus:border-[#22C55E]"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-[#CBD5E1] mb-1">Target URL (Localhost / Lab)</label>
                  <input
                    type="url"
                    required
                    placeholder="http://127.0.0.1:8000"
                    value={formData.target_url}
                    onChange={(e) => setFormData({ ...formData, target_url: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] text-[#F8FAFC] font-mono focus:outline-none focus:border-[#22C55E]"
                  />
                  <span className="text-[10px] text-[#64748B] mt-1 block">
                    Kebijakan ketat: Hanya menerima localhost (127.0.0.1, localhost) atau alamat aset berotorisasi.
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-[#CBD5E1] mb-1">Tautkan Aset Terdaftar (Opsional)</label>
                    <select
                      value={formData.asset_id}
                      onChange={(e) => setFormData({ ...formData, asset_id: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] text-[#F8FAFC] focus:outline-none focus:border-[#22C55E]"
                    >
                      <option value="">-- Tanpa Tautan Langsung --</option>
                      {assets.map((a) => (
                        <option key={a.id} value={a.id}>
                          #{a.id} {a.name} ({a.target_ip}:{a.port})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-semibold text-[#CBD5E1] mb-1">Path yang Diizinkan</label>
                    <input
                      type="text"
                      placeholder="/* atau /api/*"
                      value={formData.allowed_paths}
                      onChange={(e) => setFormData({ ...formData, allowed_paths: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] text-[#F8FAFC] font-mono focus:outline-none focus:border-[#22C55E]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-[#CBD5E1] mb-1">Referensi Otorisasi</label>
                  <input
                    type="text"
                    value={formData.authorization_reference}
                    onChange={(e) => setFormData({ ...formData, authorization_reference: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] text-[#F8FAFC] focus:outline-none focus:border-[#22C55E]"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-[rgba(255,255,255,0.06)]">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-4 py-2 rounded-lg bg-[#1E293B] text-[#94A3B8] hover:text-[#F8FAFC]"
                  >
                    Batal
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 rounded-lg bg-[#22C55E] text-[#0F172A] font-bold hover:bg-[#16A34A] disabled:opacity-50"
                  >
                    {submitting ? 'Menyimpan...' : 'Daftarkan & Otorisasi'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </AppShell>
  );
}

