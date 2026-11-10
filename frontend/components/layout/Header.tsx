'use client';

import { useEffect, useState, useCallback } from 'react';
import { Activity } from 'lucide-react';
import type { HealthResponse } from '@/types';

/** Polls /api/v1/health every 30s and shows a colored dot with diagnostic info */
function HealthIndicator() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  const fetchHealth = useCallback(async () => {
    setIsChecking(true);
    try {
      const res = await fetch('/api/v1/health', { cache: 'no-store' });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status} ${res.statusText}`);
      }
      const data: HealthResponse = await res.json() as HealthResponse;
      setHealth(data);
      setErrorMsg(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Koneksi ditolak / backend tidak aktif';
      setErrorMsg(message);
      setHealth(null);
    } finally {
      setIsChecking(false);
    }
  }, []);

  useEffect(() => {
    void fetchHealth();
    const interval = setInterval(() => { void fetchHealth(); }, 30_000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  const isOnline = !errorMsg && (health?.status === 'healthy' || health?.status === 'ok');

  return (
    <button
      onClick={() => void fetchHealth()}
      title={
        isOnline
          ? `API Online (v${health?.version ?? '1.0.0'}) — Database: ${health?.database ?? 'connected'}. Klik untuk memeriksa ulang.`
          : `API Offline (${errorMsg ?? 'Layanan 127.0.0.1:8000 tidak merespons'}). Pastikan backend uvicorn berjalan. Klik untuk mencoba kembali.`
      }
      className="flex items-center gap-2 rounded-lg px-2 py-1 transition-colors hover:bg-[rgba(255,255,255,0.04)] text-left group"
      disabled={isChecking}
    >
      <span className="relative flex h-2 w-2">
        {isOnline ? (
          <span className="relative inline-flex h-2 w-2 rounded-full bg-[#22C55E] shadow-[0_0_6px_#22C55E]" />
        ) : (
          <>
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#EF4444] opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-[#EF4444] shadow-[0_0_6px_#EF4444]" />
          </>
        )}
      </span>
      <span className="hidden text-xs font-mono text-[#94A3B8] sm:block">
        {isChecking ? (
          <span className="text-[#64748B]">memeriksa...</span>
        ) : isOnline ? (
          <span className="text-[#22C55E]">API v{health?.version ?? '1.0.0'}</span>
        ) : (
          <span className="text-[#EF4444]">API offline</span>
        )}
      </span>
    </button>
  );
}

/** Clock that updates every second */
function RealtimeClock() {
  const [time, setTime] = useState<string>('');

  useEffect(() => {
    const update = () => {
      setTime(
        new Intl.DateTimeFormat('id-ID', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
          timeZone: 'Asia/Jakarta',
        }).format(new Date()),
      );
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <span className="font-mono text-sm text-[#94A3B8] tabular-nums">
      {time || '—'}
    </span>
  );
}

interface HeaderProps {
  title: string;
}

export default function Header({ title }: HeaderProps) {
  return (
    <header className="flex h-14 items-center justify-between border-b border-[rgba(255,255,255,0.06)] bg-[#0F172A]/80 px-6 backdrop-blur-md">
      {/* Page title */}
      <div className="flex items-center gap-3">
        <Activity className="h-4 w-4 text-[#22C55E]" strokeWidth={2} />
        <h1 className="text-sm font-semibold text-[#CBD5E1] tracking-wide">
          {title}
        </h1>
      </div>

      {/* Right side: clock + health */}
      <div className="flex items-center gap-5">
        <RealtimeClock />
        <div className="h-4 w-px bg-[#334155]" />
        <HealthIndicator />
      </div>
    </header>
  );
}
