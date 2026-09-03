import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // --- Proxy API calls to the FastAPI backend ---
  // Set API_URL env var to point to a remote backend, defaults to localhost
  async rewrites() {
    const apiUrl = process.env.API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
