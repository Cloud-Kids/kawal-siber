import { Suspense } from 'react';
import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import ScansMonitoringClient from '@/components/monitoring/ScansMonitoringClient';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { getAssets, getScans } from '@/lib/api';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Pemantauan Pemindaian Jaringan',
};

export const dynamic = 'force-dynamic';

export default async function ScansMonitoringPage() {
  const [scansResult, assetsResult] = await Promise.allSettled([
    getScans({ limit: 100 }),
    getAssets(),
  ]);

  const jobs = scansResult.status === 'fulfilled' ? scansResult.value : [];
  const assets = assetsResult.status === 'fulfilled' ? assetsResult.value : [];

  return (
    <AppShell>
      <Header title="Pemantauan Pemindaian Jaringan" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        <Suspense
          fallback={
            <div className="flex h-64 items-center justify-center">
              <LoadingSpinner label="Memuat antrean pemindaian..." />
            </div>
          }
        >
          <ScansMonitoringClient initialJobs={jobs} assets={assets} />
        </Suspense>
      </main>
    </AppShell>
  );
}

