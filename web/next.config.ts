import type { NextConfig } from "next";

const apiInternal = process.env.API_INTERNAL_URL || "http://127.0.0.1:5000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiInternal}/api/v1/:path*`,
      },
      {
        source: "/uploads/:path*",
        destination: `${apiInternal}/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
