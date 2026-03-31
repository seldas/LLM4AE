import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  basePath: "/annotator",
  trailingSlash: true,
  allowedDevOrigins: ["ncshpcgpu01", "ncshpc400", "ncshpc400.fda.gov"]
};

export default nextConfig;