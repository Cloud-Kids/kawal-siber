import type { DashboardStats } from '@/types';
import { Server, CheckCircle, AlertTriangle, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SummaryCardsProps {
  stats: DashboardStats;
}

interface CardConfig {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  iconBg: string;
  iconColor: string;
  borderColor: string;
  valueColor: string;
  pulse?: boolean;
}

export default function SummaryCards({ stats }: SummaryCardsProps) {
  const cards: CardConfig[] = [
    {
      title: 'Total Aset',
      value: stats.totalAssets,
      icon: Server,
      iconBg: 'bg-[#334155]/60',
      iconColor: 'text-[#94A3B8]',
      borderColor: 'border-[rgba(255,255,255,0.08)]',
      valueColor: 'text-[#F8FAFC]',
    },
    {
      title: 'Aset Aman',
      value: stats.safeAssets,
      icon: CheckCircle,
      iconBg: 'bg-[#22C55E]/15',
      iconColor: 'text-[#22C55E]',
      borderColor: 'border-[#22C55E]/20',
      valueColor: 'text-[#22C55E]',
    },
    {
      title: 'Diserang',
      value: stats.assetsUnderAttack,
      icon: AlertTriangle,
      iconBg: 'bg-[#EF4444]/15',
      iconColor: 'text-[#EF4444]',
      borderColor: 'border-[#EF4444]/20',
      valueColor: 'text-[#EF4444]',
      pulse: stats.assetsUnderAttack > 0,
    },
    {
      title: 'Insiden Kritis',
      value: stats.criticalIncidents,
      icon: Zap,
      iconBg: 'bg-[#F97316]/15',
      iconColor: 'text-[#F97316]',
      borderColor: 'border-[#F97316]/20',
      valueColor: 'text-[#F97316]',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.title}
          className={cn(
            'glass-card relative overflow-hidden rounded-xl border p-5',
            card.borderColor,
          )}
        >
          {/* Subtle top gradient accent */}
          <div
            className={cn(
              'pointer-events-none absolute inset-x-0 top-0 h-px',
              card.iconColor.replace('text-', 'bg-').replace('[', '[opacity-40_'),
            )}
          />

          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-[#64748B] uppercase tracking-wider mb-3">
                {card.title}
              </p>
              <p
                className={cn(
                  'text-3xl font-bold font-mono tabular-nums leading-none',
                  card.valueColor,
                  card.pulse && 'animate-pulse',
                )}
              >
                {card.value}
              </p>
            </div>

            <div
              className={cn(
                'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
                card.iconBg,
              )}
            >
              <card.icon
                className={cn('h-5 w-5', card.iconColor)}
                strokeWidth={1.75}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
