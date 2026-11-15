'use client';

import { useEffect } from 'react';

const JUDGE_MODE_RAW = process.env.NEXT_PUBLIC_JUDGE_MODE ?? '';
export const JUDGE_MODE = JUDGE_MODE_RAW === 'true';
export const JUDGE_INTERACTIVE_MODE = JUDGE_MODE_RAW === 'interactive';
export const JUDGE_ENABLED = JUDGE_MODE || JUDGE_INTERACTIVE_MODE;

/** Persistent banner shown only in judge demo mode. */
export function JudgeBanner() {
  if (!JUDGE_ENABLED) return null;
  if (JUDGE_INTERACTIVE_MODE) {
    return (
      <div className="w-full bg-sky-500/15 border-b border-sky-500/40 px-4 py-1.5 text-center text-xs text-sky-300">
        <strong>PUBLIC JUDGE DEMONSTRATION — INTERACTIVE SANDBOX</strong>
        {' '}Isolated synthetic environment. All targets are demo-only; production
        systems are unreachable from this demo.
      </div>
    );
  }
  return (
    <div className="w-full bg-amber-500/15 border-b border-amber-500/40 px-4 py-1.5 text-center text-xs text-amber-300">
      <strong>PUBLIC JUDGE DEMONSTRATION — READ ONLY</strong>
      {' '}Sanitized demo data. Operational functions are disabled to protect the
      underlying security infrastructure.
    </div>
  );
}

/** Client-side guard: in read-only judge mode blocks all mutating API calls.
 *  In interactive mode writes are permitted (backend enforces the allowlist).
 *  Backend enforcement (403) remains the authoritative layer. */
export function JudgeGuard() {
  useJudgeGuard();
  return null;
}

function useJudgeGuard() {
  useEffect(() => {
    if (!JUDGE_MODE) return;
    document.body.classList.add('judge-mode');
    const origFetch = window.fetch;
    window.fetch = function (input: RequestInfo | URL, init?: RequestInit) {
      const method = (init?.method ?? (input instanceof Request ? input.method : 'GET')).toUpperCase();
      if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        return Promise.reject(new Error('Read-only judge demo: write operations are disabled.'));
      }
      return origFetch(input as RequestInfo, init);
    };
    return () => { window.fetch = origFetch; };
  }, []);
}
