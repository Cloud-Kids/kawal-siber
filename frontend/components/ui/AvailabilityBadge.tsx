import type { AvailabilityStatus } from '@/types';
import { availabilityStatusLabel, cn } from '@/lib/utils';

interface AvailabilityBadgeProps {
  status: AvailabilityStatus;
  className?: string;
}

const statusConfig: Record<
  AvailabilityStatus,
  { bg: string; text: string; border: string; dot: string; pulse?: boolean }
> = {
  UNKNOWN: {
    bg: 'bg-slate-500/10',
    text: 'text-slate-400',
    border: 'border-slate-500/20',
    dot: 'bg-slate-400',
  },
  UP: {
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    border: 'border-emerald-500/20',
    dot: 'bg-emerald-400',
    pulse: true,
  },
  DOWN: {
    bg: 'bg-rose-500/10',
    text: 'text-rose-400',
    border: 'border-rose-500/20',
    dot: 'bg-rose-400',
  },
};

export default function AvailabilityBadge({
  status,
  className,
}: AvailabilityBadgeProps) {
  const config = statusConfig[status] ?? statusConfig.UNKNOWN;

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
      {availabilityStatusLabel(status)}
    </span>
  );
}

