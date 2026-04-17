"""Phase 3 chunking."""

from datetime import datetime, timezone

from m1_rag.chunking import (
    chunk_text_sliding,
    doc_id_for,
    normalize_unicode,
    normalized_to_chunks,
)
from m1_rag.scrape import NormalizedDocument


def test_normalize_unicode() -> None:
    assert normalize_unicode("  a\n\nb  ") == "a\n\nb"


def test_doc_id_stable() -> None:
    n = NormalizedDocument(
        source_url="https://groww.in/x",
        final_url="https://groww.in/x",
        fetched_at=datetime.now(timezone.utc),
        content_hash="abc",
        mime_type="text/html",
        text="t",
        manifest_document_type="scheme_page",
    )
    assert doc_id_for(n) == doc_id_for(n)


def test_chunk_short_text_single_chunk() -> None:
    t = "Hello world " * 10
    parts = chunk_text_sliding(
        t,
        tokenizer_model_id="bert-base-uncased",
        chunk_size_tokens=512,
        overlap_tokens=80,
    )
    assert len(parts) == 1
    assert parts[0][0] in t


def test_chunk_long_text_multiple() -> None:
    t = ("word " * 2000).strip()
    parts = chunk_text_sliding(
        t,
        tokenizer_model_id="bert-base-uncased",
        chunk_size_tokens=64,
        overlap_tokens=8,
    )
    assert len(parts) >= 2


def test_normalized_to_chunks() -> None:
    n = NormalizedDocument(
        source_url="https://groww.in/mutual-funds/z",
        final_url="https://groww.in/mutual-funds/z",
        fetched_at=datetime.now(timezone.utc),
        content_hash="deadbeef",
        mime_type="text/html",
        text=("Exit load 1%. " * 50).strip(),
        manifest_document_type="scheme_page",
        amc_id="hdfc",
        scheme_name="Z",
    )
    chunks = normalized_to_chunks(
        n,
        tokenizer_model_id="bert-base-uncased",
        chunk_size_tokens=32,
        overlap_tokens=4,
    )
    assert len(chunks) >= 1
    assert chunks[0].source_url == "https://groww.in/mutual-funds/z"
    assert chunks[0].doc_id == doc_id_for(n)
