# Phase 9 — Quality and observability

**Status**: Implemented (baseline).

## Offline evaluation

| Artifact | Purpose |
|----------|---------|
| [`golden_cases.yaml`](golden_cases.yaml) | Curated router cases: advisory, PII, factual prompts |
| [`tests/test_golden_offline.py`](../../tests/test_golden_offline.py) | Pytest reads YAML and asserts `classify_route` outcomes |

Extend `golden_cases.yaml` as the router grows; add integration tests separately for full RAG answers when you have a stable index.

## Online / runtime

- **Structured logs** (`m1_rag.chat` logger): each `POST /threads/{id}/messages` emits one JSON line with `latency_ms`, `refusal`, `abstain`, `route`, `top_distance`, `n_chunks`, `query_hash` (never raw user text). Configure level via `observability.log_level` or **`M1_RAG_LOG_LEVEL`**.
- **Index regression**: `m1-rag-index-inspect` prints Chroma row count for the configured collection (spot-check after re-ingest).

## CI

[`.github/workflows/quality.yml`](../../.github/workflows/quality.yml) runs **`pytest`** on pushes/PRs to `main`/`master`.

See [rag-architecture.md](../../docs/rag-architecture.md) §10 and Phase 9 in §2.3.
