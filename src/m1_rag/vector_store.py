"""Phase 3c: Chroma persistent vector store."""

from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection

from m1_rag.chunking import ChunkRecord


def get_collection(
    persist_directory: Path | str,
    collection_name: str,
) -> Collection:
    """Open or create a cosine-distance collection."""
    path = Path(persist_directory)
    path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(path.resolve()))
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def chroma_metadata(rec: ChunkRecord, embedding_model_id: str, embedded_at_iso: str) -> dict:
    """Chroma metadata: str / int / float / bool only."""
    meta: dict = {
        "doc_id": rec.doc_id,
        "chunk_index": rec.chunk_index,
        "source_url": rec.source_url,
        "final_url": rec.final_url,
        "content_hash": rec.content_hash,
        "manifest_document_type": rec.manifest_document_type,
        "embedding_model_id": embedding_model_id,
        "embedded_at": embedded_at_iso,
        "fetched_at": rec.fetched_at_iso,
        "start_char": rec.start_char,
        "end_char": rec.end_char,
    }
    meta["amc_id"] = rec.amc_id or ""
    meta["scheme_name"] = rec.scheme_name or ""
    meta["category"] = rec.category or ""
    return meta


def delete_by_doc_id(collection: Collection, doc_id: str) -> None:
    """Remove all vectors for a document before re-ingest."""
    collection.delete(where={"doc_id": doc_id})


def upsert_chunks(
    collection: Collection,
    records: list[ChunkRecord],
    embeddings: list[list[float]],
    *,
    embedding_model_id: str,
    embedded_at_iso: str,
) -> None:
    if len(records) != len(embeddings):
        raise ValueError("records and embeddings length mismatch")
    if not records:
        return
    ids = [r.chunk_id for r in records]
    metadatas = [chroma_metadata(r, embedding_model_id, embedded_at_iso) for r in records]
    documents = [r.text for r in records]
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents,
    )
