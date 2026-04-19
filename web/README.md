# M1 RAG — Next.js UI

React implementation of the Phase 8 chat (same behaviour as [`src/m1_rag/static/`](../src/m1_rag/static/)): disclaimer, example chips, sidebar threads (localStorage), and calls to the FastAPI backend.

## Prerequisites

Run the API from the repo root (Python venv):

```bash
m1-rag-api
# default: http://127.0.0.1:8000
```

## Configure API URL

Copy `.env.local.example` to `.env.local` and adjust if the API is not on port 8000:

```bash
cp .env.local.example .env.local
```

`NEXT_PUBLIC_M1_RAG_API_URL` must match the host/port where `m1-rag-api` listens (**no trailing slash**). For a backend on Render, use `https://your-service.onrender.com`.

**Safari / “Load failed” to Render:** set **`NEXT_PUBLIC_API_VIA_VERCEL_PROXY=1`** on Vercel (keep **`NEXT_PUBLIC_M1_RAG_API_URL`** as your Render URL — the server uses it to proxy `/api/m1/*` to Render). The browser only talks to your `*.vercel.app` origin.

**502 / “Invalid response from server” on `/api/m1/.../messages`:** the proxy uses a **Route Handler** with **`maxDuration` 300s** so long RAG + LLM calls are not cut off by Vercel’s old rewrite timeout. On the **Hobby** plan, Vercel may still cap function duration (often **10s**) — upgrade to **Pro** or expect timeouts on slow turns. Redeploy after pulling the latest `web/` code.

## Run Next.js

```bash
cd web
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). The browser talks **directly** to the FastAPI origin (CORS is enabled on the API); no Next.js API routes are required.

## Deploy on Vercel

This app lives in the **`web/`** folder of the monorepo — set that when importing the repo.

1. Go to [vercel.com](https://vercel.com) → **Add New…** → **Project** → import **`RAG_GROW`** (or your fork) from GitHub.
2. **Root Directory:** click **Edit** and set it to **`web`**. Vercel should detect **Next.js**.
3. **Environment Variables:** add  
   **`NEXT_PUBLIC_M1_RAG_API_URL`** = `https://<your-render-service>.onrender.com`  
   (your deployed FastAPI base URL, **no** trailing slash — use `https`).
4. **Deploy.** After the build finishes, open the `.vercel.app` URL; the chat should call your Render API.

Redeploy from Vercel whenever you change this variable or merge UI changes to the tracked branch.

**Send stays disabled or shows “Sending…” forever:** the UI disables Send while a request to your API is in flight. On a cold Render service the first request can take **1–2 minutes**. If it exceeds **3 minutes**, the client times out and shows an error — redeploy the API or check Render logs. **`NEXT_PUBLIC_*` is baked in at build time** — after adding or changing it in Vercel, trigger a **new deployment** so the browser gets the correct Render URL (not `http://127.0.0.1:8000`).

## Production (self-hosted)

```bash
npm run build
npm run start
```
