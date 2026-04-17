"""Phase 9 observability helpers."""

import pytest

from m1_rag.assistant import AssistantTurnResult
from m1_rag.observability import hash_query, log_chat_turn


def test_hash_query_stable() -> None:
    assert hash_query("hello") == hash_query("hello")
    assert hash_query("hello") != hash_query("world")


def test_log_chat_turn_json(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="m1_rag.chat")
    turn = AssistantTurnResult(
        answer_text="a",
        citation_url="https://x",
        last_updated="",
        footer_line="",
        refusal=False,
        route="factual",
        abstain=False,
        retrieval={"n_chunks": 3, "top_distance": 0.12},
        model_id="m",
    )
    log_chat_turn(
        thread_id="t1",
        latency_ms=42.2,
        turn=turn,
        query_hash="abc123",
    )
    assert "chat_turn" in caplog.text
    assert "t1" in caplog.text
    assert "abc123" in caplog.text
    assert "0.12" in caplog.text
