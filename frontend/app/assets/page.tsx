import { Suspense } from 'react';
import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import AssetsClient from '@/components/assets/AssetsClient';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { getAssets, getScanScopes } from '@/lib/api';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Manajemen Aset',
};

export const dynamic = 'force-dynamic';

export default async function AssetsPage() {
  const [assetsResult, scopesResult] = await Promise.allSettled([
    getAssets(),
    getScanScopes(),
  ]);

  const assets = assetsResult.status === 'fulfilled' ? assetsResult.value : [];
  const scopes = scopesResult.status === 'fulfilled' ? scopesResult.value : [];

  return (
    <AppShell>
      <Header title="Manajemen Aset Teritorial" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        <Suspense
          fallback={
            <div className="flex h-64 items-center justify-center">
              <LoadingSpinner label="Memuat inventaris aset..." />
            </div>
          }
        >
          <AssetsClient initialAssets={assets} scopes={scopes} />
        </Suspense>
      </main>
    </AppShell>
  );
}

