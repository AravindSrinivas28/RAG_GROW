"""Phase 3a: token-aware chunking (Hugging Face tokenizer) per chunking-embedding-architecture.md §2."""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from pydantic import BaseModel, Field
from transformers import AutoTokenizer
from transformers.tokenization_utils_base import PreTrainedTokenizerBase

from m1_rag.scrape import NormalizedDocument


def doc_id_for(norm: NormalizedDocument) -> str:
    """Stable id for a logical document (URL + type)."""
    raw = f"{norm.source_url}|{norm.manifest_document_type}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ChunkRecord(BaseModel):
    """One searchable segment with citation metadata."""

    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    source_url: str
    final_url: str
    content_hash: str
    manifest_document_type: str
    amc_id: str | None = None
    scheme_name: str | None = None
    category: str | None = None
    fetched_at_iso: str = Field(description="Parent document fetch time ISO8601")


def normalize_unicode(text: str) -> str:
    t = unicodedata.normalize("NFC", text)
    return "\n".join(line.rstrip() for line in t.splitlines()).strip()


@lru_cache(maxsize=8)
def _tokenizer_for(model_id: str) -> PreTrainedTokenizerBase:
    return AutoTokenizer.from_pretrained(model_id, use_fast=True)


def chunk_text_sliding(
    text: str,
    *,
    tokenizer_model_id: str,
    chunk_size_tokens: int,
    overlap_tokens: int,
) -> list[tuple[str, int, int]]:
    """
    Split text into overlapping token windows. Returns (chunk_text, start_char, end_char).
    Char spans follow the tokenizer's offset mapping into the normalized string.
    """
    if chunk_size_tokens <= 0:
        raise ValueError("chunk_size_tokens must be positive")
    if overlap_tokens >= chunk_size_tokens:
        overlap_tokens = max(0, chunk_size_tokens // 4)

    tok = _tokenizer_for(tokenizer_model_id)
    full = normalize_unicode(text)
    if not full:
        return []

    enc = tok(
        full,
        add_special_tokens=False,
        return_offsets_mapping=True,
        truncation=False,
    )
    input_ids = enc["input_ids"]
    offsets = enc["offset_mapping"]
    if not input_ids:
        return []

    if len(input_ids) <= chunk_size_tokens:
        return [(full, 0, len(full))]

    out: list[tuple[str, int, int]] = []
    step = max(1, chunk_size_tokens - overlap_tokens)
    start = 0
    n = len(input_ids)

    while start < n:
        end = min(start + chunk_size_tokens, n)
        char_start = int(offsets[start][0])
        char_end = int(offsets[end - 1][1])
        chunk_body = full[char_start:char_end]
        out.append((chunk_body.strip(), char_start, char_end))
        if end >= n:
            break
        start += step

    return out


def normalized_to_chunks(
    norm: NormalizedDocument,
    *,
    tokenizer_model_id: str,
    chunk_size_tokens: int,
    overlap_tokens: int,
) -> list[ChunkRecord]:
    """Build ChunkRecord list from a NormalizedDocument."""
    doc_id = doc_id_for(norm)
    raw_text = norm.text or ""
    pieces = chunk_text_sliding(
        raw_text,
        tokenizer_model_id=tokenizer_model_id,
        chunk_size_tokens=chunk_size_tokens,
        overlap_tokens=overlap_tokens,
    )
    fetched = norm.fetched_at.isoformat()
    out: list[ChunkRecord] = []
    for i, (txt, sc, ec) in enumerate(pieces):
        if not txt.strip():
            continue
        cid = f"{doc_id}:{i}"
        out.append(
            ChunkRecord(
                chunk_id=cid,
                doc_id=doc_id,
                chunk_index=i,
                text=txt,
                start_char=sc,
                end_char=ec,
                source_url=norm.source_url,
                final_url=norm.final_url,
                content_hash=norm.content_hash,
                manifest_document_type=norm.manifest_document_type,
                amc_id=norm.amc_id,
                scheme_name=norm.scheme_name,
                category=norm.category,
                fetched_at_iso=fetched,
            )
        )
    return out
