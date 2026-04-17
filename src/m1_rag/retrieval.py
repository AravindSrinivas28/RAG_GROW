"""Phase 5: embed query → Chroma ANN search with optional filters and abstention."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from m1_rag.embeddings import embed_query_text, make_embed_fn
from m1_rag.settings import AppSettings
from m1_rag.vector_store import get_collection


def preprocess_query(text: str) -> str:
    """Light normalization: NFC, strip, collapse whitespace."""
    t = unicodedata.normalize("NFC", text)
    t = t.strip()
    t = re.sub(r"\s+", " ", t)
    return t


def build_where_filter(
    *,
    amc_id: str | None = None,
    manifest_document_types: list[str] | None = None,
) -> dict[str, Any] | None:
    """
    Chroma `where` clause for metadata filters.

    Empty strings in stored metadata are treated as missing — do not filter on amc_id=\"\".
    """
    clauses: list[dict[str, Any]] = []
    if amc_id:
        clauses.append({"amc_id": {"$eq": amc_id}})
    if manifest_document_types:
        if len(manifest_document_types) == 1:
            clauses.append({"manifest_document_type": {"$eq": manifest_document_types[0]}})
        else:
            clauses.append(
                {
                    "$or": [
                        {"manifest_document_type": {"$eq": t}} for t in manifest_document_types
                    ]
                }
            )
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    source_url: str
    distance: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    abstain: bool = False
    abstain_reason: str | None = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def retrieve(
    app: AppSettings,
    query: str,
    *,
    where: dict[str, Any] | None = None,
    embed_texts: Callable[[list[str]], list[list[float]]] | None = None,
    top_k: int | None = None,
) -> RetrievalResult:
    """
    Dense retrieval: embed `query` with the same model as ingest, query Chroma.

    If `max_distance` is set in config and the best match distance exceeds it, `abstain` is True
    with chunks still populated for inspection (caller may ignore).
    """
    q = preprocess_query(query)
    if not q:
        return RetrievalResult(query=query, abstain=True, abstain_reason="empty_query")

    embed_fn = embed_texts or make_embed_fn(app.yaml.embedding)
    qvec = embed_query_text(embed_fn, q)

    root = _project_root()
    persist = root / app.yaml.vector_db.persist_directory
    collection = get_collection(persist, app.yaml.vector_db.collection_name)

    try:
        n_docs = collection.count()
    except Exception:
        n_docs = 0

    if n_docs == 0:
        return RetrievalResult(query=query, abstain=True, abstain_reason="empty_index")

    k = top_k if top_k is not None else app.yaml.retrieval.top_k
    n_results = min(max(k, 1), n_docs)

    kwargs: dict[str, Any] = {
        "query_embeddings": [qvec],
        "n_results": n_results,
        "include": ["metadatas", "documents", "distances"],
    }
    if where:
        kwargs["where"] = where

    raw = collection.query(**kwargs)

    ids_batch = raw.get("ids") or []
    dist_batch = raw.get("distances") or []
    meta_batch = raw.get("metadatas") or []
    doc_batch = raw.get("documents") or []

    ids = ids_batch[0] if ids_batch else []
    distances = dist_batch[0] if dist_batch else []
    metas = meta_batch[0] if meta_batch else []
    docs = doc_batch[0] if doc_batch else []

    chunks: list[RetrievedChunk] = []
    for i, cid in enumerate(ids):
        meta = dict(metas[i]) if i < len(metas) and metas[i] else {}
        text = docs[i] if i < len(docs) and docs[i] is not None else ""
        dist = float(distances[i]) if i < len(distances) and distances[i] is not None else None
        src = str(meta.get("source_url", "") or meta.get("final_url", ""))
        chunks.append(
            RetrievedChunk(
                chunk_id=str(cid),
                text=text,
                source_url=src,
                distance=dist,
                metadata=meta,
            )
        )

    abstain = False
    reason: str | None = None
    max_d = app.yaml.retrieval.max_distance
    if chunks and max_d is not None and chunks[0].distance is not None:
        if chunks[0].distance > max_d:
            abstain = True
            reason = f"best_distance_{chunks[0].distance:.4f}_exceeds_max_{max_d}"

    return RetrievalResult(query=query, chunks=chunks, abstain=abstain, abstain_reason=reason)


def main() -> None:
    """CLI: one query string → JSON RetrievalResult on stdout."""
    import json
    import sys

    app = AppSettings.load()
    if len(sys.argv) < 2:
        print("Usage: m1-rag-retrieve 'your question'", file=sys.stderr)
        sys.exit(1)
    query = " ".join(sys.argv[1:])
    try:
        result = retrieve(app, query)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    print(result.model_dump(mode="json", exclude_none=True))


if __name__ == "__main__":
    main()
