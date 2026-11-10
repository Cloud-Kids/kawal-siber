'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Server,
  Crosshair,
  Radar,
  AlertTriangle,
  ShieldAlert,
  Radio,
  FileSearch,
  Shield,
  Globe,
  Bug,
  ListFilter,
  BrainCircuit,
  Siren,
  FileText,
  BarChart3,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Pusat Insiden', href: '/incidents', icon: Siren },
  { label: 'AI Intelligence', href: '/intelligence', icon: BrainCircuit },
  { label: 'Pusat Laporan', href: '/reports', icon: FileText },
  { label: 'Analitik Keamanan', href: '/analytics', icon: BarChart3 },
  { label: 'Manajemen Aset', href: '/assets', icon: Server },
  { label: 'Scope Otorisasi', href: '/scopes', icon: Crosshair },
  { label: 'Pemindaian Nmap', href: '/monitoring/scans', icon: Radar },
  { label: 'Monitoring Ancaman', href: '/monitoring', icon: Radio },
  { label: 'Peringatan Siber', href: '/monitoring/alerts', icon: ShieldAlert },
  { label: 'Event Telemetri', href: '/monitoring/events', icon: AlertTriangle },
  { label: 'Analisis PCAP', href: '/monitoring/pcap', icon: FileSearch },
  { label: 'Keamanan Web (Deep Eye)', href: '/web-security', icon: Globe },
  { label: 'Target Web', href: '/web-security/targets', icon: Crosshair },
  { label: 'Asesmen Web', href: '/web-security/assessments', icon: ListFilter },
  { label: 'Temuan Kerentanan', href: '/web-security/findings', icon: Bug },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-60 flex-col bg-[#0F172A] border-r border-[rgba(255,255,255,0.06)]">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-[rgba(255,255,255,0.06)]">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#22C55E]/15 border border-[#22C55E]/30">
          <Shield className="h-5 w-5 text-[#22C55E]" strokeWidth={2} />
        </div>
        <div>
          <span className="block text-sm font-bold tracking-widest text-[#F8FAFC] font-mono uppercase">
            KAWAL SIBER
          </span>
          <span className="block text-[10px] text-[#475569] font-mono">
            Sistem Pertahanan Teritorial
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname?.startsWith(item.href));
          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                'group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-150',
                isActive
                  ? 'bg-[#22C55E]/10 text-[#22C55E]'
                  : 'text-[#64748B] hover:bg-[#1E293B] hover:text-[#CBD5E1]',
              )}
            >
              {/* Active indicator */}
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-r bg-[#22C55E]" />
              )}
              <item.icon
                className={cn(
                  'h-4 w-4 shrink-0 transition-colors',
                  isActive ? 'text-[#22C55E]' : 'text-[#475569] group-hover:text-[#94A3B8]',
                )}
                strokeWidth={isActive ? 2 : 1.75}
              />
              <span className="font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-[rgba(255,255,255,0.06)]">
        <span className="block text-[10px] font-mono text-[#475569] text-center">
          v6.0.0 — FASE 6 (AUTOMATED REPORTING & PLATFORM INTEGRATION)
        </span>
      </div>
    </aside>
  );
}
