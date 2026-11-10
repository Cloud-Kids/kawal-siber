import type { ScanJobStatus } from '@/types';
import { scanJobStatusLabel, cn } from '@/lib/utils';

interface ScanJobStatusBadgeProps {
  status: ScanJobStatus;
  className?: string;
}

const statusConfig: Record<
  ScanJobStatus,
  { bg: string; text: string; border: string; dot: string; pulse?: boolean }
> = {
  PENDING: {
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    border: 'border-amber-500/20',
    dot: 'bg-amber-400',
    pulse: true,
  },
  RUNNING: {
    bg: 'bg-cyan-500/10',
    text: 'text-cyan-400',
    border: 'border-cyan-500/20',
    dot: 'bg-cyan-400',
    pulse: true,
  },
  COMPLETED: {
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    border: 'border-emerald-500/20',
    dot: 'bg-emerald-400',
  },
  FAILED: {
    bg: 'bg-rose-500/10',
    text: 'text-rose-400',
    border: 'border-rose-500/20',
    dot: 'bg-rose-400',
  },
  CANCELLED: {
    bg: 'bg-slate-500/10',
    text: 'text-slate-400',
    border: 'border-slate-500/20',
    dot: 'bg-slate-400',
  },
};

export default function ScanJobStatusBadge({
  status,
  className,
}: ScanJobStatusBadgeProps) {
  const config = statusConfig[status] ?? statusConfig.PENDING;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium font-mono',
        config.bg,
        config.text,
        config.border,
        className,
      )}
    >
      <span
        className={cn(
          'inline-block h-1.5 w-1.5 rounded-full',
          config.dot,
          config.pulse && 'animate-pulse',
        )}
      />
      {scanJobStatusLabel(status)}
    </span>
  );
}

