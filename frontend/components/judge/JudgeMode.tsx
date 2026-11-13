'use client';

import { useEffect } from 'react';

export const JUDGE_MODE = process.env.NEXT_PUBLIC_JUDGE_MODE === 'true';

/** Persistent banner shown only in judge demo mode. */
export function JudgeBanner() {
  if (!JUDGE_MODE) return null;
  return (
    <div className="w-full bg-amber-500/15 border-b border-amber-500/40 px-4 py-1.5 text-center text-xs text-amber-300">
      <strong>PUBLIC JUDGE DEMONSTRATION — READ ONLY</strong>
      {' '}Sanitized demo data. Operational functions are disabled to protect the
      underlying security infrastructure.
    </div>
  );
}

/** Client-side guard: blocks all mutating API calls in judge mode.
 *  Backend enforcement (403) remains the authoritative layer. */
export function useJudgeGuard() {
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
