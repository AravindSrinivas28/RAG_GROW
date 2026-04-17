# Phase 0 — Foundation

Implements tooling, **configuration as data**, and **secrets policy** per [rag-architecture.md](../../docs/rag-architecture.md) §2.3.

## Deliverables (this folder + repo root)

| Artifact | Location |
|----------|----------|
| Python project + pinned deps | `pyproject.toml`, `requirements.lock` |
| Default config (allowlist, embedding model id, vector DB, retrieval `top_k`) | `config/default.yaml` |
| Settings loader (YAML + env) | `src/m1_rag/settings.py` |
| Env template (no real secrets) | `.env.example` |
| GitHub / CI secret names | [SECRETS.md](./SECRETS.md) |
| Ignore rules for `.env`, venv, data | `.gitignore` |

## Usage

```bash
cd /path/to/M1_RAG
python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
# Reproducible install (no editable): pip install -r requirements.lock && pip install --no-deps .
cp .env.example .env
# Edit .env only locally; never commit.

python -c "from m1_rag.settings import AppSettings; s = AppSettings.load(); print(s.yaml.embedding.model_id)"
```

## Tests

```bash
pytest tests/
```

## Next

- **Phase 1**: frozen URL manifest under `phases/phase_1_corpus/`.
