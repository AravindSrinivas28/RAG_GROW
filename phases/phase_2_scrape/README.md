# Phase 2 — Scrape and normalize

**Status**: Implemented.

## Deliverables

| Piece | Location |
|-------|----------|
| Scrape + normalize | [`src/m1_rag/scrape.py`](../../src/m1_rag/scrape.py) |
| Config | `config/default.yaml` → `scrape` (`user_agent`, `delay_seconds`, `timeout_seconds`, `max_retries`, `respect_robots_txt`, optional raw snapshots) |
| Models | `NormalizedDocument` (text, `content_hash`, `mime_type`, `final_url`, `fetched_at`, manifest metadata) |
| CLI | `m1-rag-scrape` or `python -m m1_rag.scrape` → JSON lines on stdout (full corpus; **hits the network**) |

## Behaviour (architecture §3.2, §4.2)

- **Allowlist**: URLs validated with [`validate_urls_against_allowlist`](../phase_1_corpus/README.md) before any GET.
- **robots.txt**: [`urllib.robotparser`](https://docs.python.org/3/library/urllib.robotparser.html) per origin (fetched with stdlib `urllib`, not httpx). If `respect_robots_txt: false`, checks are skipped (e.g. tests).
- **Throttle**: `delay_seconds` sleep between requests (sequential batch).
- **User-Agent**: `scrape.user_agent` on every request.
- **HTML**: [trafilatura](https://github.com/adbar/trafilatura) extract, fallback tag-strip.
- **PDF**: `application/pdf` or `%PDF` magic → [pypdf](https://pypdf.readthedocs.io/) text extraction.
- **Hashing**: SHA-256 of normalized UTF-8 **text** (for Phase 3 skip-if-unchanged).
- **Failures**: `ScrapeResult` per URL; batch always completes.

## Optional raw snapshots

Set `scrape.store_raw_snapshots: true` to write response bytes under `raw_snapshots_dir` (filename keyed by URL hash).

## Tests

Mocked HTTP only (`tests/test_scrape.py`). No network in CI.

## Next

- **Phase 3**: chunk → embed → index using `NormalizedDocument.text` and `content_hash`.
