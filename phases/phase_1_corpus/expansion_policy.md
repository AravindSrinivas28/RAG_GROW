# Corpus expansion policy (Phase 1)

This document defines how the **frozen manifest** (`corpus_manifest.yaml`) relates to future **dynamic** expansion in Phase 2.

## Goals

- Stay within [rag-architecture.md](../../docs/rag-architecture.md) §4.1–4.2: **Groww** as reference context; expanded **official** PDFs/HTML only from AMC / AMFI / SEBI allowlisted hosts.
- Preserve **category diversity** (e.g., large-cap, flexi/multi-cap, ELSS, debt, liquid, index) across schemes and AMCs.

## Rules (for crawlers / scrapers)

| Rule | Detail |
|------|--------|
| **Seeds** | Always include the five AMC hub URLs in `seeds` in the manifest. |
| **Scheme pages** | Prefer one Groww **scheme** URL per chosen fund (`document_type: scheme_page`). Slugs follow `https://groww.in/mutual-funds/{slug}`. |
| **Max URLs per ingest run** | Default cap **40** total (seeds + expanded + regulatory) unless raised in config; problem statement targets **15–25** document URLs — this manifest uses **25** for a clear baseline. |
| **Link following** | Phase 2 may follow links **only** to hosts in `config/default.yaml` → `allowlist.hosts`. From a scheme page, allow following links to **factsheet/KIM/SID PDFs** on the same allowlisted AMC registrar domains. |
| **Blocked** | Third-party blogs, news aggregators, and non-curated comparison sites. |

## Versioning

- Bump `manifest_version` in `corpus_manifest.yaml` when URLs or entries change materially.
- Commit messages should note why the corpus changed (e.g., scheme renamed on Groww).
