"""Phase 1: load and validate the versioned corpus manifest (YAML)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, HttpUrl


class SeedItem(BaseModel):
    """AMC hub seed URL."""

    amc_id: str = Field(..., description="Short AMC key, e.g. hdfc")
    url: HttpUrl


class ManifestEntry(BaseModel):
    """Scheme page or regulatory URL with metadata for filters and citations."""

    url: HttpUrl
    amc_id: str | None = None
    scheme_name: str | None = None
    document_type: Literal["scheme_page", "regulatory"]
    category: str | None = Field(
        default=None,
        description="Rough scheme category for diversity tracking (e.g. elss, large_cap)",
    )


class CorpusManifest(BaseModel):
    """Root schema for `corpus_manifest.yaml`."""

    manifest_version: str
    description: str | None = None
    seeds: list[SeedItem]
    entries: list[ManifestEntry]


class CorpusDocument(BaseModel):
    """Unified row for ingestion (hubs + scheme pages + regulatory)."""

    url: HttpUrl
    amc_id: str | None
    scheme_name: str | None
    document_type: Literal["hub", "scheme_page", "regulatory"]
    category: str | None
    origin: Literal["seed", "entry"]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def manifest_path_from_config(relative_path: str) -> Path:
    """Resolve corpus.manifest_path relative to project root."""
    p = Path(relative_path)
    if p.is_absolute():
        return p
    return _project_root() / p


def load_corpus_manifest(path: Path | None = None) -> CorpusManifest:
    """Load and validate the corpus manifest from YAML."""
    resolved = path or manifest_path_from_config("phases/phase_1_corpus/corpus_manifest.yaml")
    with resolved.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError("corpus manifest must be a YAML mapping")
    return CorpusManifest.model_validate(raw)


def iter_corpus_documents(manifest: CorpusManifest) -> list[CorpusDocument]:
    """Merge seeds (as hubs) and entries into one deduped list (first occurrence wins)."""
    seen: set[str] = set()
    out: list[CorpusDocument] = []

    for s in manifest.seeds:
        key = str(s.url)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            CorpusDocument(
                url=s.url,
                amc_id=s.amc_id,
                scheme_name=None,
                document_type="hub",
                category=None,
                origin="seed",
            )
        )

    for e in manifest.entries:
        key = str(e.url)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            CorpusDocument(
                url=e.url,
                amc_id=e.amc_id,
                scheme_name=e.scheme_name,
                document_type=e.document_type,
                category=e.category,
                origin="entry",
            )
        )

    return out


def all_corpus_urls(manifest: CorpusManifest) -> list[str]:
    """Ordered unique URLs for the scraper."""
    return [str(d.url) for d in iter_corpus_documents(manifest)]


def _host_matches_allowed(hostname: str | None, allowed_hosts: list[str]) -> bool:
    if not hostname:
        return False
    h = hostname.lower()
    for a in allowed_hosts:
        al = a.lower()
        if h == al or h == f"www.{al}" or f"www.{h}" == al:
            return True
    return False


def _prefixes_for_host(hostname: str | None, path_prefixes_by_host: dict[str, list[str]]) -> list[str] | None:
    """Return prefix list for this host key, or None if not restricted."""
    if not hostname:
        return None
    h = hostname.lower()
    for key, prefs in path_prefixes_by_host.items():
        kl = key.lower()
        if h == kl or h == f"www.{kl}" or f"www.{h}" == kl:
            return prefs
    return None


def validate_urls_against_allowlist(
    urls: list[str],
    *,
    allowed_hosts: list[str],
    path_prefixes_by_host: dict[str, list[str]],
) -> list[str]:
    """
    Return a list of human-readable errors for URLs outside the allowlist.

    If path_prefixes_by_host has no entry for a host, all paths on that host are allowed.
    """
    from urllib.parse import urlparse

    errors: list[str] = []
    for u in urls:
        parsed = urlparse(u)
        host = parsed.hostname
        if not _host_matches_allowed(host, allowed_hosts):
            errors.append(f"host not allowed: {host!r} ({u})")
            continue
        prefixes = _prefixes_for_host(host, path_prefixes_by_host)
        if not prefixes:
            continue
        path = parsed.path or "/"
        if not any(path.startswith(p) for p in prefixes):
            errors.append(f"path not under allowed prefixes for {host}: {u}")
    return errors
