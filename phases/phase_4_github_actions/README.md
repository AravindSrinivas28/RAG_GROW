# Phase 4 — GitHub Actions schedule

**Status**: Implemented.

## Workflow

| File | Purpose |
|------|---------|
| [`.github/workflows/scheduled-ingest.yml`](../../.github/workflows/scheduled-ingest.yml) | Daily cron + manual **workflow_dispatch** |

- **Cron**: `45 3 * * *` (UTC) = **09:15 IST** (Asia/Kolkata, no DST). Comment in YAML repeats this.
- **Manual**: Actions → *Scheduled corpus ingest* → **Run workflow**.
- **Entrypoint**: `python -m m1_rag.ingest` (same as [`m1-rag-ingest`](../../README.md)).
- **Timeout**: 90 minutes (scrape delay + first-time model download + embed batch for ~25 URLs).
- **Summary**: On completion or failure, last step appends `ingest_report.json` to the job summary when the file exists.

No **`EMBEDDING_API_KEY`** repository secret is required for the default **local** `bge-small-en-v1.5` embedder (models load from Hugging Face on the runner). Optional: cache `HF_HOME` between runs to speed up cold starts.

See [phase_0 SECRETS.md](../phase_0_foundation/SECRETS.md) for LLM keys (Phase 6+).

## Ephemeral runner storage

The job writes Chroma under `data/vector_store` on the runner; **it is not persisted** between runs unless you add artifact upload, a remote vector DB, or a deploy step. For production, point Phase 3 storage at a durable backend or sync artifacts.

## Next

- **Phase 5**: retrieval service reading the same `persist_directory` / collection in a long-lived environment.
