"""Phase 7: FastAPI — threads + messages (rag-architecture.md §9)."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.requests import Request

from m1_rag.assistant import AssistantTurnResult, run_assistant_turn
from m1_rag.observability import configure_logging, hash_query, log_chat_turn
from m1_rag.settings import AppSettings
from m1_rag.thread_store import ThreadStore


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _thread_db_path(settings: AppSettings) -> Path:
    p = Path(settings.yaml.api.thread_store_path)
    if not p.is_absolute():
        p = _project_root() / p
    return p


def _ui_static_dir() -> Path:
    """Phase 8 minimal UI assets (shipped inside the ``m1_rag`` package)."""
    return Path(__file__).resolve().parent / "static"


class CreateThreadResponse(BaseModel):
    thread_id: str = Field(description="Opaque conversation id (UUID).")


class PostMessageBody(BaseModel):
    content: str = Field(min_length=1, description="User message text (no PII).")


class AssistantPayload(BaseModel):
    answer_text: str
    citation_url: str = ""
    last_updated: str = ""
    footer_line: str = ""
    refusal: bool = False
    abstain: bool = False
    abstain_reason: str | None = None
    route: str = ""
    model_id: str | None = None


class PostMessageResponse(BaseModel):
    thread_id: str
    assistant: AssistantPayload


def _turn_to_payload(t: AssistantTurnResult) -> AssistantPayload:
    return AssistantPayload(
        answer_text=t.answer_text,
        citation_url=t.citation_url,
        last_updated=t.last_updated,
        footer_line=t.footer_line,
        refusal=t.refusal,
        abstain=t.abstain,
        abstain_reason=t.abstain_reason,
        route=t.route,
        model_id=t.model_id,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = AppSettings.load()
    configure_logging(settings.yaml)
    store = ThreadStore(_thread_db_path(settings))
    app.state.settings = settings
    app.state.thread_store = store
    yield
    store.close()


app = FastAPI(
    title="M1 RAG",
    description="Facts-only mutual fund FAQ API (threads + grounded replies).",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_static = _ui_static_dir()
if _static.is_dir():
    app.mount(
        "/static",
        StaticFiles(directory=str(_static)),
        name="static",
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def serve_minimal_ui() -> FileResponse:
    """Phase 8: single-page chat (``rag-architecture.md`` §2.3 Phase 8, §9.2)."""
    index = _ui_static_dir() / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Minimal UI not installed (missing index.html).")
    return FileResponse(index)


def get_settings(request: Request) -> AppSettings:
    return request.app.state.settings


def get_store(request: Request) -> ThreadStore:
    return request.app.state.thread_store


@app.post("/threads", response_model=CreateThreadResponse)
def create_thread(store: ThreadStore = Depends(get_store)) -> CreateThreadResponse:
    tid = store.create_thread()
    return CreateThreadResponse(thread_id=tid)


@app.post("/threads/{thread_id}/messages", response_model=PostMessageResponse)
def post_message(
    thread_id: str,
    body: PostMessageBody,
    settings: AppSettings = Depends(get_settings),
    store: ThreadStore = Depends(get_store),
) -> PostMessageResponse:
    if not store.has_thread(thread_id):
        raise HTTPException(status_code=404, detail="thread not found")

    store.append_message(thread_id, role="user", content=body.content)

    qhash = hash_query(body.content)
    t0 = time.perf_counter()
    turn: AssistantTurnResult | None = None
    try:
        turn = run_assistant_turn(settings, body.content)
    except RuntimeError as e:
        err = str(e)
        if "LLM API key" in err or "M1_RAG_LLM_API_KEY" in err:
            raise HTTPException(
                status_code=503,
                detail=(
                    "LLM is not configured: set M1_RAG_OPENROUTER_API_KEY or M1_RAG_LLM_API_KEY "
                    "(OpenRouter is the default; see config llm.api_base)."
                ),
            ) from e
        raise
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if turn is not None:
            log_chat_turn(
                thread_id=thread_id,
                latency_ms=elapsed_ms,
                turn=turn,
                query_hash=qhash,
            )

    assert turn is not None
    store.append_message(
        thread_id,
        role="assistant",
        content=turn.answer_text,
        citation_url=turn.citation_url,
        last_updated=turn.last_updated,
        footer_line=turn.footer_line,
        refusal=turn.refusal,
        abstain=turn.abstain,
        route=turn.route,
        abstain_reason=turn.abstain_reason,
        model_id=turn.model_id,
    )

    return PostMessageResponse(thread_id=thread_id, assistant=_turn_to_payload(turn))


def run() -> None:
    """CLI entry: ``python -m m1_rag.api`` or ``m1-rag-api``.

    Host/port: ``M1_RAG_API_HOST`` / ``M1_RAG_API_PORT`` (also read from ``.env`` via
    :class:`m1_rag.settings.SecretsSettings`). Defaults: ``127.0.0.1:8000``.
    If another app uses 8000, set e.g. ``M1_RAG_API_PORT=8765``.

    **Cloud (e.g. Render):** platforms set ``PORT``; when present we bind that
    port and default host to ``0.0.0.0`` unless ``M1_RAG_API_HOST`` is set.
    """
    import os

    import uvicorn

    from m1_rag.settings import SecretsSettings

    s = SecretsSettings()
    port_env = os.environ.get("PORT")
    port = s.api_port
    if port is None and port_env is not None:
        port = int(port_env)
    if port is None:
        port = 8000

    host = (s.api_host or "").strip()
    if not host:
        host = "0.0.0.0" if port_env is not None else "127.0.0.1"

    uvicorn.run("m1_rag.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
