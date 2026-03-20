import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ['ncshpcgpu01'],
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8862/api/:path*',
      },
    ];
  },
};

export default nextConfig;
