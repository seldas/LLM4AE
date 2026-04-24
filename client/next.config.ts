import type { NextConfig } from "next";

const rawBasePath = process.env.NEXT_PUBLIC_BASE_PATH !== undefined ? process.env.NEXT_PUBLIC_BASE_PATH : "/annotator";
const normalizedBasePath = rawBasePath === "" ? undefined : (rawBasePath.startsWith('/') ? rawBasePath : `/${rawBasePath}`).replace(/\/$/, '');

const nextConfig: NextConfig = {
  basePath: normalizedBasePath,
  trailingSlash: true,
  allowedDevOrigins: ["ncshpcgpu01", "ncshpc400", "ncshpc400.fda.gov", "localhost"],
  async rewrites() {
    const apiBase = normalizedBasePath || "";
    return [
      {
        source: `${apiBase}/annotator_api/:path*`,
        destination: `http://${process.env.BACKEND_HOST || 'localhost'}:8862/:path*`,
      },
    ];
  },
};

export default nextConfig;