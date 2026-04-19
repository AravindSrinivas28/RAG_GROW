import type { NextConfig } from "next";

/** Upstream FastAPI (e.g. Render). Used to rewrite /api/m1/* → backend (same-origin in browser). */
function upstreamApiBase(): string | null {
  const raw =
    process.env.M1_RAG_UPSTREAM_API_URL?.trim() ||
    process.env.NEXT_PUBLIC_M1_RAG_API_URL?.trim();
  if (!raw) return null;
  return raw.replace(/\/+$/, "");
}

const nextConfig: NextConfig = {
  async rewrites() {
    const upstream = upstreamApiBase();
    if (!upstream) return [];
    return [
      {
        source: "/api/m1/:path*",
        destination: `${upstream}/:path*`,
      },
    ];
  },
};

export default nextConfig;
