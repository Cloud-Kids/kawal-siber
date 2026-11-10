import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import { getWebSecurityStatistics, getWebAssessments, getWebTargets } from '@/lib/api';
import type { WebSecurityStatistics, WebAssessment, WebTarget } from '@/types';
import Link from 'next/link';
import {
  Globe,
  ShieldAlert,
  ShieldCheck,
  Activity,
  Bug,
  ListFilter,
  Crosshair,
  ExternalLink,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Flame,
} from 'lucide-react';

export const dynamic = 'force-dynamic';

export default async function WebSecurityPage() {
  let stats: WebSecurityStatistics = {
    total_targets: 0,
    total_assessments: 0,
    total_findings: 0,
    critical_findings: 0,
    high_findings: 0,
    medium_findings: 0,
    low_findings: 0,
    informational_findings: 0,
    severity_distribution: { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFORMATIONAL: 0 },
    status_distribution: {},
    top_vulnerabilities: [],
  };

  let recentAssessments: WebAssessment[] = [];
  let targets: WebTarget[] = [];

  try {
    const [s, a, t] = await Promise.all([
      getWebSecurityStatistics().catch(() => stats),
      getWebAssessments().catch(() => []),
      getWebTargets().catch(() => []),
    ]);
    stats = s;
    recentAssessments = (a || []).slice(0, 5);
    targets = t || [];
  } catch {
    // Graceful fallback
  }

  const targetMap = new Map<number, WebTarget>(targets.map((t) => [t.id, t]));

  return (
    <AppShell>
      <Header title="Asesmen Keamanan Aplikasi Web — Deep Eye" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Banner Engine Deep Eye */}
        <div className="rounded-xl border border-[#3B82F6]/30 bg-gradient-to-r from-[#0F172A] via-[#1E293B] to-[#0F172A] p-5 shadow-lg">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#3B82F6]/20 text-[#3B82F6] border border-[#3B82F6]/40">
                <Globe className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-[#F8FAFC]">Deep Eye Security Engine (v1.4.0 Hanzou)</h2>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-[#22C55E]/20 text-[#22C55E] border border-[#22C55E]/30">
                    TERHUBUNG & SIAP
                  </span>
                </div>
                <p className="text-xs text-[#94A3B8] mt-0.5">
                  Modul asesmen keamanan aplikasi web lokal, audit header HTTP, TLS, cookie, CORS, CSP, dan kerentanan non-destruktif.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Link
                href="/web-security/targets"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#1E293B] text-[#F8FAFC] border border-[rgba(255,255,255,0.1)] hover:bg-[#334155] transition-colors"
              >
                <Crosshair className="h-3.5 w-3.5 text-[#3B82F6]" />
                Kelola Target
              </Link>
              <Link
                href="/web-security/assessments"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#22C55E] text-[#0F172A] hover:bg-[#16A34A] transition-colors shadow-sm"
              >
                <ListFilter className="h-3.5 w-3.5" />
                Jalankan Asesmen
              </Link>
            </div>
          </div>
        </div>

        {/* Top Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-[#94A3B8]">Target Terdaftar</p>
              <p className="text-2xl font-bold font-mono text-[#F8FAFC] mt-1">{stats.total_targets}</p>
              <p className="text-[11px] text-[#64748B] mt-0.5">Laboratorium localhost</p>
            </div>
            <div className="h-10 w-10 rounded-lg bg-[#3B82F6]/10 border border-[#3B82F6]/20 flex items-center justify-center text-[#3B82F6]">
              <Crosshair className="h-5 w-5" />
            </div>
          </div>

          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-[#94A3B8]">Total Asesmen</p>
              <p className="text-2xl font-bold font-mono text-[#22C55E] mt-1">{stats.total_assessments}</p>
              <p className="text-[11px] text-[#64748B] mt-0.5">Riwayat eksekusi</p>
            </div>
            <div className="h-10 w-10 rounded-lg bg-[#22C55E]/10 border border-[#22C55E]/20 flex items-center justify-center text-[#22C55E]">
              <Activity className="h-5 w-5" />
            </div>
          </div>

          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-[#94A3B8]">Total Temuan</p>
              <p className="text-2xl font-bold font-mono text-[#F59E0B] mt-1">{stats.total_findings}</p>
              <p className="text-[11px] text-[#64748B] mt-0.5">Terdeduplikasi unik</p>
            </div>
            <div className="h-10 w-10 rounded-lg bg-[#F59E0B]/10 border border-[#F59E0B]/20 flex items-center justify-center text-[#F59E0B]">
              <Bug className="h-5 w-5" />
            </div>
          </div>

          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-[#94A3B8]">Critical / High</p>
              <p className="text-2xl font-bold font-mono text-[#EF4444] mt-1">
                {stats.critical_findings + stats.high_findings}
              </p>
              <p className="text-[11px] text-[#64748B] mt-0.5">Perlu mitigasi segera</p>
            </div>
            <div className="h-10 w-10 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/20 flex items-center justify-center text-[#EF4444]">
              <ShieldAlert className="h-5 w-5" />
            </div>
          </div>
        </div>

        {/* Profile Policy & Severity Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Policy Overview */}
          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-5 space-y-4">
            <h3 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-[#22C55E]" />
              Kebijakan Profil Asesmen
            </h3>
            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-[#1E293B]/60 border border-[rgba(255,255,255,0.05)]">
                <div className="flex items-center justify-between font-bold text-[#3B82F6]">
                  <span>PASSIVE ASSESSMENT</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#3B82F6]/20 font-mono">DEFAULT</span>
                </div>
                <p className="text-[#94A3B8] mt-1 leading-relaxed">
                  Audit non-intrusif: verifikasi Security Headers (CSP, X-Frame, HSTS), Cookie Flags (HttpOnly, Secure, SameSite), konfigurasi CORS, dan kebocoran metadata.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-[#1E293B]/60 border border-[rgba(255,255,255,0.05)]">
                <div className="flex items-center justify-between font-bold text-[#22C55E]">
                  <span>SAFE LOCAL ASSESSMENT</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#22C55E]/20 font-mono">LAB SAFE</span>
                </div>
                <p className="text-[#94A3B8] mt-1 leading-relaxed">
                  Asesmen teruji non-destruktif: enumerasi metode HTTP, canary endpoint paths, rate-limited maksimal 50 request, tanpa brute force, tanpa DoS.
                </p>
              </div>
            </div>
          </div>

          {/* Severity Breakdown */}
          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-5 space-y-4">
            <h3 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
              <Flame className="h-4 w-4 text-[#F59E0B]" />
              Distribusi Tingkat Keparahan
            </h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs font-mono text-[#CBD5E1] mb-1">
                  <span className="text-[#EF4444] font-semibold">CRITICAL</span>
                  <span>{stats.critical_findings}</span>
                </div>
                <div className="h-2 w-full bg-[#1E293B] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#EF4444]"
                    style={{ width: `${stats.total_findings ? (stats.critical_findings / stats.total_findings) * 100 : 0}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono text-[#CBD5E1] mb-1">
                  <span className="text-[#F97316] font-semibold">HIGH</span>
                  <span>{stats.high_findings}</span>
                </div>
                <div className="h-2 w-full bg-[#1E293B] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#F97316]"
                    style={{ width: `${stats.total_findings ? (stats.high_findings / stats.total_findings) * 100 : 0}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono text-[#CBD5E1] mb-1">
                  <span className="text-[#F59E0B] font-semibold">MEDIUM</span>
                  <span>{stats.medium_findings}</span>
                </div>
                <div className="h-2 w-full bg-[#1E293B] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#F59E0B]"
                    style={{ width: `${stats.total_findings ? (stats.medium_findings / stats.total_findings) * 100 : 0}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono text-[#CBD5E1] mb-1">
                  <span className="text-[#3B82F6] font-semibold">LOW / INFO</span>
                  <span>{stats.low_findings + stats.informational_findings}</span>
                </div>
                <div className="h-2 w-full bg-[#1E293B] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#3B82F6]"
                    style={{
                      width: `${
                        stats.total_findings
                          ? ((stats.low_findings + stats.informational_findings) / stats.total_findings) * 100
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Top Vulnerability Types */}
          <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] p-5 space-y-4">
            <h3 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
              <Bug className="h-4 w-4 text-[#3B82F6]" />
              Kategori Kerentanan Terbanyak
            </h3>
            {stats.top_vulnerabilities.length === 0 ? (
              <p className="text-xs text-[#64748B] italic">Belum ada temuan kerentanan tercatat.</p>
            ) : (
              <div className="space-y-2">
                {stats.top_vulnerabilities.slice(0, 5).map((v) => (
                  <div key={v.type} className="flex items-center justify-between text-xs p-2 rounded bg-[#1E293B]/40">
                    <span className="font-mono text-[#CBD5E1] truncate max-w-[180px]">{v.type}</span>
                    <span className="px-2 py-0.5 rounded font-mono font-bold bg-[#3B82F6]/20 text-[#60A5FA]">
                      {v.count}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Recent Assessments Table */}
        <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0F172A] overflow-hidden">
          <div className="p-4 border-b border-[rgba(255,255,255,0.06)] flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
              <Clock className="h-4 w-4 text-[#22C55E]" />
              Asesmen Terakhir
            </h3>
            <Link
              href="/web-security/assessments"
              className="text-xs text-[#22C55E] hover:underline flex items-center gap-1 font-medium"
            >
              Lihat Seluruh Asesmen <ExternalLink className="h-3 w-3" />
            </Link>
          </div>

          {recentAssessments.length === 0 ? (
            <div className="p-8 text-center text-xs text-[#64748B]">
              Belum ada riwayat asesmen web. Silakan jalankan asesmen dari menu Target atau Asesmen Web.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#1E293B]/50 font-mono text-[#94A3B8] border-b border-[rgba(255,255,255,0.06)]">
                  <tr>
                    <th className="p-3">ID</th>
                    <th className="p-3">Target</th>
                    <th className="p-3">Profil</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Temuan</th>
                    <th className="p-3">Durasi</th>
                    <th className="p-3">Waktu</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(255,255,255,0.05)] text-[#CBD5E1]">
                  {recentAssessments.map((a) => {
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
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
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
                        <td className="p-3 font-mono">
                          <span className="font-bold text-[#F8FAFC]">{a.total_findings}</span>
                          {(a.critical_count > 0 || a.high_count > 0) && (
                            <span className="ml-1.5 px-1.5 py-0.2 rounded text-[10px] bg-[#EF4444]/20 text-[#EF4444]">
                              {a.critical_count + a.high_count} Sev
                            </span>
                          )}
                        </td>
                        <td className="p-3 font-mono text-[#94A3B8]">{a.duration_ms ? `${a.duration_ms} ms` : '-'}</td>
                        <td className="p-3 font-mono text-[#64748B]">
                          {new Date(a.created_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}
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

