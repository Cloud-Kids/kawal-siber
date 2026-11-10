import { notFound } from 'next/navigation';
import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import AssetDetailClient from '@/components/assets/AssetDetailClient';
import { getAsset, getAssetScans, getScanResults, getScanScopes } from '@/lib/api';
import type { Metadata } from 'next';

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = 'force-dynamic';

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  return {
    title: `Detail Aset #${id}`,
  };
}

export default async function AssetDetailPage({ params }: PageProps) {
  const { id } = await params;
  const assetId = parseInt(id, 10);
  if (isNaN(assetId)) {
    notFound();
  }

  let asset;
  try {
    asset = await getAsset(assetId);
  } catch {
    notFound();
  }

  const [scansResult, scopesResult] = await Promise.allSettled([
    getAssetScans(assetId),
    getScanScopes(),
  ]);

  const scanHistory = scansResult.status === 'fulfilled' ? scansResult.value : [];
  const availableScopes = scopesResult.status === 'fulfilled' ? scopesResult.value : [];

  const matchedScope = asset.scope_id
    ? availableScopes.find((s) => s.id === asset.scope_id) || null
    : null;

  let latestResults: any[] = [];
  if (scanHistory.length > 0) {
    const latestJob = scanHistory[0];
    if (latestJob.status === 'COMPLETED') {
      try {
        latestResults = await getScanResults(latestJob.id);
      } catch {
        latestResults = [];
      }
    }
  }

  return (
    <AppShell>
      <Header title={`Aset: ${asset.name}`} />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        <AssetDetailClient
          asset={asset}
          scope={matchedScope}
          scanHistory={scanHistory}
          latestResults={latestResults}
          availableScopes={availableScopes}
        />
      </main>
    </AppShell>
  );
}
