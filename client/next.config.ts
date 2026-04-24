import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  basePath: process.env.NEXT_PUBLIC_BASE_PATH !== undefined ? process.env.NEXT_PUBLIC_BASE_PATH : "/annotator",
  trailingSlash: true,
  allowedDevOrigins: ["ncshpcgpu01", "ncshpc400", "ncshpc400.fda.gov", "localhost"],
  async rewrites() {
    return [
      {
        source: '/annotator_api/:path*',
        destination: `http://${process.env.BACKEND_HOST || 'localhost'}:8862/:path*`,
      },
    ];
  },
};

export default nextConfig;