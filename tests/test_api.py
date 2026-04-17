"""Phase 7 API (TestClient + mocked assistant)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from m1_rag.api import app
from m1_rag.assistant import AssistantTurnResult


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg = tmp_path / "cfg.yaml"
    db = tmp_path / "threads.sqlite"
    cfg.write_text(
        f"""api:
  thread_store_path: "{db.as_posix()}"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("M1_RAG_CONFIG_FILE", str(cfg))

    def fake_turn(_app, user_message: str, **_k):
        return AssistantTurnResult(
            answer_text="ok",
            citation_url="https://example.com",
            last_updated="2025-01-01",
            footer_line="Last updated from sources: 2025-01-01",
            refusal=False,
            route="factual",
            abstain=False,
            model_id="test",
        )

    monkeypatch.setattr("m1_rag.api.run_assistant_turn", fake_turn)

    with TestClient(app) as c:
        yield c


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_thread_and_message(client: TestClient) -> None:
    r = client.post("/threads")
    assert r.status_code == 200
    tid = r.json()["thread_id"]
    assert tid

    r2 = client.post(f"/threads/{tid}/messages", json={"content": "What is the expense ratio?"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["thread_id"] == tid
    assert body["assistant"]["answer_text"] == "ok"
    assert body["assistant"]["citation_url"] == "https://example.com"
    assert body["assistant"]["last_updated"] == "2025-01-01"


def test_unknown_thread_404(client: TestClient) -> None:
    r = client.post("/threads/bad-id/messages", json={"content": "hi"})
    assert r.status_code == 404
