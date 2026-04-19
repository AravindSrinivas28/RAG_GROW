import type { NextConfig } from "next";

/**
 * Proxy to Render is implemented in `src/app/api/m1/[[...path]]/route.ts`
 * (Node runtime + maxDuration). Do not use rewrites here — Vercel’s external
 * rewrite proxy times out on long RAG/LLM requests and returns 502.
 */
const nextConfig: NextConfig = {};

export default nextConfig;
