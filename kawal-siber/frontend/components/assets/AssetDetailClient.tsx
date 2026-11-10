'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Radar,
  Server,
  Shield,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Crosshair,
  ExternalLink,
  Edit2,
  AlertCircle,
  FileSearch,
} from 'lucide-react';
import type { Asset, ScanJob, ScanResult, ScanScope } from '@/types';
import StatusBadge from '@/components/ui/StatusBadge';
import AvailabilityBadge from '@/components/ui/AvailabilityBadge';
import ScanJobStatusBadge from '@/components/ui/ScanJobStatusBadge';
import EmptyState from '@/components/ui/EmptyState';
import { createAssetScan, updateAsset } from '@/lib/api';
import { formatDateTime, formatResponseTime } from '@/lib/utils';

interface AssetDetailClientProps {
  asset: Asset;
  scope: ScanScope | null;
  scanHistory: ScanJob[];
  latestResults: ScanResult[];
  availableScopes: ScanScope[];
}

export default function AssetDetailClient({
  asset,
  scope,
  scanHistory,
  latestResults,
  availableScopes,
}: AssetDetailClientProps) {
  const router = useRouter();
  const [isScanning, setIsScanning] = useState(false);
  const [toastMsg, setToastMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Edit Modal State
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editName, setEditName] = useState(asset.name);
  const [editTargetIp, setEditTargetIp] = useState(asset.target_ip);
  const [editPort, setEditPort] = useState(String(asset.port));
  const [editScopeId, setEditScopeId] = useState(asset.scope_id ? String(asset.scope_id) : '');
  const [isSaving, setIsSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMsg({ text, type });
    setTimeout(() => setToastMsg(null), 5000);
  };

  const handleTriggerScan = async () => {
    setIsScanning(true);
    try {
      const job = await createAssetScan(asset.id);
      showToast(`Pemindaian berhasil dijadwalkan (Job ID #${job.id}). Worker sedang memproses.`);
      router.refresh();
    } catch (err: any) {
      showToast(err.message || 'Gagal memicu pemindaian Nmap.', 'error');
    } finally {
      setIsScanning(false);
    }
  };

  const handleUpdateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setEditError(null);

    const portNum = parseInt(editPort, 10);
    if (isNaN(portNum) || portNum < 1 || portNum > 65535) {
      setEditError('Port harus berada dalam rentang 1 - 65535.');
      setIsSaving(false);
      return;
    }

    try {
      await updateAsset(asset.id, {
        name: editName.trim(),
        target_ip: editTargetIp.trim(),
        port: portNum,
        scope_id: editScopeId ? parseInt(editScopeId, 10) : null,
      });

      showToast('Informasi aset berhasil diperbarui.');
      setIsEditOpen(false);
      router.refresh();
    } catch (err: any) {
      setEditError(err.message || 'Gagal memperbarui aset.');
    } finally {
      setIsSaving(false);
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

      {/* Back button and Header Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Link
          href="/assets"
          className="inline-flex items-center gap-2 text-xs font-mono text-[#64748B] hover:text-[#CBD5E1] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Kembali ke Daftar Aset
        </Link>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsEditOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3.5 py-2 text-xs font-medium text-[#CBD5E1] hover:bg-[#334155] transition-colors"
          >
            <Edit2 className="h-3.5 w-3.5" />
            Edit Aset
          </button>

          <button
            onClick={handleTriggerScan}
            disabled={isScanning}
            className="inline-flex items-center gap-2 rounded-lg bg-[#22C55E] px-4 py-2 text-xs font-bold text-[#0F172A] shadow-lg hover:bg-[#16A34A] transition-all disabled:opacity-50"
          >
            <Radar className={`h-4 w-4 ${isScanning ? 'animate-spin' : ''}`} />
            {isScanning ? 'Mendaftarkan Scan...' : 'Luncurkan Pindai Nmap'}
          </button>
        </div>
      </div>

      {/* Top Details Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Asset Spec Card */}
        <div className="lg:col-span-2 glass-card rounded-xl border border-[rgba(255,255,255,0.08)] p-6 space-y-4">
          <div className="flex items-start justify-between border-b border-[rgba(255,255,255,0.08)] pb-4">
            <div>
              <span className="font-mono text-xs text-[#22C55E] tracking-wider uppercase">
                Aset Teritorial #{asset.id}
              </span>
              <h2 className="text-xl font-bold text-[#F8FAFC] mt-0.5">{asset.name}</h2>
            </div>
            <div className="flex flex-col items-end gap-1.5">
              <StatusBadge status={asset.status} />
              <AvailabilityBadge status={asset.availability_status} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 font-mono text-xs">
            <div className="rounded-lg bg-[#0F172A] p-3 border border-[rgba(255,255,255,0.04)]">
              <span className="block text-[11px] text-[#64748B]">Target IP / Host</span>
              <span className="block text-sm font-bold text-[#38BDF8] mt-1">
                {asset.target_ip}
              </span>
            </div>

            <div className="rounded-lg bg-[#0F172A] p-3 border border-[rgba(255,255,255,0.04)]">
              <span className="block text-[11px] text-[#64748B]">Port Terdaftar</span>
              <span className="block text-sm font-bold text-[#F8FAFC] mt-1">
                {asset.port} / TCP
              </span>
            </div>

            <div className="rounded-lg bg-[#0F172A] p-3 border border-[rgba(255,255,255,0.04)]">
              <span className="block text-[11px] text-[#64748B]">Waktu Respon</span>
              <span className="block text-sm font-bold text-[#A7F3D0] mt-1">
                {formatResponseTime(asset.response_time_ms)}
              </span>
            </div>

            <div className="rounded-lg bg-[#0F172A] p-3 border border-[rgba(255,255,255,0.04)]">
              <span className="block text-[11px] text-[#64748B]">Terakhir Dipindai</span>
              <span className="block text-[11px] font-bold text-[#CBD5E1] mt-1">
                {formatDateTime(asset.last_scanned)}
              </span>
            </div>
          </div>

          <div className="rounded-lg bg-[#1E293B]/40 p-3.5 border border-amber-500/20 text-xs text-[#94A3B8]">
            <span className="font-semibold text-amber-400 block mb-1">
              Catatan Arsitektur Keamanan:
            </span>
            Status ketersediaan jaringan (Online/Offline) dipastikan melalui respon TCP Nmap,
            sedangkan status keamanan siber ({asset.status}) ditentukan secara terpisah melalui
            audit kerentanan dan sensor deteksi serangan.
          </div>
        </div>

        {/* Scope Authorization Card */}
        <div className="glass-card rounded-xl border border-[rgba(255,255,255,0.08)] p-6 space-y-4">
          <div className="flex items-center gap-2 text-emerald-400 border-b border-[rgba(255,255,255,0.08)] pb-3">
            <Crosshair className="h-5 w-5" />
            <h3 className="font-bold text-sm text-[#F8FAFC]">Otorisasi Scope Pemindaian</h3>
          </div>

          {scope ? (
            <div className="space-y-3 text-xs">
              <div>
                <span className="text-[#64748B] block text-[11px]">Nama Scope:</span>
                <span className="font-bold text-[#F8FAFC] text-sm">{scope.name}</span>
              </div>

              <div>
                <span className="text-[#64748B] block text-[11px]">Subnet CIDR Izin:</span>
                <span className="font-mono text-[#38BDF8] font-bold text-sm">{scope.cidr}</span>
              </div>

              <div>
                <span className="text-[#64748B] block text-[11px]">Referensi Otorisasi:</span>
                <span className="font-mono text-[#CBD5E1] bg-[#0F172A] px-2 py-0.5 rounded border border-[rgba(255,255,255,0.06)]">
                  {scope.authorization_reference}
                </span>
              </div>

              <div>
                <span className="text-[#64748B] block text-[11px]">Masa Berlaku Izin:</span>
                <span className="font-mono text-[#F59E0B]">
                  {formatDateTime(scope.expires_at)}
                </span>
              </div>

              <div className="pt-2">
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-mono border ${
                    scope.enabled
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      scope.enabled ? 'bg-emerald-400' : 'bg-rose-400'
                    }`}
                  />
                  {scope.enabled ? 'Scope Aktif & Diizinkan' : 'Scope Dinonaktifkan'}
                </span>
              </div>
            </div>
          ) : (
            <div className="py-6 text-center space-y-2">
              <AlertCircle className="h-8 w-8 text-amber-400 mx-auto" />
              <p className="text-xs text-[#94A3B8]">
                Aset ini belum ditautkan ke Scope Otorisasi eksplisit.
              </p>
              <p className="text-[11px] text-[#64748B]">
                Saat pemindaian dipicu, sistem akan memeriksa apakah ada subnet scope aktif yang mencakup IP target.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Latest Findings Table */}
      <div className="glass-card rounded-xl border border-[rgba(255,255,255,0.08)] overflow-hidden">
        <div className="px-5 py-4 border-b border-[rgba(255,255,255,0.08)] bg-[#0F172A]/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileSearch className="h-4 w-4 text-[#38BDF8]" />
            <h3 className="font-bold text-sm text-[#F8FAFC]">Temuan Port & Layanan Terkini</h3>
          </div>
          <span className="text-xs font-mono text-[#64748B]">
            {latestResults.length} Temuan Terdeteksi
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.08)] bg-[#0F172A]/50 font-mono text-[#94A3B8] uppercase">
                <th className="px-5 py-3">Port / Protokol</th>
                <th className="px-5 py-3">Status Port</th>
                <th className="px-5 py-3">Layanan (Service)</th>
                <th className="px-5 py-3">Produk / Banner</th>
                <th className="px-5 py-3">Versi</th>
                <th className="px-5 py-3">Alasan (Reason)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255,255,255,0.04)] font-mono">
              {latestResults.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-[#64748B]">
                    Belum ada data temuan hasil pemindaian port untuk aset ini.
                  </td>
                </tr>
              ) : (
                latestResults.map((res) => (
                  <tr key={res.id} className="hover:bg-[#1E293B]/40">
                    <td className="px-5 py-3 font-bold text-[#38BDF8]">
                      {res.port} / {res.protocol.toUpperCase()}
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`inline-flex items-center rounded px-2 py-0.5 text-[11px] font-bold ${
                          res.state === 'open'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : res.state === 'closed'
                            ? 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
                            : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        }`}
                      >
                        {res.state.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-[#F8FAFC]">{res.service_name || '—'}</td>
                    <td className="px-5 py-3 text-[#CBD5E1]">{res.product || '—'}</td>
                    <td className="px-5 py-3 text-[#94A3B8]">{res.version || '—'}</td>
                    <td className="px-5 py-3 text-[#64748B]">{res.reason || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Scan History Table */}
      <div className="glass-card rounded-xl border border-[rgba(255,255,255,0.08)] overflow-hidden">
        <div className="px-5 py-4 border-b border-[rgba(255,255,255,0.08)] bg-[#0F172A]/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-[#F59E0B]" />
            <h3 className="font-bold text-sm text-[#F8FAFC]">Riwayat Pemindaian (Scan History)</h3>
          </div>
          <span className="text-xs font-mono text-[#64748B]">
            {scanHistory.length} Riwayat Pekerjaan
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.08)] bg-[#0F172A]/50 font-mono text-[#94A3B8] uppercase">
                <th className="px-5 py-3">Job ID</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">IP Terverifikasi</th>
                <th className="px-5 py-3">Durasi</th>
                <th className="px-5 py-3">Versi Scanner</th>
                <th className="px-5 py-3">Waktu Eksekusi</th>
                <th className="px-5 py-3">Detail / Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255,255,255,0.04)] font-mono">
              {scanHistory.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-[#64748B]">
                    Belum ada riwayat pemindaian untuk aset ini. Klik tombol di atas untuk memulai.
                  </td>
                </tr>
              ) : (
                scanHistory.map((job) => (
                  <tr key={job.id} className="hover:bg-[#1E293B]/40">
                    <td className="px-5 py-3 font-bold text-[#F8FAFC]">#{job.id}</td>
                    <td className="px-5 py-3">
                      <ScanJobStatusBadge status={job.status} />
                    </td>
                    <td className="px-5 py-3 text-[#38BDF8]">
                      {job.resolved_ip || '—'}
                    </td>
                    <td className="px-5 py-3 text-[#CBD5E1]">
                      {formatResponseTime(job.duration_ms)}
                    </td>
                    <td className="px-5 py-3 text-[11px] text-[#64748B]">
                      {job.scanner_version || '—'}
                    </td>
                    <td className="px-5 py-3 text-[#94A3B8]">
                      {formatDateTime(job.finished_at || job.created_at)}
                    </td>
                    <td className="px-5 py-3 text-xs">
                      {job.error_message ? (
                        <span className="text-rose-400 truncate max-w-xs block" title={job.error_message}>
                          [{job.error_code}] {job.error_message}
                        </span>
                      ) : (
                        <span className="text-emerald-400">Sukses</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Modal */}
      {isEditOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="glass-card w-full max-w-md rounded-xl border border-[rgba(255,255,255,0.12)] p-6 shadow-2xl bg-[#0F172A]">
            <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.08)] pb-4 mb-4">
              <h3 className="text-base font-bold text-[#F8FAFC]">Ubah Data Aset</h3>
              <button onClick={() => setIsEditOpen(false)} className="text-[#64748B] hover:text-[#F8FAFC]">
                ✕
              </button>
            </div>

            {editError && (
              <div className="mb-4 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-400">
                {editError}
              </div>
            )}

            <form onSubmit={handleUpdateAsset} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#94A3B8] mb-1 font-medium">Nama Aset</label>
                <input
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-sm text-[#F8FAFC] focus:border-[#22C55E] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[#94A3B8] mb-1 font-medium">IP Target / Hostname</label>
                <input
                  type="text"
                  required
                  value={editTargetIp}
                  onChange={(e) => setEditTargetIp(e.target.value)}
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
                  value={editPort}
                  onChange={(e) => setEditPort(e.target.value)}
                  className="w-full rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-sm font-mono text-[#F8FAFC] focus:border-[#22C55E] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[#94A3B8] mb-1 font-medium">Scope Otorisasi</label>
                <select
                  value={editScopeId}
                  onChange={(e) => setEditScopeId(e.target.value)}
                  className="w-full rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-xs font-mono text-[#F8FAFC] focus:border-[#22C55E] focus:outline-none"
                >
                  <option value="">Tanpa Scope (atau tentukan otomatis)</option>
                  {availableScopes.map((s) => (
                    <option key={s.id} value={String(s.id)}>
                      {s.name} ({s.cidr})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-[rgba(255,255,255,0.08)]">
                <button
                  type="button"
                  onClick={() => setIsEditOpen(false)}
                  className="rounded-lg px-4 py-2 text-xs font-medium text-[#94A3B8] hover:bg-[#1E293B] transition-colors"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="rounded-lg bg-[#22C55E] px-4 py-2 text-xs font-bold text-[#0F172A] hover:bg-[#16A34A] transition-colors disabled:opacity-50"
                >
                  {isSaving ? 'Menyimpan...' : 'Perbarui Aset'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

