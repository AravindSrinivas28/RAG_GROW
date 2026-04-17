"""Phase 9: structured logging and safe telemetry (rag-architecture.md §10.1)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

from m1_rag.assistant import AssistantTurnResult
from m1_rag.settings import YamlConfig

_LOG = logging.getLogger("m1_rag.chat")


def hash_query(text: str) -> str:
    """SHA-256 prefix of UTF-8 query — log this instead of raw user text."""
    h = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return h[:16]


def configure_logging(yaml_cfg: YamlConfig | None = None) -> None:
    """Idempotent logging setup for API and CLIs."""
    obs = yaml_cfg.observability if yaml_cfg is not None else None
    level_name = (os.environ.get("M1_RAG_LOG_LEVEL") or (obs.log_level if obs else "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=level, format="%(message)s")
    for name in ("m1_rag", "m1_rag.chat"):
        logging.getLogger(name).setLevel(level)


def log_chat_turn(
    *,
    thread_id: str,
    latency_ms: float,
    turn: AssistantTurnResult,
    query_hash: str,
) -> None:
    """
    One JSON line per chat turn: latency, refusal/abstain flags, route, retrieval scores.

    Does **not** log raw user content (use ``query_hash`` from :func:`hash_query`).
    """
    top_d: float | None = None
    n_chunks: int | None = None
    if turn.retrieval:
        top_d = turn.retrieval.get("top_distance")
        if isinstance(top_d, (int, float)):
            top_d = float(top_d)
        else:
            top_d = None
        nc = turn.retrieval.get("n_chunks")
        if isinstance(nc, int):
            n_chunks = nc

    payload: dict[str, Any] = {
        "event": "chat_turn",
        "thread_id": thread_id,
        "query_hash": query_hash,
        "latency_ms": round(latency_ms, 2),
        "refusal": turn.refusal,
        "abstain": turn.abstain,
        "route": turn.route,
        "top_distance": top_d,
        "n_chunks": n_chunks,
        "model_id": turn.model_id,
    }
    if turn.abstain_reason:
        payload["abstain_reason"] = turn.abstain_reason

    _LOG.info(json.dumps(payload, separators=(",", ":")))


def citation_host_allowed(url: str, allowed_hosts: list[str]) -> bool:
    """Whether ``url`` netloc matches or is a subdomain of an allowed host (golden / policy checks)."""
    from urllib.parse import urlparse

    u = urlparse(url.strip())
    if u.scheme not in ("http", "https") or not u.netloc:
        return False
    host = u.netloc.lower().split(":")[0]
    for h in allowed_hosts:
        h = h.lower().strip()
        if not h:
            continue
        if host == h or host.endswith("." + h):
            return True
    return False
