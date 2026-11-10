import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import { getSecurityAlerts } from '@/lib/api';
import type { PaginatedSecurityEvents } from '@/types';
import AlertsClient from '@/components/monitoring/AlertsClient';

export const dynamic = 'force-dynamic';

export default async function AlertsPage() {
  let initialData: PaginatedSecurityEvents = { items: [], total: 0, page: 1, page_size: 50 };
  try {
    initialData = await getSecurityAlerts({ page: 1, page_size: 50 });
  } catch {
    // fallback
  }

  return (
    <AppShell>
      <Header title="Peringatan Keamanan Jaringan — Suricata Alerts" />

      <main className="flex-1 overflow-y-auto p-6 space-y-4">
        <div>
          <h2 className="text-base font-bold text-[#F8FAFC]">Peringatan Keamanan Aktif (Security Alerts)</h2>
          <p className="text-xs text-[#94A3B8]">
            Daftar event dengan klasifikasi alert yang terdeteksi oleh rule signature Suricata IDS.
          </p>
        </div>
        <AlertsClient initialData={initialData} />
      </main>
    </AppShell>
  );
}
