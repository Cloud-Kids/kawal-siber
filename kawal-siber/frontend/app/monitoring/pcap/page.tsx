import AppShell from '@/components/layout/AppShell';
import Header from '@/components/layout/Header';
import { getPcapAnalyses } from '@/lib/api';
import type { PcapAnalysis } from '@/types';
import PcapClient from '@/components/monitoring/PcapClient';

export const dynamic = 'force-dynamic';

export default async function PcapPage() {
  let analyses: PcapAnalysis[] = [];
  try {
    analyses = await getPcapAnalyses({ limit: 50 });
  } catch {
    // fallback
  }

  return (
    <AppShell>
      <Header title="Analisis Berkas PCAP — Suricata Offline IDS" />

      <main className="flex-1 overflow-y-auto p-6 space-y-4">
        <div>
          <h2 className="text-base font-bold text-[#F8FAFC]">Pengolahan & Inspeksi Paket Jaringan (PCAP)</h2>
          <p className="text-xs text-[#94A3B8]">
            Analisis forensik lalu lintas jaringan lab terisolasi secara offline menggunakan mesin Suricata IDS.
          </p>
        </div>
        <PcapClient initialAnalyses={analyses} />
      </main>
    </AppShell>
  );
}
