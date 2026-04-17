# Phase 7 — API and threads

**Status**: Implemented.

## API

| File | Role |
|------|------|
| [`src/m1_rag/api.py`](../../src/m1_rag/api.py) | FastAPI app: `GET /health`, `POST /threads`, `POST /threads/{id}/messages` |
| [`src/m1_rag/thread_store.py`](../../src/m1_rag/thread_store.py) | SQLite persistence (`api.thread_store_path`) — **no PII columns** |

## Configuration

- `api.thread_store_path` in [`config/default.yaml`](../../config/default.yaml) (relative to project root unless absolute).

## Run

```bash
m1-rag-api
# or: uvicorn m1_rag.api:app --host 127.0.0.1 --port 8000
```

Optional: `M1_RAG_API_HOST`, `M1_RAG_API_PORT` for the `m1-rag-api` entrypoint (read from `.env`). Default port is **8000**; if something else already uses it, set e.g. `M1_RAG_API_PORT=8765`.

## Contract

- `POST /threads` → `{ "thread_id": "<uuid>" }`
- `POST /threads/{thread_id}/messages` with `{ "content": "..." }` → assistant payload with `answer_text`, `citation_url`, `last_updated`, `footer_line`, refusal/abstain flags.

See [rag-architecture.md](../../docs/rag-architecture.md) §8–9.
