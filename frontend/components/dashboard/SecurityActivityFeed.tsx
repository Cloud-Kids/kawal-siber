import type { Incident, AttackType } from '@/types';
import EmptyState from '@/components/ui/EmptyState';
import {
  Activity,
  KeyRound,
  Database,
  Code2,
  Radar,
  BarChart3,
} from 'lucide-react';
import { formatDateTime, attackTypeLabel } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface SecurityActivityFeedProps {
  incidents: Incident[];
}

const attackTypeIconMap: Record<
  AttackType,
  React.ComponentType<{ className?: string; strokeWidth?: number }>
> = {
  BRUTE_FORCE: KeyRound,
  SQL_INJECTION: Database,
  XSS: Code2,
  PORT_SCAN: Radar,
  ANOMALY_TRAFFIC: BarChart3,
};

const severityColorMap: Record<string, string> = {
  CRITICAL: 'border-[#EF4444] bg-[#EF4444]/15 text-[#EF4444]',
  HIGH: 'border-[#F97316] bg-[#F97316]/15 text-[#F97316]',
  MEDIUM: 'border-[#F59E0B] bg-[#F59E0B]/15 text-[#F59E0B]',
  LOW: 'border-[#22C55E] bg-[#22C55E]/15 text-[#22C55E]',
  PENDING: 'border-[#64748B] bg-[#64748B]/15 text-[#64748B]',
};

const severityLineMap: Record<string, string> = {
  CRITICAL: 'bg-[#EF4444]',
  HIGH: 'bg-[#F97316]',
  MEDIUM: 'bg-[#F59E0B]',
  LOW: 'bg-[#22C55E]',
  PENDING: 'bg-[#64748B]',
};

export default function SecurityActivityFeed({
  incidents,
}: SecurityActivityFeedProps) {
  return (
    <div className="glass-card rounded-xl border border-[rgba(255,255,255,0.08)]">
      {/* Card header */}
      <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.06)] px-5 py-4">
        <div className="flex items-center gap-2.5">
          <Activity className="h-4 w-4 text-[#22C55E]" strokeWidth={1.75} />
          <h2 className="text-sm font-semibold text-[#CBD5E1]">
            Aktivitas Keamanan
          </h2>
        </div>
      </div>

      {incidents.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="Belum ada aktivitas tercatat"
          description="Belum ada aktivitas keamanan tercatat. Sistem siap memantau."
        />
      ) : (
        <div className="px-5 py-4">
          <div className="relative space-y-0">
            {incidents.map((incident, idx) => {
              const Icon =
                attackTypeIconMap[incident.attack_type] ?? Activity;
              const colorClasses =
                severityColorMap[incident.severity] ??
                severityColorMap.PENDING;
              const lineColor =
                severityLineMap[incident.severity] ??
                severityLineMap.PENDING;
              const isLast = idx === incidents.length - 1;

              return (
                <div key={incident.id} className="relative flex gap-4">
                  {/* Timeline line */}
                  {!isLast && (
                    <span
                      className={cn(
                        'absolute left-[17px] top-9 bottom-0 w-px opacity-20',
                        lineColor,
                      )}
                    />
                  )}

                  {/* Icon bubble */}
                  <div className="relative z-10 mt-1 shrink-0">
                    <div
                      className={cn(
                        'flex h-9 w-9 items-center justify-center rounded-lg border',
                        colorClasses,
                      )}
                    >
                      <Icon className="h-4 w-4" strokeWidth={1.75} />
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex-1 pb-5">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <span className="text-sm font-semibold text-[#CBD5E1]">
                        {attackTypeLabel(incident.attack_type)}
                      </span>
                      <span className="font-mono text-xs text-[#475569]">
                        dari {incident.source_ip}
                      </span>
                    </div>
                    <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5">
                      <span className="font-mono text-xs text-[#475569]">
                        {formatDateTime(incident.timestamp)}
                      </span>
                      {incident.is_mitigated ? (
                        <span className="text-xs text-[#22C55E]">✓ Dimitigasi</span>
                      ) : (
                        <span className="text-xs text-[#EF4444]">⚠ Aktif</span>
                      )}
                    </div>
                    {incident.ai_analysis && (
                      <p className="mt-1.5 text-xs text-[#64748B] leading-relaxed line-clamp-2">
                        {incident.ai_analysis}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
