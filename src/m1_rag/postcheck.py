"""Phase 6: post-checks on model output (rag-architecture.md §6)."""

from __future__ import annotations

import re
from urllib.parse import urlparse


def count_sentences(text: str) -> int:
    """Rough sentence count for English prose (max-3-sentence policy)."""
    t = text.strip()
    if not t:
        return 0
    # Split on sentence-ending punctuation followed by space or end.
    parts = re.split(r"(?<=[.!?])\s+", t)
    return len([p for p in parts if p.strip()])


def truncate_to_sentences(text: str, max_sentences: int = 3) -> str:
    if max_sentences <= 0:
        return ""
    t = text.strip()
    if not t:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", t)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        out.append(p)
        if len(out) >= max_sentences:
            break
    return " ".join(out)


def is_allowed_http_url(url: str) -> bool:
    try:
        p = urlparse(url.strip())
    except Exception:
        return False
    return p.scheme in ("http", "https") and bool(p.netloc)


def pick_allowed_citation(requested: str, allowed_urls: set[str]) -> str | None:
    """If model citation is in the allow-list, use it; else None."""
    u = requested.strip()
    if u in allowed_urls:
        return u
    return None
