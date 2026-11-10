import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import { getReports, getReportStatistics } from '@/lib/api';
import type { PaginatedReports, ReportStatistics } from '@/types';
import ReportsClient from '@/components/reports/ReportsClient';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Pusat Laporan Keamanan — KAWAL SIBER',
  description: 'Automated Security Reporting & Audit Documentation',
};

export const dynamic = 'force-dynamic';

export default async function ReportsPage() {
  let reportsData: PaginatedReports = {
    items: [],
    total: 0,
    page: 1,
    page_size: 50,
  };

  let stats: ReportStatistics = {
    total_reports: 0,
    completed_reports: 0,
    failed_reports: 0,
    pending_reports: 0,
    by_type: {},
    by_format: {},
    latest_report: null,
  };

  try {
    const [rep, st] = await Promise.all([
      getReports({ page_size: 50 }).catch(() => reportsData),
      getReportStatistics().catch(() => stats),
    ]);
    reportsData = rep;
    stats = st;
  } catch (err) {
    console.error('Failed to load reports page data:', err);
  }

  return (
    <AppShell>
      <Header title="Pusat Pelaporan Keamanan Otomatis (Reporting Center)" />
      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        <ReportsClient initialReports={reportsData} initialStats={stats} />
      </main>
    </AppShell>
  );
}

