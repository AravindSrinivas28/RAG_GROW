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

## Production (self-hosted)

```bash
npm run build
npm run start
```
