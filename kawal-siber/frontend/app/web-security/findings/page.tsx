'use client';

import { useState, useEffect, Suspense } from 'react';
import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import { getWebFindings, updateWebFindingStatus } from '@/lib/api';
import type { WebFinding } from '@/types';
import Link from 'next/link';
import {
  Bug,
  Filter,
  Search,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
  AlertTriangle,
  Info,
  CheckCircle,
} from 'lucide-react';
import { useSearchParams } from 'next/navigation';

function WebFindingsContent() {
  const searchParams = useSearchParams();
  const targetIdParam = searchParams.get('target_id');

  const [findings, setFindings] = useState<WebFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');

  async function loadFindings() {
    setLoading(true);
    setError(null);
    try {
      const res = await getWebFindings({
        severity: severityFilter || undefined,
        finding_status: statusFilter || undefined,
        web_target_id: targetIdParam ? Number(targetIdParam) : undefined,
        search: searchTerm || undefined,
      });
      setFindings(res);
    } catch (err: any) {
      setError(err?.message || 'Gagal memuat temuan kerentanan.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFindings();
  }, [severityFilter, statusFilter, targetIdParam]);

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    loadFindings();
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

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'CONFIRMED':
        return 'bg-[#EF4444]/15 text-[#EF4444] border-[#EF4444]/30';
      case 'NEEDS_REVIEW':
        return 'bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]/30';
      case 'FALSE_POSITIVE':
        return 'bg-[#64748B]/15 text-[#94A3B8] border-[#64748B]/30';
      case 'ACCEPTED_RISK':
        return 'bg-[#A855F7]/15 text-[#C084FC] border-[#A855F7]/30';
      default:
        return 'bg-[#3B82F6]/15 text-[#60A5FA] border-[#3B82F6]/30';
    }
  };

  return (
    <AppShell>
      <Header title="Katalog Temuan Kerentanan Web (Vulnerabilities)" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Filter Controls Bar */}
        <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <form onSubmit={handleSearchSubmit} className="flex-1 flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[#64748B]" />
              <input
                type="text"
                placeholder="Cari kerentanan berdasarkan judul atau deskripsi..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] text-xs text-[#F8FAFC] focus:outline-none focus:border-[#22C55E]"
              />
            </div>
            <button
              type="submit"
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#1E293B] text-[#CBD5E1] hover:text-[#F8FAFC] border border-[rgba(255,255,255,0.08)]"
            >
              Cari
            </button>
          </form>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5">
              <Filter className="h-3.5 w-3.5 text-[#64748B]" />
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] text-xs text-[#F8FAFC] focus:outline-none focus:border-[#22C55E]"
              >
                <option value="">Semua Severity</option>
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
                <option value="INFORMATIONAL">INFORMATIONAL</option>
              </select>
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg bg-[#1E293B] border border-[rgba(255,255,255,0.1)] text-xs text-[#F8FAFC] focus:outline-none focus:border-[#22C55E]"
            >
              <option value="">Semua Status</option>
              <option value="UNVERIFIED">UNVERIFIED</option>
              <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
              <option value="CONFIRMED">CONFIRMED</option>
              <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
              <option value="ACCEPTED_RISK">ACCEPTED_RISK</option>
            </select>

            <button
              onClick={loadFindings}
              disabled={loading}
              className="p-1.5 rounded-lg bg-[#1E293B] text-[#94A3B8] hover:text-[#F8FAFC] border border-[rgba(255,255,255,0.08)]"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Findings Table */}
        <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-xs text-[#64748B] flex items-center justify-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin text-[#3B82F6]" />
              Memuat temuan kerentanan...
            </div>
          ) : findings.length === 0 ? (
            <div className="p-12 text-center space-y-2">
              <Bug className="h-8 w-8 text-[#475569] mx-auto" />
              <p className="text-xs text-[#94A3B8]">Tidak ada temuan kerentanan yang sesuai kriteria filter.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#1E293B]/50 font-mono text-[#94A3B8] border-b border-[rgba(255,255,255,0.06)]">
                  <tr>
                    <th className="p-3">Severity</th>
                    <th className="p-3">Judul Kerentanan</th>
                    <th className="p-3">Kategori / Tipe</th>
                    <th className="p-3">Affected URL</th>
                    <th className="p-3">Confidence</th>
                    <th className="p-3">Status Triage</th>
                    <th className="p-3">Terakhir Terdeteksi</th>
                    <th className="p-3 text-right">Detail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(255,255,255,0.05)] text-[#CBD5E1]">
                  {findings.map((f) => (
                    <tr key={f.id} className="hover:bg-[#1E293B]/30 transition-colors">
                      <td className="p-3">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getSeverityBadge(
                            f.severity,
                          )}`}
                        >
                          {f.severity}
                        </span>
                      </td>
                      <td className="p-3 max-w-xs">
                        <Link
                          href={`/web-security/findings/${f.id}`}
                          className="font-semibold text-[#F8FAFC] hover:text-[#38BDF8] transition-colors block truncate"
                        >
                          {f.title}
                        </Link>
                        <span className="text-[11px] text-[#64748B] truncate block">{f.description}</span>
                      </td>
                      <td className="p-3 font-mono text-[#A855F7]">
                        {f.vulnerability_type}
                      </td>
                      <td className="p-3 font-mono text-[#38BDF8] max-w-xs truncate">
                        {f.affected_url}
                      </td>
                      <td className="p-3 font-mono text-[#94A3B8]">
                        {f.confidence}
                      </td>
                      <td className="p-3">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${getStatusBadge(
                            f.finding_status,
                          )}`}
                        >
                          {f.finding_status}
                        </span>
                      </td>
                      <td className="p-3 font-mono text-[#64748B]">
                        {new Date(f.last_seen).toLocaleDateString('id-ID', {
                          day: '2-digit',
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="p-3 text-right">
                        <Link
                          href={`/web-security/findings/${f.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-semibold bg-[#1E293B] text-[#38BDF8] border border-[rgba(255,255,255,0.08)] hover:bg-[#334155] transition-colors"
                        >
                          Buka
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </AppShell>
  );
}

export default function WebFindingsPage() {
  return (
    <Suspense
      fallback={
        <AppShell>
          <Header title="Katalog Temuan Kerentanan Web (Vulnerabilities)" />
          <div className="p-12 text-center text-xs text-[#64748B]">Memuat temuan kerentanan...</div>
        </AppShell>
      }
    >
      <WebFindingsContent />
    </Suspense>
  );
}

