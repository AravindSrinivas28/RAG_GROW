# Phase 3 — Chunk, embed, index

**Status**: Implemented.

## Modules

| Step | Module | Role |
|------|--------|------|
| Chunk | [`src/m1_rag/chunking.py`](../../src/m1_rag/chunking.py) | `doc_id`, Hugging Face tokenizer sliding windows (`tokenizer_model_id`), `ChunkRecord` |
| Embed | [`src/m1_rag/embeddings.py`](../../src/m1_rag/embeddings.py) | sentence-transformers `encode` for `BAAI/bge-small-en-v1.5`, batched by `embedding.batch_size` |
| Store | [`src/m1_rag/vector_store.py`](../../src/m1_rag/vector_store.py) | Chroma `PersistentClient`, cosine space, upsert + delete-by-`doc_id` |
| Orchestrate | [`src/m1_rag/ingest.py`](../../src/m1_rag/ingest.py) | Skip unchanged `content_hash`, state file, full pipeline |

## Configuration (`config/default.yaml`)

- **`chunking`**: `tokenizer_model_id` (default matches BGE), `chunk_size_tokens`, `overlap_tokens`
- **`embedding`**: `model_id`, `dimensions` (384), `batch_size`, optional `device` (e.g. `cuda:0`)
- **`ingest.state_path`**: JSON map `doc_id` → `content_hash` for skip-on-unchanged
- **`vector_db`**: `persist_directory`, `collection_name`

## CLI

No embedding API key required (local model downloads from Hugging Face on first use).

```bash
m1-rag-ingest
# or: python -m m1_rag.ingest
```

Runs: manifest → scrape all URLs → chunk → embed → Chroma upsert. Prints a JSON summary (counts + errors). Exits `2` if any indexing error occurred.

## Tests

Chunking and ingest use **mock embeddings** and a temp Chroma dir (`tests/test_chunking.py`, `tests/test_ingest.py`). No embedding inference in CI.

## Next

- **Phase 4**: schedule this command via GitHub Actions.
- **Phase 5**: query embedding + Chroma query on the same collection.
