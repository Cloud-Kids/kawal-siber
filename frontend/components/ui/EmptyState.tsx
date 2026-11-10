import type { LucideProps } from 'lucide-react';
import { AlertCircle } from 'lucide-react';
import type { ComponentType, ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ComponentType<LucideProps>;
  title: string;
  description: string;
  action?: ReactNode;
}

export default function EmptyState({
  icon: Icon = AlertCircle,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[#1E293B] border border-[rgba(255,255,255,0.08)]">
        <Icon className="h-8 w-8 text-[#475569]" strokeWidth={1.5} />
      </div>
      <h3 className="mb-1.5 text-sm font-semibold text-[#94A3B8]">{title}</h3>
      <p className="max-w-xs text-xs text-[#475569] leading-relaxed">
        {description}
      </p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
