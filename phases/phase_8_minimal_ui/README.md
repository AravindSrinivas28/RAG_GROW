# Phase 8 — Minimal UI

**Status**: Implemented.

## Behaviour

- **Single-page chat** with a **sticky header** that always shows the disclaimer: *Facts-only. No investment advice.*
- **Welcome** copy plus **three clickable example questions** (minimum SIP, expense ratio, exit load).
- Each assistant reply shows **answer text**, **one source link** (`citation_url`), and the **footer line** (`footer_line` / last updated) from the API.
- **Multi-thread (client-side)**: sidebar lists conversations; **New conversation** creates another `thread_id` via `POST /threads`. Message history for each thread is stored in **localStorage** (browser-only); the server still persists messages in SQLite for audit, but the UI does not call a history API.

## Files

| Location | Role |
|----------|------|
| [`src/m1_rag/static/index.html`](../../src/m1_rag/static/index.html) | Markup: header disclaimer, sidebar, welcome + examples, composer |
| [`src/m1_rag/static/styles.css`](../../src/m1_rag/static/styles.css) | Layout (responsive), bubbles |
| [`src/m1_rag/static/app.js`](../../src/m1_rag/static/app.js) | Fetch `POST /threads` and `POST /threads/{id}/messages`, thread list + storage |
| [`web/`](../../web/) | Optional **Next.js** UI — same contract and localStorage keys; see [`web/README.md`](../../web/README.md) |

## Serving

The FastAPI app exposes:

- `GET /` — minimal UI (`index.html`)
- `GET /static/*` — CSS/JS

Run `m1-rag-api` and open **http://127.0.0.1:8000/** unless you set `M1_RAG_API_PORT` in `.env` (use that port if `8000` is already taken by another app).

See [rag-architecture.md](../../docs/rag-architecture.md) §2.3 Phase 8 and §9.2.
