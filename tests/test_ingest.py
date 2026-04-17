"""Phase 3 ingest (mocked embeddings)."""

from datetime import datetime, timezone
from pathlib import Path

from m1_rag.chunking import doc_id_for
from m1_rag.ingest import _state_path, ingest_normalized_documents, load_ingest_state, save_ingest_state
from m1_rag.scrape import NormalizedDocument
from m1_rag.settings import AppSettings, SecretsSettings, YamlConfig
from m1_rag.vector_store import get_collection


def _fake_embed(dim: int):
    def _embed(texts: list[str]) -> list[list[float]]:
        return [[0.1] * dim for _ in texts]

    return _embed


def _minimal_app(tmp_path: Path, state_name: str = "ingest_state.json") -> AppSettings:
    yaml = YamlConfig.model_validate(
        {
            "chunking": {
                "tokenizer_model_id": "bert-base-uncased",
                "chunk_size_tokens": 128,
                "overlap_tokens": 16,
            },
            "embedding": {
                "model_id": "test-model",
                "dimensions": 384,
                "batch_size": 8,
            },
            "vector_db": {
                "backend": "chroma",
                "collection_name": "test_m1",
                "persist_directory": str(tmp_path / "chroma"),
            },
            "ingest": {"state_path": str(tmp_path / state_name)},
        }
    )
    return AppSettings(yaml=yaml, secrets=SecretsSettings())


def test_ingest_state_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "s.json"
    save_ingest_state(p, {"a": "1"})
    assert load_ingest_state(p) == {"a": "1"}


def test_ingest_upserts_and_skips_on_hash(tmp_path: Path) -> None:
    app = _minimal_app(tmp_path)
    dim = app.yaml.embedding.dimensions

    n = NormalizedDocument(
        source_url="https://groww.in/mutual-funds/foo",
        final_url="https://groww.in/mutual-funds/foo",
        fetched_at=datetime.now(timezone.utc),
        content_hash="hash1",
        mime_type="text/html",
        text=("Minimum SIP Rs 500. " * 80).strip(),
        manifest_document_type="scheme_page",
        amc_id="hdfc",
    )

    r1 = ingest_normalized_documents(app, [n], _fake_embed(dim))
    assert r1.documents_indexed == 1
    assert r1.chunks_upserted >= 1
    assert r1.documents_skipped_unchanged == 0
    assert not r1.errors

    col = get_collection(tmp_path / "chroma", "test_m1")
    got = col.get(include=["metadatas"], where={"doc_id": doc_id_for(n)})
    assert got["ids"] and len(got["ids"]) >= 1

    r2 = ingest_normalized_documents(app, [n], _fake_embed(dim))
    assert r2.documents_skipped_unchanged == 1
    assert r2.documents_indexed == 0
    assert r2.chunks_upserted == 0

    n2 = n.model_copy(update={"content_hash": "hash2"})
    r3 = ingest_normalized_documents(app, [n2], _fake_embed(dim))
    assert r3.documents_indexed == 1
    assert r3.documents_skipped_unchanged == 0


def test_state_path_resolves(tmp_path: Path) -> None:
    app = _minimal_app(tmp_path)
    p = _state_path(app)
    assert p.is_absolute()
    assert p.name == "ingest_state.json"
