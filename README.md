# M1 RAG — Facts-only mutual fund FAQ assistant

Implementation follows the phased plan in [docs/rag-architecture.md](docs/rag-architecture.md).

## Layout

| Path | Phase |
|------|--------|
| [phases/phase_0_foundation/](phases/phase_0_foundation/) | Foundation (config, deps, secrets policy) |
| [phases/phase_1_corpus/](phases/phase_1_corpus/) | Versioned `corpus_manifest.yaml` + loader (`m1_rag.corpus`) |
| [phases/phase_2_scrape/](phases/phase_2_scrape/) | HTTP fetch, normalize HTML/PDF, `content_hash` |
| [phases/phase_3_chunk_embed/](phases/phase_3_chunk_embed/) | HF tokenizer chunks, `bge-small-en-v1.5` embeddings, Chroma |
| [phases/phase_4_github_actions/](phases/phase_4_github_actions/) | Daily / manual ingest workflow |
| [phases/phase_5_retrieval/](phases/phase_5_retrieval/) | Query embed + Chroma ANN + filters |
| [phases/phase_6_router_generation/](phases/phase_6_router_generation/) | Router, grounded LLM, refusal templates |
| [phases/phase_7_api_threads/](phases/phase_7_api_threads/) | FastAPI + SQLite threads |
| [phases/phase_8_minimal_ui/](phases/phase_8_minimal_ui/) | Static chat UI (`src/m1_rag/static`), served at `GET /`; optional [Next.js UI](web/) |
| [phases/phase_9_quality/](phases/phase_9_quality/) | Golden cases, observability, CI quality workflow |

Shared application code lives under `src/m1_rag/`. Default configuration is in `config/default.yaml`.

## Quick start (Phase 0)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
pytest tests/
```

### Scrape corpus (Phase 2 — network)

Runs all manifest URLs with configured delay (default 1s between requests):

```bash
m1-rag-scrape
# or: python -m m1_rag.scrape
```

Writes one JSON object per line to stdout. Respect robots, rate limits, and site terms when running against production sites.

### Full ingest (Phase 3 — network + local embedder)

Scrapes the corpus, chunks text, runs **`BAAI/bge-small-en-v1.5`** via sentence-transformers (downloads from Hugging Face on first run), writes **Chroma** under `data/vector_store` (configurable):

```bash
m1-rag-ingest
# or: python -m m1_rag.ingest
```

Re-runs skip documents whose `content_hash` matches `data/ingest_state.json` (unless the page content changed).

### Scheduled ingest (Phase 4 — GitHub Actions)

Workflow [`.github/workflows/scheduled-ingest.yml`](.github/workflows/scheduled-ingest.yml) runs the same ingest **daily at 09:15 IST** (UTC cron `45 3 * * *`) and supports **workflow_dispatch** (no embedding API key required for the default local model). Runner storage for Chroma is ephemeral unless you add persistence.

### Retrieval (Phase 5 — query API)

After indexing, run a **dense search** (same embedding model as ingest):

```bash
m1-rag-retrieve "What is the expense ratio?"
```

Returns JSON with `chunks` (text + `source_url` + distance) and optional `abstain` if `retrieval.max_distance` is exceeded.

### HTTP API (Phase 6–7 — router + threads)

Set **`M1_RAG_OPENROUTER_API_KEY`** (or **`M1_RAG_LLM_API_KEY`**) for factual answers. Defaults use **OpenRouter** (`llm.api_base` in `config/default.yaml`). Ingest an index first (`m1-rag-ingest`).

```bash
m1-rag-api
# or: uvicorn m1_rag.api:app --host 127.0.0.1 --port 8000
```

- `POST /threads` → `{ "thread_id": "..." }`
- `POST /threads/{thread_id}/messages` with `{ "content": "your question" }` → JSON with `assistant.answer_text`, `citation_url`, `last_updated`, `footer_line`, and flags for refusal/abstention.

With the server running, open **http://127.0.0.1:8000/** (or your chosen port) for the **Phase 8** minimal UI (disclaimer, three example questions, multi-conversation sidebar using localStorage).

**Next.js UI (optional):** a React version lives under [`web/`](web/). Run `m1-rag-api` in one terminal, then `cd web && npm install && npm run dev` and open **http://127.0.0.1:3000** — set `NEXT_PUBLIC_M1_RAG_API_URL` in `web/.env.local` if the API is not at `http://127.0.0.1:8000`.

**Port already in use:** another process may be bound to `8000`. Pick a free port, e.g. add to `.env`: `M1_RAG_API_PORT=8765`, then run `m1-rag-api` and open **http://127.0.0.1:8765/**.

### Configuration notes

Pinned transitive versions: `requirements.lock` (optional `pip install -r requirements.lock` before editable install for stricter CI). Optional: [Dockerfile](Dockerfile) for a minimal runtime image.

### Deploy backend on Render

1. Push this repo to GitHub and open [Render](https://render.com) → **New** → **Blueprint** (or **Web Service** with **Docker**).
2. Select the repo; Render uses [`render.yaml`](render.yaml) and the root [`Dockerfile`](Dockerfile).
3. In the service **Environment**, add **`M1_RAG_OPENROUTER_API_KEY`** (or **`M1_RAG_LLM_API_KEY`**) — same as local `.env`. Render sets **`PORT`** automatically; the API binds **`0.0.0.0`** and uses that port.
4. After deploy, check **`https://<your-service>.onrender.com/health`** → `{"status":"ok"}`.
5. **Index:** the container starts with an **empty** `data/` directory unless you add a [persistent disk](https://render.com/docs/disks) or run **`m1-rag-ingest`** (e.g. one-off job or locally) and sync artifacts — otherwise retrieval has nothing to search. SQLite thread storage is also on ephemeral disk unless you attach a disk and point `api.thread_store_path` at it via a custom config.
6. Point the Next.js app at the API: **`NEXT_PUBLIC_M1_RAG_API_URL=https://<your-service>.onrender.com`** in `web/.env.local` (production env on Vercel, etc.).

On the **free** tier, web services **spin down** when idle; the first request after idle can take ~30–60s while the instance wakes.

### Deploy frontend on Vercel

After the API is live on Render, deploy the Next.js app from the same GitHub repo:

1. [Vercel](https://vercel.com) → **New Project** → import the repo.
2. Set **Root Directory** to **`web`** (required — the Next app is not at the repo root).
3. Add **`NEXT_PUBLIC_M1_RAG_API_URL`** = `https://<your-render-service>.onrender.com` (no trailing slash).
4. If the UI shows **“Load failed”** / cannot reach Render from the browser, add **`NEXT_PUBLIC_API_VIA_VERCEL_PROXY=1`** (same Render URL stays in `NEXT_PUBLIC_M1_RAG_API_URL` for server-side rewrites) and redeploy — see [`web/README.md`](web/README.md).
5. Deploy and open the assigned `*.vercel.app` URL.

Details: [`web/README.md`](web/README.md#deploy-on-vercel).

## Configuration

- **Data** (committed): `config/default.yaml` — allowlist hosts, embedding model id, vector DB backend/name/path, retrieval `top_k`, `llm.*`, `api.thread_store_path`, `observability.*` (Phase 9).
- **Secrets** (never committed): see `.env.example` and [phases/phase_0_foundation/SECRETS.md](phases/phase_0_foundation/SECRETS.md).

## Documentation

- [Problem statement](docs/problemStatement.md)
- [RAG architecture](docs/rag-architecture.md)
- [Chunking & embedding](docs/chunking-embedding-architecture.md)
