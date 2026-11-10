import type { NextConfig } from 'next';

const rawApiUrl = process.env.API_INTERNAL_URL ?? 'http://127.0.0.1:8000';
const internalOrigin = rawApiUrl.replace(/\/api\/v1\/?$/, '').replace(/\/+$/, '');

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${internalOrigin}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
