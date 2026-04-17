# Phase 6 — Router and generation

**Status**: Implemented.

## Modules

| Piece | Module |
|-------|--------|
| Route rules (advisory / PII / factual) | [`src/m1_rag/router.py`](../../src/m1_rag/router.py) |
| Refusal + generation prompts (versioned) | [`src/m1_rag/prompts/`](../../src/m1_rag/prompts/) |
| Post-checks (sentence cap, URL validation) | [`src/m1_rag/postcheck.py`](../../src/m1_rag/postcheck.py) |
| Grounded JSON LLM call | [`src/m1_rag/generation.py`](../../src/m1_rag/generation.py) |
| Orchestration | [`src/m1_rag/assistant.py`](../../src/m1_rag/assistant.py) |

## Configuration

- `llm.model`, `llm.temperature`, `llm.max_tokens`, optional `llm.api_base` in [`config/default.yaml`](../../config/default.yaml).
- **Secrets**: `M1_RAG_OPENROUTER_API_KEY` or `M1_RAG_LLM_API_KEY`. Defaults in `config/default.yaml` target **OpenRouter** (`https://openrouter.ai/api/v1`) with model slugs like `openai/gpt-4o-mini`. To use OpenAI directly, set `llm.api_base` to `https://api.openai.com/v1` and `M1_RAG_LLM_API_KEY`.

## Behaviour

- Advisory/comparative and PII-style prompts get **template refusals** + one educational link (no retrieval).
- Factual path: **retrieve** → **grounded generation** with JSON `answer_text` / `citation_url` / `last_updated`, then post-checks (≤3 sentences, citation must match retrieved sources).

See [rag-architecture.md](../../docs/rag-architecture.md) §6–7.
