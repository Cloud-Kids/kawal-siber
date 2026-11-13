import type { AssetStatus, AttackType, AvailabilityStatus, ScanJobStatus, Severity } from '@/types';

/**
 * Parse an API timestamp into a Date.
 * Backend stores UTC; naive ISO strings (no Z / offset) are treated as UTC
 * explicitly so the browser never interprets them as local time.
 */
export function parseApiTimestamp(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  // Has explicit zone? (Z or ±hh:mm at end) → parse as-is.
  if (/[zZ]$|[+-]\d{2}:?\d{2}$/.test(iso.trim())) {
    const d = new Date(iso);
    return isNaN(d.getTime()) ? null : d;
  }
  // Naive ISO datetime → treat as UTC.
  const d = new Date(iso.trim().replace(' ', 'T') + 'Z');
  return isNaN(d.getTime()) ? null : d;
}

/** Format a date string to a locale-aware human-readable string (Indonesian locale, WIB). */
export function formatDateTime(iso: string | null): string {
  if (!iso) return '—';
  try {
    const d = parseApiTimestamp(iso);
    if (!d) return '—';
    return new Intl.DateTimeFormat('id-ID', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'Asia/Jakarta',
    }).format(d);
  } catch {
    return iso;
  }
}

/** Format milliseconds response time to a display string. */
export function formatResponseTime(ms: number | null): string {
  if (ms === null) return '—';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

/** Map an AssetStatus to a human-readable Indonesian label. */
export function assetStatusLabel(status: AssetStatus): string {
  const map: Record<AssetStatus, string> = {
    UNKNOWN: 'Tidak Diketahui',
    SAFE: 'Aman',
    WARNING: 'Peringatan',
    UNDER_ATTACK: 'Diserang',
    DOWN: 'Tidak Aktif',
  };
  return map[status] ?? status;
}

/** Map an AvailabilityStatus to a human-readable Indonesian label. */
export function availabilityStatusLabel(status: AvailabilityStatus): string {
  const map: Record<AvailabilityStatus, string> = {
    UNKNOWN: 'Belum Diperiksa',
    UP: 'Online',
    DOWN: 'Offline',
  };
  return map[status] ?? status;
}

/** Map a ScanJobStatus to a human-readable Indonesian label. */
export function scanJobStatusLabel(status: ScanJobStatus): string {
  const map: Record<ScanJobStatus, string> = {
    PENDING: 'Menunggu',
    RUNNING: 'Memindai',
    COMPLETED: 'Selesai',
    FAILED: 'Gagal',
    CANCELLED: 'Dibatalkan',
  };
  return map[status] ?? status;
}

/** Map a Severity to a human-readable label. */
export function severityLabel(severity: Severity): string {
  const map: Record<Severity, string> = {
    CRITICAL: 'Kritis',
    HIGH: 'Tinggi',
    MEDIUM: 'Sedang',
    LOW: 'Rendah',
    PENDING: 'Tertunda',
  };
  return map[severity] ?? severity;
}

/** Map an AttackType to a display label. */
export function attackTypeLabel(type: AttackType): string {
  const map: Record<AttackType, string> = {
    BRUTE_FORCE: 'Brute Force',
    SQL_INJECTION: 'SQL Injection',
    XSS: 'Cross-Site Scripting',
    PORT_SCAN: 'Port Scan',
    ANOMALY_TRAFFIC: 'Anomali Trafik',
  };
  return map[type] ?? type;
}

/** Combine class names, filtering out falsy values. */
export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}

/** Clamp a number between min and max. */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
