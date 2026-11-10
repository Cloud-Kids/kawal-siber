'use client';

import { useState } from 'react';
import type { PcapAnalysis } from '@/types';
import {
  FileSearch,
  Upload,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldAlert,
  HardDrive,
  Activity,
} from 'lucide-react';

interface PcapClientProps {
  initialAnalyses: PcapAnalysis[];
}

export default function PcapClient({ initialAnalyses }: PcapClientProps) {
  const [analyses, setAnalyses] = useState<PcapAnalysis[]>(initialAnalyses);
  const [isUploading, setIsUploading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [existingFilename, setExistingFilename] = useState('');
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const refreshAnalyses = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch('/api/v1/monitoring/pcap?limit=50');
      if (res.ok) {
        const json = await res.json();
        setAnalyses(json);
      }
    } catch {
      // fallback
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setNotification({ type: 'error', message: 'Silakan pilih file PCAP terlebih dahulu.' });
      return;
    }

    setIsUploading(true);
    setNotification(null);

    const formData = new FormData();
    formData.append('file', uploadFile);

    try {
      const res = await fetch('/api/v1/monitoring/pcap', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Upload gagal: HTTP ${res.status}`);
      }

      setNotification({
        type: 'success',
        message: `Berkas ${uploadFile.name} berhasil diajukan. Mesin Suricata sedang menganalisis di background.`,
      });
      setUploadFile(null);
      await refreshAnalyses();
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Gagal memproses file PCAP.' });
    } finally {
      setIsUploading(false);
    }
  };

  const handleExistingAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!existingFilename.trim()) {
      setNotification({ type: 'error', message: 'Masukkan nama file PCAP di storage/pcaps/.' });
      return;
    }

    setIsUploading(true);
    setNotification(null);

    try {
      const res = await fetch('/api/v1/monitoring/pcap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: existingFilename.trim() }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Analisis gagal: HTTP ${res.status}`);
      }

      setNotification({
        type: 'success',
        message: `Analisis untuk ${existingFilename} berhasil dimulai.`,
      });
      setExistingFilename('');
      await refreshAnalyses();
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Gagal memicu analisis PCAP.' });
    } finally {
      setIsUploading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-[#22C55E]/15 text-[#22C55E] border border-[#22C55E]/30">
            <CheckCircle2 className="h-3 w-3" /> SELESAI
          </span>
        );
      case 'RUNNING':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-[#38BDF8]/15 text-[#38BDF8] border border-[#38BDF8]/30">
            <Activity className="h-3 w-3 animate-spin" /> MEMPROSES
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-[#EF4444]/15 text-[#EF4444] border border-[#EF4444]/30">
            <AlertCircle className="h-3 w-3" /> GAGAL
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-[#F59E0B]/15 text-[#F59E0B] border border-[#F59E0B]/30">
            <Clock className="h-3 w-3" /> ANTRIAN
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Notifications */}
      {notification && (
        <div
          className={`rounded-xl p-4 text-xs font-mono border ${
            notification.type === 'success'
              ? 'bg-[#22C55E]/10 border-[#22C55E]/30 text-[#22C55E]'
              : 'bg-[#EF4444]/10 border-[#EF4444]/30 text-[#EF4444]'
          }`}
        >
          {notification.message}
        </div>
      )}

      {/* Upload & Select Forms */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload New PCAP */}
        <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 p-5">
          <div className="flex items-center gap-2 mb-3">
            <Upload className="h-4 w-4 text-[#22C55E]" />
            <h3 className="text-sm font-semibold text-[#F8FAFC]">Unggah Berkas PCAP Baru</h3>
          </div>
          <p className="text-xs text-[#94A3B8] mb-4">
            Unggah rekaman paket jaringan (.pcap, .pcapng, .cap) untuk inspeksi ancaman offline menggunakan Suricata IDS.
          </p>

          <form onSubmit={handleFileUpload} className="space-y-4">
            <div className="rounded-lg border-2 border-dashed border-[rgba(255,255,255,0.1)] p-4 text-center hover:border-[#22C55E]/50 transition-colors">
              <input
                type="file"
                accept=".pcap,.pcapng,.cap"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                className="hidden"
                id="pcap-file-input"
              />
              <label htmlFor="pcap-file-input" className="cursor-pointer block">
                <FileSearch className="h-8 w-8 text-[#64748B] mx-auto mb-2" />
                <span className="text-xs font-medium text-[#CBD5E1]">
                  {uploadFile ? uploadFile.name : 'Pilih file dari komputer'}
                </span>
                <span className="block text-[10px] text-[#64748B] mt-1 font-mono">
                  Maksimum 50 MB (.pcap, .pcapng, .cap)
                </span>
              </label>
            </div>

            <button
              type="submit"
              disabled={isUploading || !uploadFile}
              className="w-full rounded-lg bg-[#22C55E] py-2.5 text-xs font-semibold text-[#0F172A] hover:bg-[#16A34A] transition-colors disabled:opacity-50"
            >
              {isUploading ? 'Memproses Berkas...' : 'Unggah & Analisis PCAP'}
            </button>
          </form>
        </div>

        {/* Analyze Existing Storage PCAP */}
        <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 p-5">
          <div className="flex items-center gap-2 mb-3">
            <HardDrive className="h-4 w-4 text-[#38BDF8]" />
            <h3 className="text-sm font-semibold text-[#F8FAFC]">Analisis PCAP dari Penyimpanan Lab</h3>
          </div>
          <p className="text-xs text-[#94A3B8] mb-4">
            Pilih berkas PCAP yang sudah tersedia di direktori lab lokal terotorisasi (<code className="text-[#38BDF8]">storage/pcaps/</code>).
          </p>

          <form onSubmit={handleExistingAnalyze} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-[#94A3B8] mb-1.5">Nama Berkas PCAP:</label>
              <input
                type="text"
                placeholder="contoh: lab_test_sample.pcap"
                value={existingFilename}
                onChange={(e) => setExistingFilename(e.target.value)}
                className="w-full rounded-lg bg-[#0F172A] px-3 py-2 text-xs text-[#F8FAFC] border border-[rgba(255,255,255,0.08)] focus:border-[#38BDF8] focus:outline-none font-mono"
              />
            </div>

            <button
              type="submit"
              disabled={isUploading || !existingFilename.trim()}
              className="w-full rounded-lg bg-[#38BDF8] py-2.5 text-xs font-semibold text-[#0F172A] hover:bg-[#0284C7] transition-colors disabled:opacity-50"
            >
              {isUploading ? 'Memproses...' : 'Mulai Analisis Berkas Lab'}
            </button>
          </form>
        </div>
      </div>

      {/* History Table */}
      <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-[#F8FAFC]">Riwayat Analisis Berkas PCAP</h3>
            <p className="text-xs text-[#94A3B8]">Daftar analisis offline IDS beserta ringkasan temuan keamanan.</p>
          </div>
          <button
            onClick={refreshAnalyses}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[rgba(255,255,255,0.08)] bg-[#0F172A] px-3 py-1.5 text-xs font-mono text-[#CBD5E1] hover:bg-[#334155] transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin text-[#22C55E]' : ''}`} />
            Perbarui
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0F172A]/80 text-[#94A3B8] font-mono border-b border-[rgba(255,255,255,0.06)]">
              <tr>
                <th className="py-3 px-4">ID</th>
                <th className="py-3 px-4">Nama Berkas</th>
                <th className="py-3 px-4">Ukuran</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Hasil Temuan</th>
                <th className="py-3 px-4">Waktu Pengajuan</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255,255,255,0.04)]">
              {analyses.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[#64748B]">
                    Belum ada riwayat analisis PCAP. Unggah file di atas untuk memulai.
                  </td>
                </tr>
              ) : (
                analyses.map((job) => (
                  <tr key={job.id} className="hover:bg-[rgba(255,255,255,0.02)] transition-colors">
                    <td className="py-3 px-4 font-mono text-[#94A3B8]">#{job.id}</td>
                    <td className="py-3 px-4 font-medium text-[#F8FAFC]">
                      <div>{job.filename}</div>
                      <div className="text-[10px] font-mono text-[#64748B] truncate max-w-xs">
                        SHA256: {job.file_hash.slice(0, 16)}...
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-[#94A3B8]">
                      {job.file_size_bytes ? `${Math.round(job.file_size_bytes / 1024)} KB` : '—'}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">{getStatusBadge(job.status)}</td>
                    <td className="py-3 px-4 whitespace-nowrap font-mono">
                      <span className="text-[#38BDF8] font-semibold">{job.event_count}</span> event(s)
                      {job.alert_count > 0 && (
                        <span className="ml-2 inline-flex items-center gap-1 text-[#EF4444] font-bold">
                          <ShieldAlert className="h-3 w-3" /> {job.alert_count} alert(s)
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono text-[#94A3B8] whitespace-nowrap">
                      {new Date(job.created_at).toLocaleDateString('id-ID', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

