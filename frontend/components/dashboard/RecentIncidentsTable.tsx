import type { Incident } from '@/types';
import SeverityBadge from '@/components/ui/SeverityBadge';
import EmptyState from '@/components/ui/EmptyState';
import { AlertTriangle, ShieldCheck, ShieldAlert } from 'lucide-react';
import { formatDateTime, attackTypeLabel } from '@/lib/utils';

interface RecentIncidentsTableProps {
  incidents: Incident[];
}

export default function RecentIncidentsTable({
  incidents,
}: RecentIncidentsTableProps) {
  return (
    <div className="glass-card rounded-xl border border-[rgba(255,255,255,0.08)]">
      {/* Card header */}
      <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.06)] px-5 py-4">
        <div className="flex items-center gap-2.5">
          <AlertTriangle
            className="h-4 w-4 text-[#F59E0B]"
            strokeWidth={1.75}
          />
          <h2 className="text-sm font-semibold text-[#CBD5E1]">
            Insiden Terbaru
          </h2>
        </div>
        <span className="rounded-full bg-[#334155]/60 px-2.5 py-0.5 text-xs font-mono text-[#94A3B8]">
          {incidents.length} insiden
        </span>
      </div>

      {incidents.length === 0 ? (
        <EmptyState
          icon={AlertTriangle}
          title="Tidak ada insiden tercatat"
          description="Tidak ada insiden keamanan yang terdeteksi saat ini. Sistem berjalan normal."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.05)]">
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#475569]">
                  Waktu
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#475569]">
                  IP Sumber
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#475569]">
                  Jenis Serangan
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#475569]">
                  Tingkat
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#475569]">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255,255,255,0.04)]">
              {incidents.map((incident) => (
                <tr
                  key={incident.id}
                  className="transition-colors hover:bg-[rgba(255,255,255,0.02)]"
                >
                  <td className="px-5 py-3.5 font-mono text-xs text-[#94A3B8] whitespace-nowrap">
                    {formatDateTime(incident.timestamp)}
                  </td>
                  <td className="px-5 py-3.5 font-mono text-xs text-[#94A3B8]">
                    {incident.source_ip}
                  </td>
                  <td className="px-5 py-3.5 text-[#CBD5E1]">
                    {attackTypeLabel(incident.attack_type)}
                  </td>
                  <td className="px-5 py-3.5">
                    <SeverityBadge severity={incident.severity} />
                  </td>
                  <td className="px-5 py-3.5">
                    {incident.is_mitigated ? (
                      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[#22C55E]">
                        <ShieldCheck className="h-3.5 w-3.5" strokeWidth={2} />
                        Dimitigasi
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[#EF4444]">
                        <ShieldAlert className="h-3.5 w-3.5" strokeWidth={2} />
                        Aktif
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
