import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        // Proxy /api/* to FastAPI EXCEPT /api/auth/* (NextAuth routes)
        source: "/api/:path((?!auth).*)",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};


export default nextConfig;
