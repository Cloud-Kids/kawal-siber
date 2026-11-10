'use client';

import type { ReactNode } from 'react';
import Sidebar from './Sidebar';

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-[#0F172A]">
      {/* Fixed sidebar */}
      <Sidebar />

      {/* Main content — offset by sidebar width */}
      <div className="flex flex-1 flex-col pl-60 min-w-0">
        {children}
      </div>
    </div>
  );
}
