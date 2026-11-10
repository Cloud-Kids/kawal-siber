import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

const sizeMap = {
  sm: 'h-4 w-4 border-2',
  md: 'h-8 w-8 border-2',
  lg: 'h-12 w-12 border-[3px]',
};

export default function LoadingSpinner({
  size = 'md',
  className,
  label = 'Memuat...',
}: LoadingSpinnerProps) {
  return (
    <div
      className={cn('flex flex-col items-center justify-center gap-3', className)}
      role="status"
      aria-label={label}
    >
      <span
        className={cn(
          'animate-spin rounded-full border-[#334155] border-t-[#22C55E]',
          sizeMap[size],
        )}
      />
      <span className="text-xs text-[#475569] font-mono">{label}</span>
    </div>
  );
}
