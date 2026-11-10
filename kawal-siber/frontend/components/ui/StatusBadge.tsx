import type { AssetStatus } from '@/types';
import { assetStatusLabel } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  status: AssetStatus;
  className?: string;
}

const statusConfig: Record<
  AssetStatus,
  { bg: string; text: string; border: string; pulse?: boolean }
> = {
  UNKNOWN: {
    bg: 'bg-[#64748B]/20',
    text: 'text-[#94A3B8]',
    border: 'border-[#64748B]/40',
  },
  SAFE: {
    bg: 'bg-[#22C55E]/20',
    text: 'text-[#22C55E]',
    border: 'border-[#22C55E]/40',
  },
  WARNING: {
    bg: 'bg-[#F59E0B]/20',
    text: 'text-[#F59E0B]',
    border: 'border-[#F59E0B]/40',
  },
  UNDER_ATTACK: {
    bg: 'bg-[#EF4444]/20',
    text: 'text-[#EF4444]',
    border: 'border-[#EF4444]/40',
    pulse: true,
  },
  DOWN: {
    bg: 'bg-[#6366F1]/20',
    text: 'text-[#6366F1]',
    border: 'border-[#6366F1]/40',
  },
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
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
          config.text.replace('text-', 'bg-'),
          config.pulse && 'animate-pulse',
        )}
      />
      {assetStatusLabel(status)}
    </span>
  );
}
