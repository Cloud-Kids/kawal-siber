import type { Severity } from '@/types';
import { severityLabel } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface SeverityBadgeProps {
  severity: Severity;
  className?: string;
}

const severityConfig: Record<
  Severity,
  { bg: string; text: string; border: string }
> = {
  CRITICAL: {
    bg: 'bg-[#EF4444]/20',
    text: 'text-[#EF4444]',
    border: 'border-[#EF4444]/40',
  },
  HIGH: {
    bg: 'bg-[#F97316]/20',
    text: 'text-[#F97316]',
    border: 'border-[#F97316]/40',
  },
  MEDIUM: {
    bg: 'bg-[#F59E0B]/20',
    text: 'text-[#F59E0B]',
    border: 'border-[#F59E0B]/40',
  },
  LOW: {
    bg: 'bg-[#22C55E]/20',
    text: 'text-[#22C55E]',
    border: 'border-[#22C55E]/40',
  },
  PENDING: {
    bg: 'bg-[#64748B]/20',
    text: 'text-[#94A3B8]',
    border: 'border-[#64748B]/40',
  },
};

export default function SeverityBadge({
  severity,
  className,
}: SeverityBadgeProps) {
  const config = severityConfig[severity] ?? severityConfig.PENDING;

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold font-mono uppercase tracking-wide',
        config.bg,
        config.text,
        config.border,
        className,
      )}
    >
      {severityLabel(severity)}
    </span>
  );
}
