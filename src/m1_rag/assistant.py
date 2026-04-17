"""Phase 6–7: orchestrate router → retrieve → generate (or refusal)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from m1_rag.generation import GroundedAnswer, generate_grounded_answer
from m1_rag.prompts.templates import (
    ABSTENTION_LOW_CONTEXT_TEXT,
    EDUCATIONAL_URL_AMFI,
    EDUCATIONAL_URL_SEBI,
    REFUSAL_ADVISORY_TEXT,
    REFUSAL_PII_TEXT,
)
from m1_rag.retrieval import RetrievedChunk, RetrievalResult, retrieve
from m1_rag.router import RouteClass, classify_route
from m1_rag.settings import AppSettings


def footer_line(last_updated_iso_date: str) -> str:
    """Problem-statement footer."""
    d = (last_updated_iso_date or "").strip()
    if d:
        return f"Last updated from sources: {d}"
    return "Last updated from sources: (date unavailable)"


@dataclass
class AssistantTurnResult:
    """One assistant reply for API / UI."""

    answer_text: str
    citation_url: str
    last_updated: str
    footer_line: str
    refusal: bool
    route: str
    abstain: bool
    abstain_reason: str | None = None
    retrieval: dict[str, Any] | None = None
    model_id: str | None = None


def _chunks_summary(chunks: list[RetrievedChunk]) -> dict[str, Any]:
    return {
        "n_chunks": len(chunks),
        "top_source_url": chunks[0].source_url if chunks else None,
        "top_distance": chunks[0].distance if chunks else None,
    }


def run_assistant_turn(
    app: AppSettings,
    user_message: str,
    *,
    retrieve_fn: Callable[..., RetrievalResult] | None = None,
    generate_fn: Callable[..., GroundedAnswer] | None = None,
) -> AssistantTurnResult:
    """
    Full path: preprocess routing → (optional) retrieve → generate or refusal templates.

    Dependency injection for tests: ``retrieve_fn``, ``generate_fn``.
    """
    route = classify_route(user_message)

    if route == RouteClass.ADVISORY:
        return AssistantTurnResult(
            answer_text=REFUSAL_ADVISORY_TEXT,
            citation_url=EDUCATIONAL_URL_AMFI,
            last_updated="",
            footer_line=footer_line(""),
            refusal=True,
            route=route.value,
            abstain=False,
        )

    if route == RouteClass.PII:
        return AssistantTurnResult(
            answer_text=REFUSAL_PII_TEXT,
            citation_url=EDUCATIONAL_URL_SEBI,
            last_updated="",
            footer_line=footer_line(""),
            refusal=True,
            route=route.value,
            abstain=False,
        )

    rfn = retrieve_fn or retrieve
    ret: RetrievalResult = rfn(app, user_message)

    if not ret.chunks:
        return AssistantTurnResult(
            answer_text=ABSTENTION_LOW_CONTEXT_TEXT,
            citation_url=EDUCATIONAL_URL_AMFI,
            last_updated="",
            footer_line=footer_line(""),
            refusal=False,
            route=route.value,
            abstain=True,
            abstain_reason=ret.abstain_reason or "no_chunks",
            retrieval=_chunks_summary(ret.chunks),
        )

    # Distance-based abstention: chunks present but similarity too weak
    if ret.abstain and ret.abstain_reason:
        return AssistantTurnResult(
            answer_text=(
                f"{ABSTENTION_LOW_CONTEXT_TEXT} (Retrieval confidence was low for this query.)"
            ),
            citation_url=ret.chunks[0].source_url or EDUCATIONAL_URL_AMFI,
            last_updated="",
            footer_line=footer_line(""),
            refusal=False,
            route=route.value,
            abstain=True,
            abstain_reason=ret.abstain_reason,
            retrieval=_chunks_summary(ret.chunks),
        )

    gfn = generate_fn or generate_grounded_answer
    gen = gfn(app, user_query=user_message, chunks=ret.chunks)
    lu = gen.last_updated
    return AssistantTurnResult(
        answer_text=gen.answer_text,
        citation_url=gen.citation_url,
        last_updated=lu,
        footer_line=footer_line(lu),
        refusal=False,
        route=route.value,
        abstain=False,
        retrieval=_chunks_summary(ret.chunks),
        model_id=gen.model_id,
    )
