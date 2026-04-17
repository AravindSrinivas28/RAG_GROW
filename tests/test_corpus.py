"""Phase 1 corpus manifest."""

from pathlib import Path

from m1_rag.corpus import (
    iter_corpus_documents,
    load_corpus_manifest,
    manifest_path_from_config,
    validate_urls_against_allowlist,
)
from m1_rag.settings import AppSettings, load_yaml_config


def test_manifest_loads_and_counts() -> None:
    root = Path(__file__).resolve().parents[1]
    m = load_corpus_manifest(root / "phases" / "phase_1_corpus" / "corpus_manifest.yaml")
    assert m.manifest_version == "1.0"
    assert len(m.seeds) == 5
    assert len(m.entries) == 20
    docs = iter_corpus_documents(m)
    assert len(docs) == 25
    urls = [str(d.url) for d in docs]
    assert len(urls) == len(set(urls))


def test_manifest_matches_allowlist() -> None:
    root = Path(__file__).resolve().parents[1]
    yaml_cfg = load_yaml_config(root / "config" / "default.yaml")
    m = load_corpus_manifest(root / "phases" / "phase_1_corpus" / "corpus_manifest.yaml")
    urls = [str(d.url) for d in iter_corpus_documents(m)]
    errs = validate_urls_against_allowlist(
        urls,
        allowed_hosts=yaml_cfg.allowlist.hosts,
        path_prefixes_by_host=yaml_cfg.allowlist.path_prefixes_by_host,
    )
    assert errs == [], errs


def test_reject_disallowed_host() -> None:
    errs = validate_urls_against_allowlist(
        ["https://example.com/page"],
        allowed_hosts=["groww.in"],
        path_prefixes_by_host={},
    )
    assert any("not allowed" in e for e in errs)


def test_groww_path_prefix_enforced() -> None:
    errs = validate_urls_against_allowlist(
        ["https://groww.in/stocks/something"],
        allowed_hosts=["groww.in"],
        path_prefixes_by_host={"groww.in": ["/mutual-funds/"]},
    )
    assert len(errs) == 1


def test_manifest_path_from_config() -> None:
    s = AppSettings.load()
    p = manifest_path_from_config(s.yaml.corpus.manifest_path)
    assert p.name == "corpus_manifest.yaml"
    assert p.is_file()
