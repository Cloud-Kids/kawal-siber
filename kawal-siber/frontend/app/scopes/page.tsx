import { Suspense } from 'react';
import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import ScopesClient from '@/components/scopes/ScopesClient';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { getScanScopes } from '@/lib/api';
import type { ScanScope } from '@/types';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Scope Otorisasi Pemindaian',
};

export const dynamic = 'force-dynamic';

export default async function ScopesPage() {
  let scopes: ScanScope[] = [];
  try {
    scopes = await getScanScopes();
  } catch (err) {
    console.error('Failed to fetch scan scopes:', err);
    scopes = [];
  }

  return (
    <AppShell>
      <Header title="Scope Otorisasi Pemindaian" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        <Suspense
          fallback={
            <div className="flex h-64 items-center justify-center">
              <LoadingSpinner label="Memuat scope otorisasi..." />
            </div>
          }
        >
          <ScopesClient initialScopes={scopes} />
        </Suspense>
      </main>
    </AppShell>
  );
}
