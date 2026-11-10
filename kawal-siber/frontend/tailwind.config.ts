import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: [
    './app/**/*.{ts,tsx,mdx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
    './types/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Base palette
        background: '#0F172A',
        foreground: '#F8FAFC',
        primary: {
          DEFAULT: '#1E293B',
          foreground: '#F8FAFC',
        },
        secondary: {
          DEFAULT: '#334155',
          foreground: '#CBD5E1',
        },
        accent: {
          DEFAULT: '#22C55E',
          foreground: '#0F172A',
        },
        card: {
          DEFAULT: '#1B2336',
          foreground: '#F8FAFC',
        },
        muted: {
          DEFAULT: '#272F42',
          foreground: '#94A3B8',
        },
        border: '#475569',
        destructive: {
          DEFAULT: '#EF4444',
          foreground: '#F8FAFC',
        },

        // Cybersecurity semantic tokens
        status: {
          unknown: '#64748B',
          safe: '#22C55E',
          warning: '#F59E0B',
          'under-attack': '#EF4444',
          down: '#6366F1',
        },
        severity: {
          critical: '#EF4444',
          high: '#F97316',
          medium: '#F59E0B',
          low: '#22C55E',
          pending: '#64748B',
        },
      },
      fontFamily: {
        sans: ['var(--font-fira-sans)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['var(--font-fira-code)', 'ui-monospace', 'Consolas', 'monospace'],
      },
      spacing: {
        '18': '4.5rem',
        '60': '15rem',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glow-green': '0 0 16px rgba(34, 197, 94, 0.2)',
        'glow-red': '0 0 16px rgba(239, 68, 68, 0.2)',
        'glow-amber': '0 0 16px rgba(245, 158, 11, 0.2)',
      },
    },
  },
  plugins: [],
};

export default config;
