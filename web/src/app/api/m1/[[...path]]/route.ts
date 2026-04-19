import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

/**
 * Same-origin proxy to Render (FastAPI). Replaces next.config rewrites so we can
 * set maxDuration — external rewrites time out quickly and return 502 on long
 * RAG + LLM requests.
 */
export const runtime = "nodejs";

/** Hobby may cap this (e.g. 10–60s); Pro allows up to 300s+ depending on plan. */
export const maxDuration = 300;

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);

function getUpstreamBase(): string | null {
  const raw =
    process.env.M1_RAG_UPSTREAM_API_URL?.trim() ||
    process.env.NEXT_PUBLIC_M1_RAG_API_URL?.trim();
  if (!raw) return null;
  return raw.replace(/\/+$/, "");
}

function buildUpstreamUrl(req: NextRequest, pathSegments: string[]): string {
  const base = getUpstreamBase()!;
  const rel = pathSegments.length ? pathSegments.join("/") : "";
  const url = new URL(rel, base.endsWith("/") ? base : `${base}/`);
  req.nextUrl.searchParams.forEach((v, k) => {
    url.searchParams.set(k, v);
  });
  return url.toString();
}

async function proxy(req: NextRequest, pathSegments: string[]) {
  const upstream = getUpstreamBase();
  if (!upstream) {
    return NextResponse.json(
      {
        detail:
          "Missing M1_RAG_UPSTREAM_API_URL or NEXT_PUBLIC_M1_RAG_API_URL on Vercel",
      },
      { status: 500 },
    );
  }

  const dest = buildUpstreamUrl(req, pathSegments);

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const init: RequestInit & { duplex?: string } = {
    method: req.method,
    headers,
    redirect: "manual",
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = req.body;
    init.duplex = "half";
  }

  const res = await fetch(dest, init);

  const out = new Headers(res.headers);
  out.delete("transfer-encoding");

  return new NextResponse(res.body, {
    status: res.status,
    statusText: res.statusText,
    headers: out,
  });
}

type Ctx = { params: Promise<{ path?: string[] }> };

export async function GET(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(req, path ?? []);
}

export async function POST(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(req, path ?? []);
}

export async function PUT(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(req, path ?? []);
}

export async function PATCH(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(req, path ?? []);
}

export async function DELETE(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(req, path ?? []);
}

export async function OPTIONS(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(req, path ?? []);
}
