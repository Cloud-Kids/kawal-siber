'use client';

import { useState } from 'react';
import type { PaginatedSecurityEvents, SecurityEvent } from '@/types';
import { Activity, Search, Filter, ArrowRight, Eye, Layers } from 'lucide-react';

interface EventsClientProps {
  initialData: PaginatedSecurityEvents;
}

export default function EventsClient({ initialData }: EventsClientProps) {
  const [data, setData] = useState<PaginatedSecurityEvents>(initialData);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [selectedProto, setSelectedProto] = useState<string>('ALL');
  const [activeEvent, setActiveEvent] = useState<SecurityEvent | null>(null);

  const fetchEvents = async (type: string, proto: string, search: string) => {
    setSelectedType(type);
    setSelectedProto(proto);
    const params = new URLSearchParams();
    if (type !== 'ALL') params.set('event_type', type);
    if (proto !== 'ALL') params.set('protocol', proto);
    if (search.trim()) params.set('search', search.trim());
    params.set('page', '1');
    params.set('page_size', '50');

    try {
      const res = await fetch(`/api/v1/security-events?${params.toString()}`);
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch {
      // fallback
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'alert':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#EF4444]/20 text-[#EF4444] border border-[#EF4444]/40">ALERT</span>;
      case 'anomaly':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/40">ANOMALY</span>;
      case 'http':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#38BDF8]/20 text-[#38BDF8] border border-[#38BDF8]/40">HTTP</span>;
      case 'dns':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#A855F7]/20 text-[#A855F7] border border-[#A855F7]/40">DNS</span>;
      case 'tls':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#06B6D4]/20 text-[#06B6D4] border border-[#06B6D4]/40">TLS</span>;
      case 'flow':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#64748B]/20 text-[#94A3B8] border border-[#64748B]/40">FLOW</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#475569]/20 text-[#CBD5E1] border border-[#475569]/40">{type.toUpperCase()}</span>;
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#1E293B]/60 p-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#64748B]" />
          <input
            type="text"
            placeholder="Cari IP sumber, tujuan, atau signature..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              fetchEvents(selectedType, selectedProto, e.target.value);
            }}
            className="w-full rounded-lg bg-[#0F172A] pl-9 pr-4 py-2 text-xs text-[#F8FAFC] placeholder-[#64748B] border border-[rgba(255,255,255,0.08)] focus:border-[#22C55E] focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto">
          <span className="text-xs font-mono text-[#64748B] shrink-0">Tipe:</span>
          {['ALL', 'alert', 'anomaly', 'flow', 'http', 'dns', 'tls'].map((t) => (
            <button
              key={t}
              onClick={() => fetchEvents(t, selectedProto, searchTerm)}
              className={`px-2.5 py-1 rounded text-[11px] font-mono transition-colors ${
                selectedType === t
                  ? 'bg-[#22C55E]/20 text-[#22C55E] border border-[#22C55E]/40'
                  : 'bg-[#0F172A] text-[#94A3B8] border border-[rgba(255,255,255,0.06)] hover:bg-[#334155]'
              }`}
            >
              {t.toUpperCase()}
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
                <th className="py-3 px-4">Tipe Event</th>
                <th className="py-3 px-4">Protokol</th>
                <th className="py-3 px-4">Aliran (IP Sumber → Tujuan)</th>
                <th className="py-3 px-4">Signature / Deskripsi</th>
                <th className="py-3 px-4 text-right">Raw JSON</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255,255,255,0.04)]">
              {data.items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[#64748B]">
                    Tidak ada event telemetri ditemukan.
                  </td>
                </tr>
              ) : (
                data.items.map((evt) => (
                  <tr key={evt.id} className="hover:bg-[rgba(255,255,255,0.02)] transition-colors">
                    <td className="py-2.5 px-4 font-mono text-[#94A3B8] whitespace-nowrap">
                      {new Date(evt.timestamp).toLocaleTimeString('id-ID', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </td>
                    <td className="py-2.5 px-4 whitespace-nowrap">{getTypeBadge(evt.event_type)}</td>
                    <td className="py-2.5 px-4 font-mono text-[#E2E8F0]">{evt.protocol ?? '—'}</td>
                    <td className="py-2.5 px-4 font-mono whitespace-nowrap">
                      <span className="text-[#CBD5E1]">{evt.source_ip || '—'}:{evt.source_port ?? '—'}</span>
                      <ArrowRight className="inline-block h-3 w-3 mx-1 text-[#64748B]" />
                      <span className="text-[#38BDF8]">{evt.destination_ip || '—'}:{evt.destination_port ?? '—'}</span>
                    </td>
                    <td className="py-2.5 px-4 min-w-[200px] text-[#94A3B8] truncate">
                      {evt.signature || `${evt.event_type.toUpperCase()} telemetry log`}
                    </td>
                    <td className="py-2.5 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => setActiveEvent(evt)}
                        className="inline-flex items-center gap-1 rounded bg-[#334155]/60 hover:bg-[#334155] px-2.5 py-1 text-[11px] text-[#CBD5E1] transition-colors"
                      >
                        <Eye className="h-3 w-3" /> Lihat
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
                <Layers className="h-5 w-5 text-[#38BDF8]" />
                <h3 className="text-sm font-bold text-[#F8FAFC]">Inspeksi EVE JSON Raw Event</h3>
              </div>
              <button
                onClick={() => setActiveEvent(null)}
                className="text-xs text-[#94A3B8] hover:text-white"
              >
                ✕ Tutup
              </button>
            </div>
            <div className="mt-4 space-y-3">
              <pre className="max-h-72 overflow-y-auto rounded-lg bg-[#020617] p-3 text-[11px] font-mono text-[#38BDF8] border border-[rgba(255,255,255,0.04)]">
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

