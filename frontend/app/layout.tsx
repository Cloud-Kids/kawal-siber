import type { Metadata } from 'next';
import { Fira_Code, Fira_Sans } from 'next/font/google';
import './globals.css';
import { JudgeBanner, JudgeGuard } from '@/components/judge/JudgeMode';

const firaSans = Fira_Sans({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-fira-sans',
  display: 'swap',
});

const firaCode = Fira_Code({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-fira-code',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'KAWAL SIBER',
    template: '%s | KAWAL SIBER',
  },
  description: 'Sistem Pemantauan Aset Teritorial — Keamanan Siber Terpadu',
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id" className={`${firaSans.variable} ${firaCode.variable} dark`}>
      <body className="bg-[#0F172A] text-[#F8FAFC] antialiased">
        <JudgeGuard />
        <JudgeBanner />
        {children}
      </body>
    </html>
  );
}
