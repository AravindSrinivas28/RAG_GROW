"""Phase 6: grounded LLM generation (JSON output + validation)."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field, SecretStr

from m1_rag.postcheck import count_sentences, is_allowed_http_url, pick_allowed_citation, truncate_to_sentences
from m1_rag.prompts.templates import GENERATION_JSON_INSTRUCTION
from m1_rag.retrieval import RetrievedChunk
from m1_rag.settings import AppSettings, LlmSection, SecretsSettings


def _effective_llm_key(secrets: SecretsSettings) -> SecretStr | None:
    """Prefer OpenRouter key when set; otherwise generic LLM key (e.g. OpenAI)."""
    return secrets.openrouter_api_key or secrets.llm_api_key


class GroundedAnswer(BaseModel):
    """Structured assistant payload after post-checks."""

    answer_text: str
    citation_url: str = ""
    last_updated: str = ""
    model_id: str = ""


def _format_context_block(ch: RetrievedChunk, index: int) -> str:
    meta = ch.metadata or {}
    fetched = str(meta.get("fetched_at", "") or "")
    return (
        f"--- CONTEXT {index + 1} ---\n"
        f"source_url: {ch.source_url}\n"
        f"fetched_at: {fetched}\n"
        f"text:\n{ch.text}\n"
    )


def _parse_json_object(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group())
        raise


def _normalize_last_updated(s: str, fallback_iso: str) -> str:
    s = (s or "").strip()
    if not s and fallback_iso:
        try:
            dt = datetime.fromisoformat(fallback_iso.replace("Z", "+00:00"))
            return dt.date().isoformat()
        except ValueError:
            try:
                return date.fromisoformat(fallback_iso[:10]).isoformat()
            except ValueError:
                return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    return s


def generate_grounded_answer(
    app: AppSettings,
    *,
    user_query: str,
    chunks: list[RetrievedChunk],
) -> GroundedAnswer:
    """
    Call the chat LLM with retrieved chunks; enforce citation URL allow-list and sentence cap.

    Requires ``M1_RAG_OPENROUTER_API_KEY`` or ``M1_RAG_LLM_API_KEY`` for OpenAI-compatible APIs.
    """
    if not chunks:
        raise ValueError("chunks required for generation")

    key = _effective_llm_key(app.secrets)
    if key is None:
        raise RuntimeError(
            "No LLM API key: set M1_RAG_OPENROUTER_API_KEY or M1_RAG_LLM_API_KEY",
        )

    llm: LlmSection = app.yaml.llm
    allowed = {c.source_url for c in chunks if c.source_url}
    if not allowed:
        raise ValueError("retrieved chunks have no source_url")

    context_blob = "\n".join(_format_context_block(c, i) for i, c in enumerate(chunks))
    user_prompt = f"USER QUESTION:\n{user_query}\n\n{context_blob}"

    kwargs: dict = {"api_key": key.get_secret_value()}
    if llm.api_base:
        kwargs["base_url"] = str(llm.api_base).rstrip("/")

    headers: dict[str, str] = {}
    base = (llm.api_base or "").lower()
    if "openrouter.ai" in base:
        ref = (llm.http_referer or "").strip() or "http://127.0.0.1"
        headers["HTTP-Referer"] = ref
        headers["X-Title"] = (llm.app_title or "M1 RAG").strip()
    if headers:
        kwargs["default_headers"] = headers

    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=llm.model,
        temperature=llm.temperature,
        max_tokens=llm.max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": GENERATION_JSON_INSTRUCTION},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    data = _parse_json_object(raw)

    answer_text = str(data.get("answer_text", "")).strip()
    citation = str(data.get("citation_url", "")).strip()
    last_up = str(data.get("last_updated", "")).strip()

    top = chunks[0]
    meta0 = top.metadata or {}
    fallback_fetch = str(meta0.get("fetched_at", "") or "")

    fixed_cite = pick_allowed_citation(citation, allowed)
    if fixed_cite is None:
        if is_allowed_http_url(citation):
            fixed_cite = top.source_url
        else:
            fixed_cite = top.source_url

    if count_sentences(answer_text) > 3:
        answer_text = truncate_to_sentences(answer_text, 3)

    last_norm = _normalize_last_updated(last_up, fallback_fetch)
    if not last_norm and fallback_fetch:
        last_norm = _normalize_last_updated("", fallback_fetch)

    return GroundedAnswer(
        answer_text=answer_text,
        citation_url=fixed_cite,
        last_updated=last_norm,
        model_id=llm.model,
    )
