'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import {
  getIncidentDetail,
  requestIncidentTriage,
  correlateIncident,
  updateIncidentStatus,
} from '@/lib/api';
import type { IncidentDetail, AITriageRun } from '@/types';
import Link from 'next/link';
import {
  ArrowLeft,
  BrainCircuit,
  ShieldAlert,
  Flame,
  CheckCircle2,
  Clock,
  RefreshCw,
  AlertTriangle,
  Play,
  FileText,
  Radio,
  Globe,
  Bug,
  Server,
  UserCheck,
  Tag,
} from 'lucide-react';

export default function IncidentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const incidentId = Number(params?.id);

  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Status transition form state
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [statusReason, setStatusReason] = useState<string>('');
  const [resolutionNotes, setResolutionNotes] = useState<string>('');

  async function loadData() {
    if (!incidentId) return;
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await getIncidentDetail(incidentId);
      setIncident(data);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Gagal memuat detail insiden.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [incidentId]);

  async function handleTriggerTriage() {
    if (!incident) return;
    try {
      setActionLoading(true);
      setErrorMsg(null);
      setSuccessMsg(null);
      await requestIncidentTriage(incident.id);
      setSuccessMsg('Permintaan AI Triage berhasil diajukan ke antrean.');
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Gagal mengajukan AI triage.');
    } finally {
      setActionLoading(false);
    }
  }

  async function handleRunCorrelation() {
    if (!incident) return;
    try {
      setActionLoading(true);
      setErrorMsg(null);
      setSuccessMsg(null);
      const res = await correlateIncident(incident.id);
      setSuccessMsg(
        `Korelasi selesai: ${res.evidence_created} bukti baru ditemukan (Skor Keyakinan: ${Math.round(
          res.confidence_score * 100
        )}%).`
      );
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Gagal menjalankan korelasi insiden.');
    } finally {
      setActionLoading(false);
    }
  }

  async function handleStatusUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!incident || !selectedStatus) return;
    try {
      setActionLoading(true);
      setErrorMsg(null);
      setSuccessMsg(null);
      await updateIncidentStatus(
        incident.id,
        selectedStatus,
        statusReason,
        resolutionNotes
      );
      setSuccessMsg(`Status siklus insiden berhasil diperbarui menjadi ${selectedStatus}.`);
      setSelectedStatus('');
      setStatusReason('');
      setResolutionNotes('');
      await loadData();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Gagal memperbarui status insiden.');
    } finally {
      setActionLoading(false);
    }
  }

  const latestTriage = incident?.triage_runs?.[0];
  let parsedTriageJson: any = null;
  if (latestTriage?.result_json) {
    try {
      parsedTriageJson = JSON.parse(latestTriage.result_json);
    } catch {
      // ignore
    }
  }

  return (
    <AppShell>
      <Header title={`Insiden #${incidentId} — Detail & AI Triage`} />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Back Link & Title */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/incidents"
              className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold font-mono text-white">Insiden #{incidentId}</h1>
                {incident && (
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-mono font-semibold border ${
                      incident.severity === 'CRITICAL'
                        ? 'bg-red-500/15 text-red-400 border-red-500/30'
                        : incident.severity === 'HIGH'
                        ? 'bg-orange-500/15 text-orange-400 border-orange-500/30'
                        : 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30'
                    }`}
                  >
                    {incident.severity}
                  </span>
                )}
                {incident && (
                  <span className="px-2 py-0.5 rounded text-xs font-mono bg-blue-500/15 text-blue-400 border border-blue-500/30">
                    {incident.lifecycle_status || 'OPEN'}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">
                Pusat investigasi ancaman teritorial dengan korelasi bukti multi-sumber dan asistensi AI.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRunCorrelation}
              disabled={actionLoading}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-500/10 border border-blue-500/30 text-blue-400 hover:bg-blue-500/20 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${actionLoading ? 'animate-spin' : ''}`} />
              Jalankan Korelasi
            </button>
            <button
              onClick={handleTriggerTriage}
              disabled={actionLoading}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-50 transition-colors"
            >
              <BrainCircuit className="h-3.5 w-3.5" />
              Minta AI Triage
            </button>
          </div>
        </div>

        {/* Notifications */}
        {errorMsg && (
          <div className="p-4 rounded-xl border border-red-500/30 bg-red-950/20 text-red-300 text-xs flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 text-red-400" />
            <span>{errorMsg}</span>
          </div>
        )}
        {successMsg && (
          <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
            <span>{successMsg}</span>
          </div>
        )}

        {loading ? (
          <div className="p-12 text-center text-slate-500 font-mono text-sm">
            Memuat data insiden...
          </div>
        ) : !incident ? (
          <div className="p-12 text-center text-slate-500 font-mono text-sm">
            Insiden tidak ditemukan.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Cols: Details, AI Triage Result, Evidence */}
            <div className="lg:col-span-2 space-y-6">
              {/* Incident Header Info */}
              <div className="p-5 rounded-xl border border-slate-800 bg-[#0F172A]/80 space-y-4">
                <h3 className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
                  Metadata Insiden
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                  <div>
                    <span className="text-slate-500 block">ID Aset</span>
                    <span className="text-white font-bold">#{incident.asset_id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">IP Penyerang</span>
                    <span className="text-white font-bold">{incident.source_ip}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Jenis Serangan</span>
                    <span className="text-white font-bold">{incident.attack_type}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Waktu Terdeteksi</span>
                    <span className="text-white font-bold">
                      {incident.timestamp ? new Date(incident.timestamp).toLocaleString('id-ID') : '-'}
                    </span>
                  </div>
                </div>

                {incident.payload && (
                  <div>
                    <span className="text-slate-500 text-xs font-mono block mb-1">Muatan / Signature:</span>
                    <pre className="p-3 rounded-lg bg-black/40 border border-slate-800 text-emerald-400 font-mono text-xs overflow-x-auto whitespace-pre-wrap">
                      {incident.payload}
                    </pre>
                  </div>
                )}
              </div>

              {/* AI Triage Card */}
              <div className="p-5 rounded-xl border border-emerald-500/20 bg-gradient-to-b from-[#0F172A] to-emerald-950/10 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <BrainCircuit className="h-5 w-5 text-emerald-400" />
                    <h3 className="text-sm font-semibold text-white">Analisis AI Triage</h3>
                  </div>
                  {latestTriage && (
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                        latestTriage.status === 'COMPLETED'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                          : latestTriage.status === 'REQUIRES_REVIEW'
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                          : latestTriage.status === 'RUNNING'
                          ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                          : 'bg-slate-500/10 text-slate-400 border-slate-500/30'
                      }`}
                    >
                      {latestTriage.status} ({latestTriage.provider})
                    </span>
                  )}
                </div>

                {!latestTriage ? (
                  <div className="text-center py-6 text-slate-500 text-xs">
                    <BrainCircuit className="h-8 w-8 mx-auto mb-2 text-slate-600" />
                    Belum ada AI Triage yang dijalankan. Klik tombol{' '}
                    <span className="text-emerald-400 font-semibold">&quot;Minta AI Triage&quot;</span> di atas
                    untuk memulai analisis otomatis.
                  </div>
                ) : (
                  <div className="space-y-4 text-xs">
                    {/* Scores */}
                    <div className="grid grid-cols-3 gap-3">
                      <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">
                          Tingkat Risiko
                        </span>
                        <span
                          className={`text-base font-bold font-mono ${
                            parsedTriageJson?.risk_level === 'CRITICAL'
                              ? 'text-red-400'
                              : parsedTriageJson?.risk_level === 'HIGH'
                              ? 'text-orange-400'
                              : 'text-yellow-400'
                          }`}
                        >
                          {parsedTriageJson?.risk_level || 'N/A'}
                        </span>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">
                          Skor Prioritas
                        </span>
                        <span className="text-base font-bold font-mono text-white">
                          {parsedTriageJson?.priority_score ?? 'N/A'} / 100
                        </span>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">
                          Tingkat Keyakinan
                        </span>
                        <span className="text-base font-bold font-mono text-emerald-400">
                          {latestTriage.confidence_score
                            ? `${Math.round(latestTriage.confidence_score * 100)}%`
                            : 'N/A'}
                        </span>
                      </div>
                    </div>

                    {/* Explanation */}
                    <div>
                      <span className="text-slate-400 font-semibold block mb-1">
                        Penjelasan Ancaman:
                      </span>
                      <p className="text-slate-300 leading-relaxed bg-slate-900/40 p-3 rounded-lg border border-slate-800/80">
                        {parsedTriageJson?.attack_explanation || incident.ai_analysis || 'Tidak ada penjelasan.'}
                      </p>
                    </div>

                    {/* Recommended Actions */}
                    {parsedTriageJson?.recommended_actions?.length > 0 && (
                      <div>
                        <span className="text-slate-400 font-semibold block mb-1.5">
                          Rekomendasi Tindakan Operator:
                        </span>
                        <ul className="space-y-1.5 list-disc list-inside text-slate-300 bg-slate-900/40 p-3 rounded-lg border border-slate-800/80">
                          {parsedTriageJson.recommended_actions.map((act: string, idx: number) => (
                            <li key={idx} className="leading-snug">
                              {act}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Operator Note Warning */}
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300/90 text-[11px] flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
                      <span>
                        Kebijakan KAWAL SIBER: AI hanya memberikan rekomendasi asesmen. Seluruh
                        mitigasi dan transisi status insiden memerlukan persetujuan operator manusia.
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Correlated Evidence Section */}
              <div className="p-5 rounded-xl border border-slate-800 bg-[#0F172A]/80 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-blue-400" />
                    <h3 className="text-sm font-semibold text-white">Bukti Terkorelasi (Multi-Source)</h3>
                  </div>
                  <span className="text-xs font-mono text-slate-400">
                    {incident.evidence_items?.length || 0} bukti tercatat
                  </span>
                </div>

                {(!incident.evidence_items || incident.evidence_items.length === 0) ? (
                  <div className="text-center py-6 text-slate-500 text-xs">
                    Belum ada bukti yang terkorelasi. Klik &quot;Jalankan Korelasi&quot; untuk mencari keterkaitan dengan event Suricata, Web Finding Deep Eye, atau Nmap.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {incident.evidence_items.map((ev) => (
                      <div
                        key={ev.id}
                        className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs flex items-start gap-3"
                      >
                        <div className="p-1.5 rounded bg-slate-800 shrink-0 text-blue-400 mt-0.5">
                          {ev.source_type === 'SURICATA_EVENT' ? (
                            <Radio className="h-4 w-4 text-purple-400" />
                          ) : ev.source_type === 'WEB_FINDING' ? (
                            <Bug className="h-4 w-4 text-orange-400" />
                          ) : (
                            <Server className="h-4 w-4 text-cyan-400" />
                          )}
                        </div>
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-[11px] font-bold text-slate-300">
                              {ev.source_type} #{ev.source_record_id || '-'}
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono">
                              {ev.relationship_type}
                            </span>
                          </div>
                          <p className="text-slate-400 leading-snug">{ev.evidence_summary}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Col: Timeline & Operator Lifecycle Controls */}
            <div className="space-y-6">
              {/* Lifecycle Controller Form */}
              <div className="p-5 rounded-xl border border-slate-800 bg-[#0F172A]/80 space-y-4">
                <div className="flex items-center gap-2">
                  <UserCheck className="h-4 w-4 text-emerald-400" />
                  <h3 className="text-sm font-semibold text-white">Kontrol Respon Operator</h3>
                </div>

                <form onSubmit={handleStatusUpdate} className="space-y-3 text-xs">
                  <div>
                    <label className="text-slate-400 block mb-1 font-mono">Status Saat Ini:</label>
                    <div className="p-2 rounded bg-slate-900 border border-slate-800 font-mono font-bold text-white">
                      {incident.lifecycle_status || 'OPEN'}
                    </div>
                  </div>

                  <div>
                    <label className="text-slate-400 block mb-1 font-mono">Ubah Status Menjadi:</label>
                    <select
                      value={selectedStatus}
                      onChange={(e) => setSelectedStatus(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white font-mono focus:outline-none focus:border-emerald-500"
                    >
                      <option value="">-- Pilih Transisi Status --</option>
                      <option value="ACKNOWLEDGED">ACKNOWLEDGED (Dikonfirmasi)</option>
                      <option value="INVESTIGATING">INVESTIGATING (Sedang Diinvestigasi)</option>
                      <option value="MITIGATED">MITIGATED (Telah Dimitigasi)</option>
                      <option value="RESOLVED">RESOLVED (Tuntas / Selesai)</option>
                      <option value="FALSE_POSITIVE">FALSE_POSITIVE (Positif Palsu)</option>
                      <option value="OPEN">OPEN (Buka Kembali)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-slate-400 block mb-1 font-mono">Alasan / Catatan:</label>
                    <input
                      type="text"
                      value={statusReason}
                      onChange={(e) => setStatusReason(e.target.value)}
                      placeholder="Contoh: Firewall rule telah diterapkan"
                      className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  {(selectedStatus === 'RESOLVED' || selectedStatus === 'FALSE_POSITIVE') && (
                    <div>
                      <label className="text-slate-400 block mb-1 font-mono">Catatan Penyelesaian:</label>
                      <textarea
                        rows={2}
                        value={resolutionNotes}
                        onChange={(e) => setResolutionNotes(e.target.value)}
                        placeholder="Detail penutupan insiden..."
                        className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={actionLoading || !selectedStatus}
                    className="w-full py-2 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold disabled:opacity-50 transition-colors"
                  >
                    Simpan Perubahan Status
                  </button>
                </form>
              </div>

              {/* Timeline Section */}
              <div className="p-5 rounded-xl border border-slate-800 bg-[#0F172A]/80 space-y-4">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-purple-400" />
                  <h3 className="text-sm font-semibold text-white">Kronologi & Timeline</h3>
                </div>

                {(!incident.timeline_events || incident.timeline_events.length === 0) ? (
                  <div className="text-center py-6 text-slate-500 text-xs">
                    Belum ada riwayat kronologi.
                  </div>
                ) : (
                  <div className="relative pl-4 space-y-4 border-l border-slate-800 text-xs">
                    {incident.timeline_events.map((te) => (
                      <div key={te.id} className="relative group">
                        {/* Dot indicator */}
                        <div className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-emerald-500 border border-[#0F172A]" />
                        <div className="space-y-0.5">
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-[11px] font-bold text-slate-300">
                              {te.event_type}
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono">
                              {new Date(te.timestamp).toLocaleTimeString('id-ID')}
                            </span>
                          </div>
                          <p className="text-slate-400 text-[11px] leading-snug">{te.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </AppShell>
  );
}
