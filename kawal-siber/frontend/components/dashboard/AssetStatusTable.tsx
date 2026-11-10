import Link from 'next/link';
import type { Asset } from '@/types';
import StatusBadge from '@/components/ui/StatusBadge';
import AvailabilityBadge from '@/components/ui/AvailabilityBadge';
import EmptyState from '@/components/ui/EmptyState';
import { Server, ArrowUpRight } from 'lucide-react';
import { formatDateTime, formatResponseTime } from '@/lib/utils';

interface AssetStatusTableProps {
  assets: Asset[];
}

export default function AssetStatusTable({ assets }: AssetStatusTableProps) {
  return (
    <div className="glass-card rounded-xl border border-[rgba(255,255,255,0.08)]">
      {/* Card header */}
      <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.06)] px-5 py-4">
        <div className="flex items-center gap-2.5">
          <Server className="h-4 w-4 text-[#475569]" strokeWidth={1.75} />
          <h2 className="text-sm font-semibold text-[#CBD5E1]">Status Aset Teritorial</h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-full bg-[#334155]/60 px-2.5 py-0.5 text-xs font-mono text-[#94A3B8]">
            {assets.length} aset
          </span>
          <Link
            href="/assets"
            className="inline-flex items-center gap-1 text-xs text-[#22C55E] hover:underline font-medium"
          >
            Semua Aset <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>
      </div>

      {assets.length === 0 ? (
        <EmptyState
          icon={Server}
          title="Belum ada aset terdaftar"
          description="Tambahkan aset untuk mulai memantau status dan keamanannya."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.05)]">
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#475569]">
                  Nama Aset
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#475569]">
                  IP : Port
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#475569]">
                  Ketersediaan
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#475569]">
                  Status Siber
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#475569]">
                  Resp. Time
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#475569]">
                  Terakhir Dipindai
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255,255,255,0.04)]">
              {assets.map((asset) => (
                <tr
                  key={asset.id}
                  className="transition-colors hover:bg-[rgba(255,255,255,0.02)]"
                >
                  <td className="px-5 py-3.5 font-medium text-[#CBD5E1]">
                    <Link
                      href={`/assets/${asset.id}`}
                      className="hover:text-[#22C55E] transition-colors"
                    >
                      {asset.name}
                    </Link>
                  </td>
                  <td className="px-5 py-3.5 font-mono text-xs text-[#94A3B8]">
                    {asset.target_ip}:{asset.port}
                  </td>
                  <td className="px-5 py-3.5">
                    <AvailabilityBadge status={asset.availability_status} />
                  </td>
                  <td className="px-5 py-3.5">
                    <StatusBadge status={asset.status} />
                  </td>
                  <td className="px-5 py-3.5 font-mono text-xs text-[#94A3B8]">
                    {formatResponseTime(asset.response_time_ms)}
                  </td>
                  <td className="px-5 py-3.5 text-xs text-[#64748B]">
                    {formatDateTime(asset.last_scanned)}
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
