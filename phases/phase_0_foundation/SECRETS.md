# Secrets policy (Phase 0)

API keys and tokens **must not** be committed. Use **environment variables** locally and **GitHub Actions secrets** in CI (Phase 4).

## Repository secrets (GitHub Actions)

Create these in the repo: **Settings → Secrets and variables → Actions**.

| Secret name | Used for | Required by |
|-------------|----------|-------------|
| `LLM_API_KEY` or `OPENROUTER_API_KEY` | Grounded generation (map to `M1_RAG_LLM_API_KEY` or `M1_RAG_OPENROUTER_API_KEY`) | Phase 6+ |

Phase 3 ingest/retrieve use **local** [`BAAI/bge-small-en-v1.5`](https://huggingface.co/BAAI/bge-small-en-v1.5) by default — **no** `EMBEDDING_API_KEY` is required unless you replace the embedder with a hosted API.

Optional: provider-specific names if you prefer (`OPENAI_API_KEY`, etc.)—then map them in the workflow to the env vars your code reads.

## Local development

Copy `.env.example` to `.env` at the project root. Supported names (see `src/m1_rag/settings.py`):

| Variable | Purpose |
|----------|---------|
| `M1_RAG_EMBEDDING_API_KEY` | Reserved for optional hosted embedding providers (unused with default local BGE) |
| `M1_RAG_OPENROUTER_API_KEY` | OpenRouter API key (preferred when using default `llm.api_base`) |
| `M1_RAG_LLM_API_KEY` | Any OpenAI-compatible API key (OpenAI, Azure, etc.) if not using `OPENROUTER_API_KEY` |
| `M1_RAG_CONFIG_FILE` | Optional absolute path to override `config/default.yaml` |
| `M1_RAG_APP_ENV` | Optional override for `app.env` in YAML |

## CI wiring (Phase 4 preview)

Workflows should inject secrets into the job environment when needed, for example:

```yaml
env:
  M1_RAG_OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

Adjust secret **names** to match what you configure in GitHub.
