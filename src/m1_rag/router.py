"""Phase 6: lightweight query router (rules + patterns; rag-architecture.md §7)."""

from __future__ import annotations

import re
from enum import Enum


class RouteClass(str, Enum):
    """High-level routing for a user turn."""

    FACTUAL = "factual"
    """In-scope factual query → retrieval + grounded generation."""

    ADVISORY = "advisory"
    """Advisory or comparative → refusal path (no retrieval)."""

    PII = "pii"
    """Sensitive / PII-seeking → refusal; do not echo secrets."""


_PII = [
    re.compile(r"(?i)\b(pan|aadhaar|aadhar|passport)\b"),
    re.compile(r"(?i)\b(?:my\s+)?account\s+number\b"),
]

_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

_ADVISORY = [
    re.compile(r"(?i)\bshould\s+i\b"),
    re.compile(r"(?i)\bshall\s+i\b"),
    re.compile(r"(?i)\bmust\s+i\b"),
    re.compile(r"(?i)\bwhich\s+(?:fund|scheme)s?\s+(?:is|are)\s+(?:better|best|worst)\b"),
    re.compile(r"(?i)\b(?:better|worse)\s+than\b"),
    re.compile(r"(?i)\brecommend\b"),
    re.compile(r"(?i)\bbest\s+fund\b"),
    re.compile(r"(?i)\boutperform\b"),
    re.compile(r"(?i)\bbeat(?:ing)?\s+the\s+market\b"),
    re.compile(r"(?i)\bwhere\s+should\s+i\s+invest\b"),
    re.compile(r"(?i)\bwhich\s+(?:fund|scheme|one)\s+should\s+i\b"),
    re.compile(r"(?i)\b(?:buy|sell)\s+or\s+(?:buy|sell)\b"),
    re.compile(r"(?i)\bfund\s+vs\.?\s+fund\b"),
    re.compile(r"(?i)\bscheme\s+vs\.?\s+scheme\b"),
]


def classify_route(user_text: str) -> RouteClass:
    """
    Classify a single user message. Router runs before retrieval.

    Uses conservative keyword/pattern rules; extend with an LLM classifier later if needed.
    """
    t = (user_text or "").strip()
    if not t:
        return RouteClass.FACTUAL

    if _EMAIL.search(t):
        return RouteClass.PII
    for rx in _PII:
        if rx.search(t):
            return RouteClass.PII

    for rx in _ADVISORY:
        if rx.search(t):
            return RouteClass.ADVISORY

    return RouteClass.FACTUAL
