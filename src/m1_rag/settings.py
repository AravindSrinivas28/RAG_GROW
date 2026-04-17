"""Load YAML configuration (data) and environment-backed secrets (Phase 0 foundation)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSection(BaseModel):
    name: str = "m1-rag"
    env: str = "development"


class AllowlistSection(BaseModel):
    hosts: list[str] = Field(default_factory=list)
    path_prefixes_by_host: dict[str, list[str]] = Field(default_factory=dict)


class ChunkingSection(BaseModel):
    tokenizer_model_id: str = "BAAI/bge-small-en-v1.5"
    chunk_size_tokens: int = 512
    overlap_tokens: int = 80


class EmbeddingSection(BaseModel):
    model_id: str = "BAAI/bge-small-en-v1.5"
    model_version: str = "1"
    dimensions: int = 384
    batch_size: int = 16
    device: str | None = Field(
        default=None,
        description="sentence-transformers device, e.g. cpu or cuda:0; omit for library default.",
    )


class IngestSection(BaseModel):
    state_path: str = "data/ingest_state.json"


class VectorDbSection(BaseModel):
    backend: str = "chroma"
    collection_name: str = "m1_rag_corpus"
    persist_directory: str = "./data/vector_store"


class RetrievalSection(BaseModel):
    top_k: int = 8
    max_distance: float | None = Field(
        default=None,
        description="If set, abstain when the best Chroma distance exceeds this (lower = more similar).",
    )


class LlmSection(BaseModel):
    """Phase 6: OpenAI-compatible chat model for grounded JSON answers."""

    model: str = "openai/gpt-4o-mini"
    temperature: float = 0.2
    max_tokens: int = 512
    api_base: str | None = Field(
        default="https://openrouter.ai/api/v1",
        description="Base URL: OpenRouter, OpenAI, Azure OpenAI, or other OpenAI-compatible APIs.",
    )
    http_referer: str | None = Field(
        default=None,
        description="Optional HTTP-Referer for OpenRouter (site URL). Defaults to a localhost placeholder.",
    )
    app_title: str | None = Field(
        default="M1 RAG",
        description="Optional X-Title header for OpenRouter.",
    )


class ApiSection(BaseModel):
    """Phase 7: HTTP API defaults (thread store path is data, not secret)."""

    thread_store_path: str = "data/threads.sqlite"


class ObservabilitySection(BaseModel):
    """Phase 9: logging defaults (see ``observability`` module)."""

    log_level: str = "INFO"
    golden_cases_path: str = "phases/phase_9_quality/golden_cases.yaml"


class CorpusSection(BaseModel):
    manifest_path: str = "phases/phase_1_corpus/corpus_manifest.yaml"
    max_urls_per_ingest_run: int = 40


class ScrapeSection(BaseModel):
    user_agent: str = "M1RAG/0.1 (facts-only mutual fund corpus)"
    delay_seconds: float = 1.0
    timeout_seconds: float = 45.0
    max_retries: int = 2
    respect_robots_txt: bool = True
    store_raw_snapshots: bool = False
    raw_snapshots_dir: str = "data/raw_snapshots"


class YamlConfig(BaseModel):
    """Configuration stored as data (committed YAML)."""

    app: AppSection = Field(default_factory=AppSection)
    allowlist: AllowlistSection = Field(default_factory=AllowlistSection)
    corpus: CorpusSection = Field(default_factory=CorpusSection)
    scrape: ScrapeSection = Field(default_factory=ScrapeSection)
    chunking: ChunkingSection = Field(default_factory=ChunkingSection)
    embedding: EmbeddingSection = Field(default_factory=EmbeddingSection)
    ingest: IngestSection = Field(default_factory=IngestSection)
    vector_db: VectorDbSection = Field(default_factory=VectorDbSection)
    retrieval: RetrievalSection = Field(default_factory=RetrievalSection)
    llm: LlmSection = Field(default_factory=LlmSection)
    api: ApiSection = Field(default_factory=ApiSection)
    observability: ObservabilitySection = Field(default_factory=ObservabilitySection)


def _project_root() -> Path:
    """src/m1_rag/settings.py -> project root."""
    return Path(__file__).resolve().parents[2]


def _load_yaml_raw(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def load_yaml_config(config_file: Path | None = None) -> YamlConfig:
    """Load committed defaults from YAML."""
    path = config_file or (_project_root() / "config" / "default.yaml")
    raw = _load_yaml_raw(path)
    return YamlConfig.model_validate(raw)


class SecretsSettings(BaseSettings):
    """Secrets and runtime overrides — never commit real values."""

    model_config = SettingsConfigDict(
        env_prefix="M1_RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    embedding_api_key: SecretStr | None = None
    llm_api_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = Field(
        default=None,
        description="OpenRouter API key; used for chat when set (else M1_RAG_LLM_API_KEY).",
    )
    api_host: str | None = Field(
        default=None,
        description="Bind address for m1-rag-api (env: M1_RAG_API_HOST).",
    )
    api_port: int | None = Field(
        default=None,
        description="Bind port for m1-rag-api (env: M1_RAG_API_PORT).",
    )
    config_file: str | None = Field(
        default=None,
        description="Optional path to YAML config; default config/default.yaml",
    )
    app_env: str | None = None


class AppSettings(BaseModel):
    """Combined view: YAML data + secrets reference."""

    yaml: YamlConfig
    secrets: SecretsSettings

    @classmethod
    def load(cls, config_file: Path | None = None) -> AppSettings:
        secrets = SecretsSettings()
        path: Path | None = Path(secrets.config_file).expanduser() if secrets.config_file else config_file
        yaml_cfg = load_yaml_config(path)
        if secrets.app_env:
            yaml_cfg.app.env = secrets.app_env
        return cls(yaml=yaml_cfg, secrets=secrets)
