"""Phase 5 retrieval (in-memory Chroma + mocked embeddings)."""

import chromadb
import pytest

from m1_rag.retrieval import (
    build_where_filter,
    preprocess_query,
    retrieve,
)
from m1_rag.settings import AppSettings, SecretsSettings, YamlConfig


def _yaml() -> YamlConfig:
    return YamlConfig.model_validate(
        {
            "retrieval": {"top_k": 5, "max_distance": None},
            "embedding": {"model_id": "test", "dimensions": 384, "batch_size": 8},
            "vector_db": {
                "persist_directory": "/tmp/unused",
                "collection_name": "t",
            },
        }
    )


def _app() -> AppSettings:
    return AppSettings(yaml=_yaml(), secrets=SecretsSettings())


def test_preprocess_query() -> None:
    assert preprocess_query("  hello   world  ") == "hello world"


def test_build_where_amc() -> None:
    w = build_where_filter(amc_id="hdfc")
    assert w == {"amc_id": {"$eq": "hdfc"}}


def test_build_where_types_or() -> None:
    w = build_where_filter(manifest_document_types=["hub", "scheme_page"])
    assert "$or" in w


def test_retrieve_empty_index(monkeypatch: pytest.MonkeyPatch) -> None:
    client = chromadb.Client()
    col = client.create_collection("empty", metadata={"hnsw:space": "cosine"})
    monkeypatch.setattr("m1_rag.retrieval.get_collection", lambda _p, _n: col)

    def embed(_: list[str]) -> list[list[float]]:
        return [[0.0] * 384]

    r = retrieve(_app(), "test", embed_texts=embed)
    assert r.abstain
    assert r.abstain_reason == "empty_index"


def test_retrieve_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    dim = 384
    u = 1.0 / (dim**0.5)
    vec = [u] * dim

    client = chromadb.Client()
    col = client.create_collection("ret-hits", metadata={"hnsw:space": "cosine"})
    col.add(
        ids=["doc:0"],
        embeddings=[vec],
        documents=["Minimum SIP Rs 500 per month."],
        metadatas=[
            {
                "source_url": "https://groww.in/mutual-funds/x",
                "final_url": "https://groww.in/mutual-funds/x",
                "amc_id": "hdfc",
                "manifest_document_type": "scheme_page",
                "doc_id": "abc",
                "chunk_index": 0,
                "content_hash": "h",
                "scheme_name": "Test",
                "category": "",
                "embedding_model_id": "m",
                "embedded_at": "t",
                "fetched_at": "t",
                "start_char": 0,
                "end_char": 20,
            }
        ],
    )
    monkeypatch.setattr("m1_rag.retrieval.get_collection", lambda _p, _n: col)

    def embed(texts: list[str]) -> list[list[float]]:
        return [vec for _ in texts]

    r = retrieve(_app(), "What is the minimum SIP?", embed_texts=embed)
    assert len(r.chunks) == 1
    assert not r.abstain
    assert "500" in r.chunks[0].text
    assert "groww.in" in r.chunks[0].source_url


def test_retrieve_max_distance_abstain(monkeypatch: pytest.MonkeyPatch) -> None:
    dim = 384
    u = 1.0 / (dim**0.5)
    vec = [u] * dim
    far = [0.0] * dim
    far[0] = 1.0

    client = chromadb.Client()
    col = client.create_collection("ret-maxdist", metadata={"hnsw:space": "cosine"})
    col.add(
        ids=["1"],
        embeddings=[vec],
        documents=["text"],
        metadatas=[
            {
                "source_url": "https://u",
                "final_url": "https://u",
                "amc_id": "",
                "manifest_document_type": "regulatory",
                "doc_id": "d",
                "chunk_index": 0,
                "content_hash": "h",
                "scheme_name": "",
                "category": "",
                "embedding_model_id": "m",
                "embedded_at": "t",
                "fetched_at": "t",
                "start_char": 0,
                "end_char": 1,
            }
        ],
    )
    monkeypatch.setattr("m1_rag.retrieval.get_collection", lambda _p, _n: col)

    yaml = YamlConfig.model_validate(
        {
            "retrieval": {"top_k": 3, "max_distance": 0.001},
            "embedding": {"model_id": "test", "dimensions": 384, "batch_size": 8},
            "vector_db": {"persist_directory": "/x", "collection_name": "ret-maxdist"},
        }
    )
    app = AppSettings(yaml=yaml, secrets=SecretsSettings())

    def embed_far(_: list[str]) -> list[list[float]]:
        return [far]

    r = retrieve(app, "unrelated query", embed_texts=embed_far)
    assert r.abstain
    assert r.abstain_reason and "exceeds_max" in r.abstain_reason
