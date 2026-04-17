"""Phase 3b: sentence-transformers embeddings (same model as ingest and retrieval)."""

from __future__ import annotations

from typing import Callable

from m1_rag.settings import EmbeddingSection


def make_embed_fn(emb: EmbeddingSection) -> Callable[[list[str]], list[list[float]]]:
    """Return a function that embeds batches of texts using `emb.model_id` (e.g. BAAI/bge-small-en-v1.5)."""

    _model = None

    def _load():
        nonlocal _model
        if _model is None:
            from sentence_transformers import SentenceTransformer

            kwargs: dict = {}
            if emb.device:
                kwargs["device"] = emb.device
            _model = SentenceTransformer(emb.model_id, **kwargs)
        return _model

    def embed_all(texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = _load()
        bs = max(1, emb.batch_size)
        out: list[list[float]] = []
        for i in range(0, len(texts), bs):
            batch = texts[i : i + bs]
            vecs = model.encode(
                batch,
                batch_size=len(batch),
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            # sentence-transformers returns a 2D ndarray for batch input
            out.extend(vecs.tolist())
        return out

    return embed_all


def embed_query_text(embed_all: Callable[[list[str]], list[list[float]]], query: str) -> list[float]:
    """Single query embedding (same model as corpus)."""
    vecs = embed_all([query])
    if not vecs:
        raise RuntimeError("embedding returned no vector")
    return vecs[0]
