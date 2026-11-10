import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import { getSecurityEvents } from '@/lib/api';
import type { PaginatedSecurityEvents } from '@/types';
import EventsClient from '@/components/monitoring/EventsClient';

export const dynamic = 'force-dynamic';

export default async function EventsPage() {
  let initialData: PaginatedSecurityEvents = { items: [], total: 0, page: 1, page_size: 50 };
  try {
    initialData = await getSecurityEvents({ page: 1, page_size: 50 });
  } catch {
    // fallback
  }

  return (
    <AppShell>
      <Header title="Event Telemetri Jaringan — Suricata EVE JSON" />

      <main className="flex-1 overflow-y-auto p-6 space-y-4">
        <div>
          <h2 className="text-base font-bold text-[#F8FAFC]">Telemetri Alur & Protokol Jaringan</h2>
          <p className="text-xs text-[#94A3B8]">
            Aliran komprehensif event jaringan mentah yang diproses dari output terstruktur Suricata EVE JSON.
          </p>
        </div>
        <EventsClient initialData={initialData} />
      </main>
    </AppShell>
  );
}
