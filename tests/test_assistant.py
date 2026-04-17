"""Assistant orchestration (mocked retrieval / generation)."""

from m1_rag.assistant import AssistantTurnResult, run_assistant_turn
from m1_rag.generation import GroundedAnswer
from m1_rag.retrieval import RetrievedChunk, RetrievalResult
from m1_rag.settings import AppSettings, SecretsSettings, YamlConfig


def _app() -> AppSettings:
    return AppSettings(yaml=YamlConfig.model_validate({}), secrets=SecretsSettings())


def test_advisory_refusal_no_retrieve() -> None:
    called: list[str] = []

    def fake_retrieve(*_a, **_k):
        called.append("retrieve")
        return RetrievalResult(query="q", chunks=[])

    r = run_assistant_turn(_app(), "Should I buy this fund?", retrieve_fn=fake_retrieve)
    assert r.refusal
    assert r.citation_url.startswith("http")
    assert not called


def test_factual_calls_generate() -> None:
    chunk = RetrievedChunk(
        chunk_id="c1",
        text="Minimum SIP is Rs 500.",
        source_url="https://groww.in/mutual-funds/x",
        metadata={"fetched_at": "2025-01-15T00:00:00+00:00"},
    )

    def fake_retrieve(*_a, **_k):
        return RetrievalResult(query="q", chunks=[chunk])

    def fake_gen(*_a, **_k):
        return GroundedAnswer(
            answer_text="The minimum SIP is Rs 500 per month.",
            citation_url="https://groww.in/mutual-funds/x",
            last_updated="2025-01-15",
            model_id="test",
        )

    r = run_assistant_turn(
        _app(),
        "What is the minimum SIP?",
        retrieve_fn=fake_retrieve,
        generate_fn=fake_gen,
    )
    assert not r.refusal
    assert "500" in r.answer_text
    assert "Last updated from sources:" in r.footer_line
