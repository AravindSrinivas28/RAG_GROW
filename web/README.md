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

`NEXT_PUBLIC_M1_RAG_API_URL` must match the host/port where `m1-rag-api` listens (no trailing slash).

## Run Next.js

```bash
cd web
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). The browser talks **directly** to the FastAPI origin (CORS is enabled on the API); no Next.js API routes are required.

## Production

```bash
npm run build
npm run start
```
