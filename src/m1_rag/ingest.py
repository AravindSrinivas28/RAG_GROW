"""Phase 3: chunk → embed → upsert into Chroma; optional skip on unchanged content_hash."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from m1_rag.chunking import doc_id_for, normalized_to_chunks
from m1_rag.corpus import iter_corpus_documents, load_corpus_manifest, manifest_path_from_config
from m1_rag.embeddings import make_embed_fn
from m1_rag.scrape import NormalizedDocument, scrape_corpus
from m1_rag.settings import AppSettings
from m1_rag.vector_store import delete_by_doc_id, get_collection, upsert_chunks

if TYPE_CHECKING:
    pass


@dataclass
class IngestReport:
    documents_total: int = 0
    documents_skipped_unchanged: int = 0
    documents_indexed: int = 0
    chunks_upserted: int = 0
    errors: list[str] = field(default_factory=list)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _state_path(app: AppSettings) -> Path:
    p = Path(app.yaml.ingest.state_path)
    if not p.is_absolute():
        p = _project_root() / p
    return p


def load_ingest_state(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}


def save_ingest_state(path: Path, state: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def ingest_normalized_documents(
    app: AppSettings,
    documents: list[NormalizedDocument],
    embed_texts: Callable[[list[str]], list[list[float]]],
) -> IngestReport:
    """
    Chunk, embed, upsert. Skips documents whose content_hash matches ingest state.
    On content change, deletes prior vectors for doc_id then upserts new chunks.
    """
    report = IngestReport(documents_total=len(documents))
    state = load_ingest_state(_state_path(app))
    root = _project_root()
    persist = root / app.yaml.vector_db.persist_directory
    collection = get_collection(persist, app.yaml.vector_db.collection_name)

    cfg = app.yaml.chunking
    emb_cfg = app.yaml.embedding
    embedded_at = datetime.now(timezone.utc).isoformat()

    for norm in documents:
        doc_id = doc_id_for(norm)
        if state.get(doc_id) == norm.content_hash:
            report.documents_skipped_unchanged += 1
            continue

        chunks = normalized_to_chunks(
            norm,
            tokenizer_model_id=cfg.tokenizer_model_id,
            chunk_size_tokens=cfg.chunk_size_tokens,
            overlap_tokens=cfg.overlap_tokens,
        )
        if not chunks:
            report.errors.append(f"no chunks for {norm.source_url}")
            continue

        texts = [c.text for c in chunks]
        try:
            vectors = embed_texts(texts)
        except Exception as e:
            report.errors.append(f"embed failed {norm.source_url}: {e!s}")
            continue

        if len(vectors) != len(chunks):
            report.errors.append(f"embedding count mismatch for {norm.source_url}")
            continue

        bad_dim = False
        for i, vec in enumerate(vectors):
            if len(vec) != emb_cfg.dimensions:
                report.errors.append(
                    f"dim {len(vec)} != config {emb_cfg.dimensions} for {norm.source_url} chunk {i}",
                )
                bad_dim = True
                break
        if bad_dim:
            continue

        try:
            delete_by_doc_id(collection, doc_id)
            upsert_chunks(
                collection,
                chunks,
                vectors,
                embedding_model_id=emb_cfg.model_id,
                embedded_at_iso=embedded_at,
            )
        except Exception as e:
            report.errors.append(f"chroma upsert {norm.source_url}: {e!s}")
            continue

        state[doc_id] = norm.content_hash
        save_ingest_state(_state_path(app), state)
        report.documents_indexed += 1
        report.chunks_upserted += len(chunks)

    return report


def run_full_ingest(app: AppSettings) -> IngestReport:
    """Scrape manifest URLs then chunk, embed locally, and index."""
    path = manifest_path_from_config(app.yaml.corpus.manifest_path)
    manifest = load_corpus_manifest(path)
    corpus_docs = iter_corpus_documents(manifest)
    if len(corpus_docs) > app.yaml.corpus.max_urls_per_ingest_run:
        raise RuntimeError("corpus exceeds max_urls_per_ingest_run")

    scrape_results = scrape_corpus(corpus_docs, app.yaml, project_root=_project_root())
    norms: list[NormalizedDocument] = []
    for r in scrape_results:
        if r.success and r.document:
            norms.append(r.document)

    embed_texts = make_embed_fn(app.yaml.embedding)
    return ingest_normalized_documents(app, norms, embed_texts)


def main() -> None:
    app = AppSettings.load()
    try:
        report = run_full_ingest(app)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    print(
        json.dumps(
            {
                "documents_total": report.documents_total,
                "documents_skipped_unchanged": report.documents_skipped_unchanged,
                "documents_indexed": report.documents_indexed,
                "chunks_upserted": report.chunks_upserted,
                "errors": report.errors,
            },
            indent=2,
        )
    )
    if report.errors:
        sys.exit(2)


if __name__ == "__main__":
    main()
