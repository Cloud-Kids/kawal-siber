import { Suspense } from 'react';
import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import SummaryCards from '@/components/dashboard/SummaryCards';
import AssetStatusTable from '@/components/dashboard/AssetStatusTable';
import RecentIncidentsTable from '@/components/dashboard/RecentIncidentsTable';
import SecurityActivityFeed from '@/components/dashboard/SecurityActivityFeed';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { getAssets, getIncidents } from '@/lib/api';
import type { Asset, DashboardStats, Incident } from '@/types';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Dashboard',
};

export const dynamic = 'force-dynamic';

/** Compute DashboardStats from already-fetched data — no extra API call */
function computeStats(
  assets: Asset[],
  allIncidents: Incident[],
  totalIncidents: number,
): DashboardStats {
  return {
    totalAssets: assets.length,
    safeAssets: assets.filter((a) => a.status === 'SAFE').length,
    assetsUnderAttack: assets.filter((a) => a.status === 'UNDER_ATTACK').length,
    assetsDown: assets.filter((a) => a.status === 'DOWN').length,
    totalIncidents,
    criticalIncidents: allIncidents.filter((i) => i.severity === 'CRITICAL')
      .length,
    unresolvedIncidents: allIncidents.filter((i) => !i.is_mitigated).length,
  };
}

/**
 * Main dashboard Server Component.
 * Fetches data in parallel; gracefully degrades on API errors.
 */
export default async function DashboardPage() {
  /* Parallel fetches — errors are caught and replaced with empty defaults */
  const [assetsResult, incidentsResult] = await Promise.allSettled([
    getAssets(),
    getIncidents({ page_size: 10, page: 1 }),
  ]);

  const assets: Asset[] =
    assetsResult.status === 'fulfilled' ? assetsResult.value : [];

  const paginatedIncidents =
    incidentsResult.status === 'fulfilled'
      ? incidentsResult.value
      : { items: [], total: 0, page: 1, page_size: 10 };

  const recentIncidents: Incident[] = paginatedIncidents.items;

  /* Log fetch failures server-side for observability */
  if (assetsResult.status === 'rejected') {
    console.error('[Dashboard] Failed to fetch assets:', assetsResult.reason);
  }
  if (incidentsResult.status === 'rejected') {
    console.error(
      '[Dashboard] Failed to fetch incidents:',
      incidentsResult.reason,
    );
  }

  const stats = computeStats(
    assets,
    recentIncidents,
    paginatedIncidents.total,
  );

  return (
    <AppShell>
      <Header title="Dashboard Pemantauan" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Summary KPI Cards */}
        <Suspense
          fallback={
            <div className="flex h-28 items-center justify-center">
              <LoadingSpinner size="sm" label="Memuat statistik..." />
            </div>
          }
        >
          <SummaryCards stats={stats} />
        </Suspense>

        {/* Main content grid */}
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          {/* Asset table — takes 2/3 width on xl */}
          <div className="xl:col-span-2">
            <Suspense
              fallback={
                <div className="glass-card flex h-48 items-center justify-center rounded-xl border border-[rgba(255,255,255,0.08)]">
                  <LoadingSpinner label="Memuat data aset..." />
                </div>
              }
            >
              <AssetStatusTable assets={assets} />
            </Suspense>
          </div>

          {/* Activity feed — takes 1/3 width on xl */}
          <div>
            <Suspense
              fallback={
                <div className="glass-card flex h-48 items-center justify-center rounded-xl border border-[rgba(255,255,255,0.08)]">
                  <LoadingSpinner label="Memuat aktivitas..." />
                </div>
              }
            >
              <SecurityActivityFeed incidents={recentIncidents} />
            </Suspense>
          </div>
        </div>

        {/* Recent incidents full-width */}
        <Suspense
          fallback={
            <div className="glass-card flex h-48 items-center justify-center rounded-xl border border-[rgba(255,255,255,0.08)]">
              <LoadingSpinner label="Memuat insiden..." />
            </div>
          }
        >
          <RecentIncidentsTable incidents={recentIncidents} />
        </Suspense>
      </main>
    </AppShell>
  );
}
