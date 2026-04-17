"""Phase 0: configuration and secrets wiring."""

from pathlib import Path

from m1_rag.settings import AppSettings, YamlConfig, load_yaml_config


def test_load_default_yaml() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = load_yaml_config(root / "config" / "default.yaml")
    assert isinstance(cfg, YamlConfig)
    assert "groww.in" in cfg.allowlist.hosts
    assert "www.sebi.gov.in" in cfg.allowlist.hosts
    assert cfg.corpus.manifest_path.endswith("corpus_manifest.yaml")
    assert cfg.scrape.user_agent
    assert cfg.scrape.delay_seconds >= 0
    assert cfg.chunking.chunk_size_tokens > 0
    assert cfg.ingest.state_path
    assert cfg.embedding.model_id
    assert cfg.retrieval.top_k > 0
    assert cfg.retrieval.max_distance is None
    assert cfg.llm.model
    assert cfg.llm.api_base and "openrouter" in cfg.llm.api_base
    assert cfg.api.thread_store_path
    assert cfg.observability.log_level


def test_app_settings_load() -> None:
    s = AppSettings.load()
    assert s.yaml.vector_db.collection_name == "m1_rag_corpus"
