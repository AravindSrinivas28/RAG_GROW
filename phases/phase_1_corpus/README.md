# Phase 1 — Corpus definition

**Status**: Implemented.

## Deliverables

| Artifact | Purpose |
|----------|---------|
| [corpus_manifest.yaml](./corpus_manifest.yaml) | Versioned URL list: **5** AMC hub seeds + **18** Groww scheme pages + **2** regulatory entry points = **25** unique URLs |
| [expansion_policy.md](./expansion_policy.md) | Rules for Phase 2 link-following, host allowlist, max URLs per run |
| `src/m1_rag/corpus.py` | Pydantic models, `load_corpus_manifest`, `iter_corpus_documents`, `validate_urls_against_allowlist` |
| `config/default.yaml` → `corpus` + expanded `allowlist.hosts` | `corpus.manifest_path`, `max_urls_per_ingest_run`; AMFI/SEBI hosts for regulatory URLs |

## Usage

```python
from pathlib import Path
from m1_rag.corpus import load_corpus_manifest, iter_corpus_documents, all_corpus_urls

m = load_corpus_manifest(Path("phases/phase_1_corpus/corpus_manifest.yaml"))
for doc in iter_corpus_documents(m):
    print(doc.document_type, doc.url)
urls = all_corpus_urls(m)
```

## Diversity

Scheme pages span **large-cap, multi-cap, mid/small-cap, ELSS, debt, liquid, overnight, index, multi-asset, hybrid**, across the five AMCs, plus AMFI/SEBI investor pages per [rag-architecture.md](../../docs/rag-architecture.md) §4.1.

## Next

- **Phase 2**: scraping service consumes `all_corpus_urls(manifest)` and enforces the allowlist at fetch time.
