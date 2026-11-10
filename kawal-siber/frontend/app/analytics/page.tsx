import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import {
  getAssets,
  getIncidents,
  getMonitoringStatistics,
  getWebSecurityStatistics,
  getIncidentIntelligenceOverview,
  getReportStatistics,
} from '@/lib/api';
import AnalyticsClient from '@/components/analytics/AnalyticsClient';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Analitik Keamanan Terpadu — KAWAL SIBER',
  description: 'Integrated Security Analytics & Platform Telemetry Dashboard',
};

export const dynamic = 'force-dynamic';

export default async function AnalyticsPage() {
  const [
    assetsRes,
    incidentsRes,
    monitoringStatsRes,
    webStatsRes,
    intelOverviewRes,
    reportStatsRes,
  ] = await Promise.allSettled([
    getAssets(),
    getIncidents({ page_size: 1000 }),
    getMonitoringStatistics(),
    getWebSecurityStatistics(),
    getIncidentIntelligenceOverview(),
    getReportStatistics(),
  ]);

  const assets = assetsRes.status === 'fulfilled' ? assetsRes.value : [];
  const incidents = incidentsRes.status === 'fulfilled' ? incidentsRes.value.items : [];
  const monitoringStats =
    monitoringStatsRes.status === 'fulfilled' ? monitoringStatsRes.value : null;
  const webStats = webStatsRes.status === 'fulfilled' ? webStatsRes.value : null;
  const intelOverview =
    intelOverviewRes.status === 'fulfilled' ? intelOverviewRes.value : null;
  const reportStats =
    reportStatsRes.status === 'fulfilled' ? reportStatsRes.value : null;

  return (
    <AppShell>
      <Header title="Analitik Keamanan & Intelijen Pertahanan Siber Terintegrasi" />
      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        <AnalyticsClient
          assets={assets}
          incidents={incidents}
          monitoringStats={monitoringStats}
          webStats={webStats}
          intelOverview={intelOverview}
          reportStats={reportStats}
        />
      </main>
    </AppShell>
  );
}

