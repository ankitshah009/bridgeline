import type { NextConfig } from "next";

const API = process.env.HOMEBASE_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  // Local dev proxies /api to FastAPI. On Vercel, vercel.json routes /api to the backend service
  // before requests reach Next.js, so no proxy is needed there.
  async rewrites() {
    if (process.env.VERCEL) return [];
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};

export default nextConfig;
