'use client';

import { useState } from 'react';
import type { PaginatedSecurityEvents, SecurityEvent } from '@/types';
import { ShieldAlert, Search, Filter, Shield, AlertTriangle, Eye, ArrowRight } from 'lucide-react';

interface AlertsClientProps {
  initialData: PaginatedSecurityEvents;
}

export default function AlertsClient({ initialData }: AlertsClientProps) {
  const [data, setData] = useState<PaginatedSecurityEvents>(initialData);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
  const [activeEvent, setActiveEvent] = useState<SecurityEvent | null>(null);

  const filterAlerts = async (sev: string, search: string) => {
    setSelectedSeverity(sev);
    const params = new URLSearchParams();
    if (sev !== 'ALL') params.set('severity', sev);
    if (search.trim()) params.set('search', search.trim());
    params.set('page', '1');
    params.set('page_size', '50');

    try {
      const res = await fetch(`/api/v1/security-alerts?${params.toString()}`);
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch {
      // fallback
    }
  };

  const getSeverityBadge = (sev: number | null) => {
    switch (sev) {
      case 1:
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#EF4444]/20 text-[#EF4444] border border-[#EF4444]/40">CRITICAL</span>;
      case 2:
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#F97316]/20 text-[#F97316] border border-[#F97316]/40">HIGH</span>;
      case 3:
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/40">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#38BDF8]/20 text-[#38BDF8] border border-[#38BDF8]/40">LOW</span>;
    }
  };

  return (
    <div className="space-y-4">
      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 p-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#64748B]" />
          <input
            type="text"
            placeholder="Cari signature, IP sumber, tujuan..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              filterAlerts(selectedSeverity, e.target.value);
            }}
            className="w-full rounded-lg bg-[#0F172A] pl-9 pr-4 py-2 text-xs text-[#F8FAFC] placeholder-[#64748B] border border-[rgba(255,255,255,0.08)] focus:border-[#22C55E] focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto">
          <Filter className="h-4 w-4 text-[#64748B] shrink-0" />
          {['ALL', '1', '2', '3', '4'].map((s) => (
            <button
              key={s}
              onClick={() => filterAlerts(s, searchTerm)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-colors ${
                selectedSeverity === s
                  ? 'bg-[#22C55E]/20 text-[#22C55E] border border-[#22C55E]/40'
                  : 'bg-[#0F172A] text-[#94A3B8] border border-[rgba(255,255,255,0.06)] hover:bg-[#334155]'
              }`}
            >
              {s === 'ALL' ? 'Semua' : s === '1' ? 'Kritis' : s === '2' ? 'Tinggi' : s === '3' ? 'Sedang' : 'Rendah'}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0F172A]/80 text-[#94A3B8] font-mono border-b border-[rgba(255,255,255,0.06)]">
              <tr>
                <th className="py-3 px-4">Waktu</th>
                <th className="py-3 px-4">Tingkat</th>
                <th className="py-3 px-4">Signature & Kategori</th>
                <th className="py-3 px-4">Alur Trafik (Sumber → Tujuan)</th>
                <th className="py-3 px-4">Protokol</th>
                <th className="py-3 px-4">Aset Terkorelasi</th>
                <th className="py-3 px-4 text-right">Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255,255,255,0.04)]">
              {data.items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-[#64748B]">
                    Tidak ada peringatan keamanan ditemukan.
                  </td>
                </tr>
              ) : (
                data.items.map((alert) => (
                  <tr key={alert.id} className="hover:bg-[rgba(255,255,255,0.02)] transition-colors">
                    <td className="py-3 px-4 font-mono text-[#94A3B8] whitespace-nowrap">
                      {new Date(alert.timestamp).toLocaleTimeString('id-ID', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">{getSeverityBadge(alert.severity)}</td>
                    <td className="py-3 px-4 min-w-[200px]">
                      <div className="font-medium text-[#F8FAFC]">{alert.signature}</div>
                      <div className="text-[10px] font-mono text-[#64748B]">
                        SID: {alert.signature_id || 'N/A'} • {alert.category || 'Umum'}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono whitespace-nowrap">
                      <span className="text-[#E2E8F0]">{alert.source_ip}:{alert.source_port ?? '—'}</span>
                      <ArrowRight className="inline-block h-3 w-3 mx-1 text-[#64748B]" />
                      <span className="text-[#38BDF8]">{alert.destination_ip}:{alert.destination_port ?? '—'}</span>
                    </td>
                    <td className="py-3 px-4 font-mono text-[#94A3B8]">{alert.protocol ?? 'IP'}</td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      {alert.asset_id ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-[#22C55E]/15 text-[#22C55E] border border-[#22C55E]/30">
                          <Shield className="h-3 w-3" /> Aset #{alert.asset_id}
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono text-[#64748B]">Eksternal</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => setActiveEvent(alert)}
                        className="inline-flex items-center gap-1 rounded bg-[#334155]/60 hover:bg-[#334155] px-2.5 py-1 text-[11px] text-[#CBD5E1] transition-colors"
                      >
                        <Eye className="h-3 w-3" /> Raw JSON
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Raw Event Modal */}
      {activeEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-xl border border-[rgba(255,255,255,0.1)] bg-[#0F172A] p-5 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[rgba(255,255,255,0.06)]">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-[#EF4444]" />
                <h3 className="text-sm font-bold text-[#F8FAFC]">Detail Telemetri Suricata EVE JSON</h3>
              </div>
              <button
                onClick={() => setActiveEvent(null)}
                className="text-xs text-[#94A3B8] hover:text-white"
              >
                ✕ Tutup
              </button>
            </div>
            <div className="mt-4 space-y-3">
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div><span className="text-[#64748B]">Event ID:</span> <span className="text-[#E2E8F0]">{activeEvent.event_id}</span></div>
                <div><span className="text-[#64748B]">Tipe:</span> <span className="text-[#22C55E]">{activeEvent.event_type}</span></div>
                <div><span className="text-[#64748B]">Signature:</span> <span className="text-[#F8FAFC]">{activeEvent.signature}</span></div>
                <div><span className="text-[#64748B]">SID:</span> <span className="text-[#E2E8F0]">{activeEvent.signature_id}</span></div>
              </div>
              <div className="text-[11px] font-mono text-[#94A3B8]">Sanitized Raw EVE JSON:</div>
              <pre className="max-h-64 overflow-y-auto rounded-lg bg-[#020617] p-3 text-[11px] font-mono text-[#38BDF8] border border-[rgba(255,255,255,0.04)]">
                {activeEvent.raw_event
                  ? JSON.stringify(JSON.parse(activeEvent.raw_event), null, 2)
                  : 'Tidak ada raw payload tersimpan.'}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

