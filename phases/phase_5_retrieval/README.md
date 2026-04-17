# Phase 5 — Retrieval service

**Status**: Implemented.

## Module

[`src/m1_rag/retrieval.py`](../../src/m1_rag/retrieval.py)

| Piece | Role |
|-------|------|
| `preprocess_query` | NFC, strip, collapse whitespace |
| `build_where_filter` | Optional Chroma `where` on `amc_id` and/or `manifest_document_type` |
| `retrieve` | Embed query (same sentence-transformers model as ingest) → `collection.query` with `top_k`, distances, metadata |
| `RetrievedChunk` / `RetrievalResult` | `chunk_id`, `text`, `source_url`, `distance`, `metadata`; `abstain` + `abstain_reason` |

## Configuration (`config/default.yaml` → `retrieval`)

- **`top_k`**: number of chunks to return.
- **`max_distance`**: if set, **`abstain`** is true when the **best** match distance exceeds this (tune on your Chroma/cosine setup). `null` = never abstain on distance alone.

## CLI

Uses the same local embedder as ingest (no API key required by default).

```bash
m1-rag-retrieve "What is the minimum SIP for HDFC Large Cap?"
# or: python -m m1_rag.retrieval "..."
```

Prints JSON (`RetrievalResult`). Does not call the LLM (Phase 6).

## Optional filters (API use)

Call `retrieve(app, query, where=build_where_filter(amc_id="hdfc"))` etc.

## Tests

[`tests/test_retrieval.py`](../../tests/test_retrieval.py) — in-memory Chroma + mocked embeddings.

## Next

- **Phase 6**: pass `RetrievalResult.chunks` into the grounded generator and router.
