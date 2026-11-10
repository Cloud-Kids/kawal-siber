'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Server,
  Search,
  Plus,
  Trash2,
  ExternalLink,
  ShieldAlert,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Filter,
} from 'lucide-react';
import type { Asset, AssetStatus, AvailabilityStatus, ScanScope } from '@/types';
import StatusBadge from '@/components/ui/StatusBadge';
import AvailabilityBadge from '@/components/ui/AvailabilityBadge';
import EmptyState from '@/components/ui/EmptyState';
import { createAsset, deleteAsset } from '@/lib/api';
import { formatDateTime, formatResponseTime } from '@/lib/utils';

interface AssetsClientProps {
  initialAssets: Asset[];
  scopes: ScanScope[];
}

export default function AssetsClient({ initialAssets, scopes }: AssetsClientProps) {
  const router = useRouter();
  const [assets, setAssets] = useState<Asset[]>(initialAssets);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [availFilter, setAvailFilter] = useState<string>('ALL');
  const [scopeFilter, setScopeFilter] = useState<string>('ALL');

  // Modal state
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Asset | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // New Asset Form State
  const [newName, setNewName] = useState('');
  const [newTargetIp, setNewTargetIp] = useState('');
  const [newPort, setNewPort] = useState('80');
  const [newScopeId, setNewScopeId] = useState<string>('');

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMsg({ text, type });
    setTimeout(() => setToastMsg(null), 4000);
  };

  const filteredAssets = assets.filter((asset) => {
    const matchSearch =
      asset.name.toLowerCase().includes(search.toLowerCase()) ||
      asset.target_ip.toLowerCase().includes(search.toLowerCase()) ||
      String(asset.port).includes(search);
    const matchStatus = statusFilter === 'ALL' || asset.status === statusFilter;
    const matchAvail = availFilter === 'ALL' || asset.availability_status === availFilter;
    const matchScope =
      scopeFilter === 'ALL' ||
      (scopeFilter === 'NONE' ? !asset.scope_id : String(asset.scope_id) === scopeFilter);

    return matchSearch && matchStatus && matchAvail && matchScope;
  });

  const handleCreateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);

    const portNum = parseInt(newPort, 10);
    if (isNaN(portNum) || portNum < 1 || portNum > 65535) {
      setErrorMsg('Port harus berada dalam rentang 1 - 65535.');
      setIsSubmitting(false);
      return;
    }

    try {
      const created = await createAsset({
        name: newName.trim(),
        target_ip: newTargetIp.trim(),
        port: portNum,
        scope_id: newScopeId ? parseInt(newScopeId, 10) : null,
      });

      setAssets((prev) => [created, ...prev]);
      setIsAddOpen(false);
      setNewName('');
      setNewTargetIp('');
      setNewPort('80');
      setNewScopeId('');
      showToast(`Aset ${created.name} berhasil didaftarkan.`);
      router.refresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Gagal mendaftarkan aset baru.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteAsset = async () => {
    if (!deleteTarget) return;
    setIsSubmitting(true);
    try {
      await deleteAsset(deleteTarget.id);
      setAssets((prev) => prev.filter((a) => a.id !== deleteTarget.id));
      showToast(`Aset ${deleteTarget.name} berhasil dihapus.`);
      setDeleteTarget(null);
      router.refresh();
    } catch (err: any) {
      showToast(err.message || 'Gagal menghapus aset.', 'error');
    } finally {
      setIsSubmitting(false);
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

      {/* Action Header & Search Controls */}
      <div className="glass-card rounded-xl border border-[rgba(255,255,255,0.08)] p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#64748B]" />
            <input
              type="text"
              placeholder="Cari nama aset, IP target, atau port..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg bg-[#0F172A] border border-[rgba(255,255,255,0.1)] py-2.5 pl-10 pr-4 text-sm text-[#F8FAFC] placeholder-[#64748B] focus:border-[#22C55E] focus:outline-none focus:ring-1 focus:ring-[#22C55E]"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Filter Keamanan */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg bg-[#0F172A] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-xs font-mono text-[#CBD5E1] focus:border-[#22C55E] focus:outline-none"
            >
              <option value="ALL">Semua Keamanan</option>
              <option value="SAFE">SAFE (Aman)</option>
              <option value="WARNING">WARNING</option>
              <option value="UNDER_ATTACK">UNDER_ATTACK</option>
              <option value="DOWN">DOWN</option>
              <option value="UNKNOWN">UNKNOWN</option>
            </select>

            {/* Filter Availability */}
            <select
              value={availFilter}
              onChange={(e) => setAvailFilter(e.target.value)}
              className="rounded-lg bg-[#0F172A] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-xs font-mono text-[#CBD5E1] focus:border-[#22C55E] focus:outline-none"
            >
              <option value="ALL">Semua Ketersediaan</option>
              <option value="UP">Online (UP)</option>
              <option value="DOWN">Offline (DOWN)</option>
              <option value="UNKNOWN">Belum Diperiksa</option>
            </select>

            {/* Filter Scope */}
            <select
              value={scopeFilter}
              onChange={(e) => setScopeFilter(e.target.value)}
              className="rounded-lg bg-[#0F172A] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-xs font-mono text-[#CBD5E1] focus:border-[#22C55E] focus:outline-none"
            >
              <option value="ALL">Semua Scope</option>
              <option value="NONE">Tanpa Scope</option>
              {scopes.map((s) => (
                <option key={s.id} value={String(s.id)}>
                  {s.name} ({s.cidr})
                </option>
              ))}
            </select>

            {/* Tambah Aset Button */}
            <button
              onClick={() => setIsAddOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-[#22C55E] px-4 py-2 text-xs font-bold text-[#0F172A] shadow-md hover:bg-[#16A34A] transition-colors"
            >
              <Plus className="h-4 w-4" />
              Daftar Aset Baru
            </button>
          </div>
        </div>
      </div>

      {/* Asset Table */}
      <div className="glass-card rounded-xl border border-[rgba(255,255,255,0.08)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.08)] bg-[#0F172A]/70 font-mono text-[#94A3B8] uppercase tracking-wider">
                <th className="px-5 py-3.5">ID / Nama Aset</th>
                <th className="px-5 py-3.5">Target IP / Port</th>
                <th className="px-5 py-3.5">Scope Otorisasi</th>
                <th className="px-5 py-3.5">Ketersediaan Jaringan</th>
                <th className="px-5 py-3.5">Status Keamanan</th>
                <th className="px-5 py-3.5">Pemindaian Terakhir</th>
                <th className="px-5 py-3.5 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255,255,255,0.04)]">
              {filteredAssets.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center">
                    <EmptyState
                      icon={Server}
                      title="Tidak Ada Aset Ditemukan"
                      description="Tidak ada aset yang cocok dengan kriteria pencarian atau filter yang dipilih."
                    />
                  </td>
                </tr>
              ) : (
                filteredAssets.map((asset) => {
                  const scope = scopes.find((s) => s.id === asset.scope_id);
                  return (
                    <tr
                      key={asset.id}
                      className="hover:bg-[#1E293B]/40 transition-colors"
                    >
                      <td className="px-5 py-3.5">
                        <Link
                          href={`/assets/${asset.id}`}
                          className="font-medium text-[#F8FAFC] hover:text-[#22C55E] transition-colors flex items-center gap-1.5"
                        >
                          <span>{asset.name}</span>
                          <ExternalLink className="h-3 w-3 text-[#64748B]" />
                        </Link>
                        <span className="font-mono text-[11px] text-[#64748B]">
                          ID: #{asset.id}
                        </span>
                      </td>

                      <td className="px-5 py-3.5 font-mono">
                        <span className="text-[#38BDF8]">{asset.target_ip}</span>
                        <span className="text-[#64748B]">:{asset.port}</span>
                      </td>

                      <td className="px-5 py-3.5">
                        {scope ? (
                          <div>
                            <span className="inline-flex items-center rounded bg-[#1E293B] px-2 py-0.5 font-mono text-[11px] text-[#A7F3D0] border border-emerald-500/20">
                              {scope.name}
                            </span>
                            <span className="block font-mono text-[10px] text-[#64748B]">
                              {scope.cidr}
                            </span>
                          </div>
                        ) : (
                          <span className="font-mono text-[11px] text-[#64748B] italic">
                            Tanpa Scope
                          </span>
                        )}
                      </td>

                      <td className="px-5 py-3.5">
                        <AvailabilityBadge status={asset.availability_status} />
                        {asset.response_time_ms !== null && (
                          <span className="block font-mono text-[10px] text-[#64748B] mt-0.5">
                            Respon: {formatResponseTime(asset.response_time_ms)}
                          </span>
                        )}
                      </td>

                      <td className="px-5 py-3.5">
                        <StatusBadge status={asset.status} />
                      </td>

                      <td className="px-5 py-3.5 font-mono text-[#94A3B8]">
                        {formatDateTime(asset.last_scanned)}
                      </td>

                      <td className="px-5 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            href={`/assets/${asset.id}`}
                            className="rounded p-1.5 text-[#64748B] hover:bg-[#1E293B] hover:text-[#38BDF8] transition-colors"
                            title="Detail & Pindai"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </Link>
                          <button
                            onClick={() => setDeleteTarget(asset)}
                            className="rounded p-1.5 text-[#64748B] hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
                            title="Hapus Aset"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Asset Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="glass-card w-full max-w-md rounded-xl border border-[rgba(255,255,255,0.12)] p-6 shadow-2xl bg-[#0F172A]">
            <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.08)] pb-4 mb-4">
              <h3 className="text-base font-bold text-[#F8FAFC]">Daftarkan Aset Teritorial Baru</h3>
              <button
                onClick={() => setIsAddOpen(false)}
                className="text-[#64748B] hover:text-[#F8FAFC]"
              >
                ✕
              </button>
            </div>

            {errorMsg && (
              <div className="mb-4 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-400">
                {errorMsg}
              </div>
            )}

            <form onSubmit={handleCreateAsset} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#94A3B8] mb-1 font-medium">Nama Aset</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Server Markas Komando"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-sm text-[#F8FAFC] focus:border-[#22C55E] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[#94A3B8] mb-1 font-medium">IP Target atau Hostname</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 192.168.1.100 atau gateway.lab.mil"
                  value={newTargetIp}
                  onChange={(e) => setNewTargetIp(e.target.value)}
                  className="w-full rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-sm font-mono text-[#F8FAFC] focus:border-[#22C55E] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[#94A3B8] mb-1 font-medium">Port Layanan (TCP)</label>
                <input
                  type="number"
                  required
                  min={1}
                  max={65535}
                  value={newPort}
                  onChange={(e) => setNewPort(e.target.value)}
                  className="w-full rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-sm font-mono text-[#F8FAFC] focus:border-[#22C55E] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[#94A3B8] mb-1 font-medium">Scope Otorisasi (Opsional)</label>
                <select
                  value={newScopeId}
                  onChange={(e) => setNewScopeId(e.target.value)}
                  className="w-full rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-xs font-mono text-[#F8FAFC] focus:border-[#22C55E] focus:outline-none"
                >
                  <option value="">Pilih Scope Terdaftar (atau tentukan otomatis)</option>
                  {scopes.map((s) => (
                    <option key={s.id} value={String(s.id)}>
                      {s.name} ({s.cidr})
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-[11px] text-[#64748B]">
                  Target pemindaian harus berada di dalam subnet scope yang aktif dan berotorisasi.
                </p>
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
                  {isSubmitting ? 'Mendaftarkan...' : 'Simpan Aset'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="glass-card w-full max-w-sm rounded-xl border border-rose-500/30 p-6 shadow-2xl bg-[#0F172A]">
            <div className="flex items-center gap-3 text-rose-400 mb-3">
              <ShieldAlert className="h-6 w-6 shrink-0" />
              <h3 className="text-base font-bold text-[#F8FAFC]">Konfirmasi Hapus Aset</h3>
            </div>
            <p className="text-xs text-[#94A3B8] mb-4">
              Apakah Anda yakin ingin menghapus aset{' '}
              <span className="font-bold text-[#F8FAFC]">{deleteTarget.name}</span> ({deleteTarget.target_ip})?
              Tindakan ini tidak dapat dibatalkan.
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                className="rounded-lg px-4 py-2 text-xs font-medium text-[#94A3B8] hover:bg-[#1E293B] transition-colors"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={handleDeleteAsset}
                disabled={isSubmitting}
                className="rounded-lg bg-rose-500 px-4 py-2 text-xs font-bold text-white hover:bg-rose-600 transition-colors disabled:opacity-50"
              >
                {isSubmitting ? 'Menghapus...' : 'Ya, Hapus Aset'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
