"""Phase 8 minimal UI (served from FastAPI)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from m1_rag.api import app


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
        from m1_rag.assistant import AssistantTurnResult

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


def test_root_serves_minimal_ui(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    body = r.text
    assert "Facts-only. No investment advice." in body
    assert "minimum SIP" in body.lower() or "Minimum SIP" in body


def test_static_assets(client: TestClient) -> None:
    r = client.get("/static/styles.css")
    assert r.status_code == 200
    assert "disclaimer" in r.text or ".top-bar" in r.text
