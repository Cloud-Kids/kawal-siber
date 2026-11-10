'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Crosshair,
  Plus,
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Power,
} from 'lucide-react';
import type { ScanScope } from '@/types';
import EmptyState from '@/components/ui/EmptyState';
import { createScanScope, updateScanScope } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

interface ScopesClientProps {
  initialScopes: ScanScope[];
}

export default function ScopesClient({ initialScopes }: ScopesClientProps) {
  const router = useRouter();
  const [scopes, setScopes] = useState<ScanScope[]>(initialScopes);
  const [search, setSearch] = useState('');
  const [filterEnabled, setFilterEnabled] = useState<string>('ALL');

  // Modal
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Form State
  const [newName, setNewName] = useState('');
  const [newCidr, setNewCidr] = useState('');
  const [newAuthRef, setNewAuthRef] = useState('');
  const [newExpiry, setNewExpiry] = useState('');
  const [newDescription, setNewDescription] = useState('');

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMsg({ text, type });
    setTimeout(() => setToastMsg(null), 4000);
  };

  const filteredScopes = scopes.filter((s) => {
    const matchSearch =
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.cidr.toLowerCase().includes(search.toLowerCase()) ||
      s.authorization_reference.toLowerCase().includes(search.toLowerCase());
    const matchEnabled =
      filterEnabled === 'ALL' ||
      (filterEnabled === 'ACTIVE' && s.enabled) ||
      (filterEnabled === 'DISABLED' && !s.enabled);
    return matchSearch && matchEnabled;
  });

  const handleCreateScope = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);

    if (!newExpiry) {
      setErrorMsg('Tanggal kedaluwarsa otorisasi wajib diisi.');
      setIsSubmitting(false);
      return;
    }

    try {
      const expiryIso = new Date(newExpiry).toISOString();
      const created = await createScanScope({
        name: newName.trim(),
        cidr: newCidr.trim(),
        authorization_reference: newAuthRef.trim(),
        expires_at: expiryIso,
        description: newDescription.trim() || null,
        enabled: true,
      });

      setScopes((prev) => [created, ...prev]);
      setIsAddOpen(false);
      setNewName('');
      setNewCidr('');
      setNewAuthRef('');
      setNewExpiry('');
      setNewDescription('');
      showToast(`Scope ${created.name} berhasil didaftarkan.`);
      router.refresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Gagal mendaftarkan scope baru.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleScope = async (scope: ScanScope) => {
    try {
      const updated = await updateScanScope(scope.id, {
        enabled: !scope.enabled,
      });
      setScopes((prev) =>
        prev.map((s) => (s.id === scope.id ? { ...s, enabled: updated.enabled } : s))
      );
      showToast(
        `Scope ${scope.name} berhasil ${updated.enabled ? 'diaktifkan' : 'dinonaktifkan'}.`
      );
      router.refresh();
    } catch (err: any) {
      showToast(err.message || 'Gagal mengubah status scope.', 'error');
    }
  };

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toastMsg && (
        <div
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-lg border px-4 py-3 shadow-xl transition-all ${
            toastMsg.type === 'success'
              ? 'bg-[#1E293B] border-emerald-500/40 text-emerald-400'
              : 'bg-[#1E293B] border-rose-500/40 text-rose-400'
          }`}
        >
          {toastMsg.type === 'success' ? (
            <CheckCircle2 className="h-5 w-5 shrink-0" />
          ) : (
            <XCircle className="h-5 w-5 shrink-0" />
          )}
          <span className="text-sm font-medium">{toastMsg.text}</span>
        </div>
      )}

      {/* Control Bar */}
      <div className="glass-card rounded-xl border border-[rgba(255,255,255,0.08)] p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#64748B]" />
            <input
              type="text"
              placeholder="Cari nama scope, CIDR, atau referensi otorisasi..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg bg-[#0F172A] border border-[rgba(255,255,255,0.1)] py-2.5 pl-10 pr-4 text-sm text-[#F8FAFC] placeholder-[#64748B] focus:border-[#22C55E] focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-3">
            <select
              value={filterEnabled}
              onChange={(e) => setFilterEnabled(e.target.value)}
              className="rounded-lg bg-[#0F172A] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-xs font-mono text-[#CBD5E1] focus:border-[#22C55E] focus:outline-none"
            >
              <option value="ALL">Semua Status</option>
              <option value="ACTIVE">Hanya Aktif</option>
              <option value="DISABLED">Hanya Dinonaktifkan</option>
            </select>

            <button
              onClick={() => setIsAddOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-[#22C55E] px-4 py-2 text-xs font-bold text-[#0F172A] shadow-md hover:bg-[#16A34A] transition-colors"
            >
              <Plus className="h-4 w-4" />
              Tambah Scope
            </button>
          </div>
        </div>
      </div>

      {/* Scopes Table */}
      <div className="glass-card rounded-xl border border-[rgba(255,255,255,0.08)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.08)] bg-[#0F172A]/70 font-mono text-[#94A3B8] uppercase tracking-wider">
                <th className="px-5 py-3.5">Nama Scope</th>
                <th className="px-5 py-3.5">Subnet CIDR</th>
                <th className="px-5 py-3.5">Referensi Otorisasi</th>
                <th className="px-5 py-3.5">Masa Berlaku (Expiry)</th>
                <th className="px-5 py-3.5">Status Izin</th>
                <th className="px-5 py-3.5 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255,255,255,0.04)]">
              {filteredScopes.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center">
                    <EmptyState
                      icon={Crosshair}
                      title="Belum Ada Scope Terdaftar"
                      description="Tambahkan scope otorisasi CIDR sebelum melakukan pemindaian keamanan jaringan."
                    />
                  </td>
                </tr>
              ) : (
                filteredScopes.map((scope) => {
                  const isExpired = new Date(scope.expires_at) <= new Date();
                  return (
                    <tr key={scope.id} className="hover:bg-[#1E293B]/40 transition-colors">
                      <td className="px-5 py-3.5">
                        <span className="font-bold text-[#F8FAFC] block">{scope.name}</span>
                        {scope.description && (
                          <span className="text-[11px] text-[#64748B] block mt-0.5">
                            {scope.description}
                          </span>
                        )}
                      </td>

                      <td className="px-5 py-3.5 font-mono">
                        <span className="inline-block rounded bg-[#0F172A] px-2 py-0.5 font-bold text-[#38BDF8] border border-[rgba(255,255,255,0.06)]">
                          {scope.cidr}
                        </span>
                      </td>

                      <td className="px-5 py-3.5 font-mono text-[#CBD5E1]">
                        {scope.authorization_reference}
                      </td>

                      <td className="px-5 py-3.5 font-mono">
                        <span className={isExpired ? 'text-rose-400 font-bold' : 'text-[#F59E0B]'}>
                          {formatDateTime(scope.expires_at)}
                        </span>
                        {isExpired && (
                          <span className="block text-[10px] text-rose-400 uppercase font-sans font-bold">
                            (Kedaluwarsa)
                          </span>
                        )}
                      </td>

                      <td className="px-5 py-3.5">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-mono border ${
                            scope.enabled && !isExpired
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                              : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                          }`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              scope.enabled && !isExpired ? 'bg-emerald-400' : 'bg-rose-400'
                            }`}
                          />
                          {scope.enabled && !isExpired ? 'Aktif' : 'Nonaktif'}
                        </span>
                      </td>

                      <td className="px-5 py-3.5 text-right">
                        <button
                          onClick={() => handleToggleScope(scope)}
                          className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                            scope.enabled
                              ? 'bg-rose-500/10 text-rose-400 hover:bg-rose-500/20'
                              : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20'
                          }`}
                        >
                          <Power className="h-3.5 w-3.5" />
                          {scope.enabled ? 'Nonaktifkan' : 'Aktifkan'}
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Scope Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="glass-card w-full max-w-md rounded-xl border border-[rgba(255,255,255,0.12)] p-6 shadow-2xl bg-[#0F172A]">
            <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.08)] pb-4 mb-4">
              <h3 className="text-base font-bold text-[#F8FAFC]">Daftarkan Scope Otorisasi Baru</h3>
              <button onClick={() => setIsAddOpen(false)} className="text-[#64748B] hover:text-[#F8FAFC]">
                ✕
              </button>
            </div>

            {errorMsg && (
              <div className="mb-4 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-400">
                {errorMsg}
              </div>
            )}

            <form onSubmit={handleCreateScope} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#94A3B8] mb-1 font-medium">Nama Scope</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Subnet Laboratorium Teritorial"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-sm text-[#F8FAFC] focus:border-[#22C55E] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[#94A3B8] mb-1 font-medium">Subnet CIDR</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 192.168.1.0/24 atau 10.0.0.0/8"
                  value={newCidr}
                  onChange={(e) => setNewCidr(e.target.value)}
                  className="w-full rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-sm font-mono text-[#F8FAFC] focus:border-[#22C55E] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[#94A3B8] mb-1 font-medium">
                  Referensi Otorisasi / Tiket Audit
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. SURAT-TUGAS-KODAM-2026-X1"
                  value={newAuthRef}
                  onChange={(e) => setNewAuthRef(e.target.value)}
                  className="w-full rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-sm font-mono text-[#F8FAFC] focus:border-[#22C55E] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[#94A3B8] mb-1 font-medium">
                  Batas Akhir Otorisasi (Expiry)
                </label>
                <input
                  type="datetime-local"
                  required
                  value={newExpiry}
                  onChange={(e) => setNewExpiry(e.target.value)}
                  className="w-full rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-sm font-mono text-[#F8FAFC] focus:border-[#22C55E] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[#94A3B8] mb-1 font-medium">Deskripsi / Catatan Lab</label>
                <textarea
                  rows={2}
                  placeholder="Keterangan lingkungan uji atau batasan operasional..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  className="w-full rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#22C55E] focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-[rgba(255,255,255,0.08)]">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="rounded-lg px-4 py-2 text-xs font-medium text-[#94A3B8] hover:bg-[#1E293B] transition-colors"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-lg bg-[#22C55E] px-4 py-2 text-xs font-bold text-[#0F172A] hover:bg-[#16A34A] transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? 'Mendaftarkan...' : 'Simpan Scope'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
