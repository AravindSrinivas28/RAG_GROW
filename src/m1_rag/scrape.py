"""Phase 2: scrape corpus URLs, normalize to text, compute content_hash (per architecture §3.2, §4.2)."""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura
from pydantic import BaseModel, Field
from pypdf import PdfReader

from m1_rag.corpus import (
    CorpusDocument,
    validate_urls_against_allowlist,
)
from m1_rag.settings import AllowlistSection, ScrapeSection, YamlConfig


class NormalizedDocument(BaseModel):
    """Payload for chunking (Phase 3). Matches §4.2 metadata needs."""

    source_url: str
    final_url: str
    fetched_at: datetime = Field(description="UTC timestamp when fetch completed")
    content_hash: str = Field(description="SHA-256 hex of normalized UTF-8 text")
    mime_type: str
    text: str
    manifest_document_type: Literal["hub", "scheme_page", "regulatory"]
    amc_id: str | None = None
    scheme_name: str | None = None
    category: str | None = None


@dataclass
class ScrapeResult:
    """One URL outcome; failures do not stop the batch."""

    source_url: str
    success: bool
    document: NormalizedDocument | None = None
    error: str | None = None


@dataclass
class RobotsCache:
    """One RobotFileParser per origin (scheme + netloc)."""

    _parsers: dict[str, RobotFileParser | None] = field(default_factory=dict)
    _failed: set[str] = field(default_factory=set)

    def can_fetch(self, origin: str, url: str, user_agent: str, respect: bool) -> bool:
        if not respect:
            return True
        if origin in self._failed:
            return True
        if origin not in self._parsers:
            rp = RobotFileParser()
            robots_url = urljoin(origin, "/robots.txt")
            rp.set_url(robots_url)
            try:
                rp.read()
                self._parsers[origin] = rp
            except Exception:
                self._failed.add(origin)
                self._parsers[origin] = None
                return True
        rp = self._parsers[origin]
        if rp is None:
            return True
        try:
            return rp.can_fetch(user_agent, url)
        except Exception:
            return True


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _strip_html_fallback(html: str) -> str:
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def html_to_text(html: str, url: str) -> str:
    """Primary: trafilatura; fallback: tag strip."""
    extracted = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )
    if extracted and extracted.strip():
        return extracted.strip()
    return _strip_html_fallback(html)


def pdf_to_text(body: bytes) -> str:
    reader = PdfReader(BytesIO(body))
    parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n\n".join(parts).strip()


def _origin_from_url(url: str) -> str:
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        raise ValueError(f"invalid URL for origin: {url}")
    return f"{p.scheme}://{p.netloc}"


def _write_raw_snapshot(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def fetch_url_bytes(
    client: httpx.Client,
    url: str,
    *,
    user_agent: str,
    timeout: float,
    max_retries: int,
) -> tuple[bytes, str, str]:
    """
    Returns (body, final_url, content_type).
    Raises httpx.HTTPError on unrecoverable failure after retries.
    """
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/pdf,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
    }
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.get(url, headers=headers, timeout=timeout, follow_redirects=True)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            return resp.content, str(resp.url), ctype or "application/octet-stream"
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(0.5 * (2**attempt))
            else:
                raise last_exc from None
    raise RuntimeError("unreachable")


def normalize_response(
    body: bytes,
    *,
    mime_type: str,
    final_url: str,
    source_url: str,
    corpus_doc: CorpusDocument,
    fetched_at: datetime,
    store_raw: bool,
    raw_path: Path | None,
) -> NormalizedDocument:
    if raw_path and store_raw:
        _write_raw_snapshot(raw_path, body)

    mt = mime_type.lower()
    if "pdf" in mt or body[:4] == b"%PDF":
        text = pdf_to_text(body)
    else:
        html = body.decode("utf-8", errors="replace")
        text = html_to_text(html, final_url)

    return NormalizedDocument(
        source_url=source_url,
        final_url=final_url,
        fetched_at=fetched_at,
        content_hash=_content_hash(text),
        mime_type=mime_type,
        text=text,
        manifest_document_type=corpus_doc.document_type,
        amc_id=corpus_doc.amc_id,
        scheme_name=corpus_doc.scheme_name,
        category=corpus_doc.category,
    )


def scrape_document(
    corpus_doc: CorpusDocument,
    *,
    client: httpx.Client,
    allowlist: AllowlistSection,
    scrape: ScrapeSection,
    robots: RobotsCache,
    raw_dir: Path | None = None,
) -> ScrapeResult:
    url = str(corpus_doc.url)
    errs = validate_urls_against_allowlist(
        [url],
        allowed_hosts=allowlist.hosts,
        path_prefixes_by_host=allowlist.path_prefixes_by_host,
    )
    if errs:
        return ScrapeResult(source_url=url, success=False, error="; ".join(errs))

    origin = _origin_from_url(url)
    if not robots.can_fetch(origin, url, scrape.user_agent, scrape.respect_robots_txt):
        return ScrapeResult(source_url=url, success=False, error="blocked by robots.txt")

    raw_path: Path | None = None
    if scrape.store_raw_snapshots and raw_dir is not None:
        safe = hashlib.sha256(url.encode()).hexdigest()[:16]
        raw_path = raw_dir / f"{safe}.bin"

    try:
        body, final_url, mime_type = fetch_url_bytes(
            client,
            url,
            user_agent=scrape.user_agent,
            timeout=scrape.timeout_seconds,
            max_retries=scrape.max_retries,
        )
        fetched_at = datetime.now(timezone.utc)
        doc = normalize_response(
            body,
            mime_type=mime_type,
            final_url=final_url,
            source_url=url,
            corpus_doc=corpus_doc,
            fetched_at=fetched_at,
            store_raw=scrape.store_raw_snapshots,
            raw_path=raw_path,
        )
        return ScrapeResult(source_url=url, success=True, document=doc)
    except Exception as e:
        return ScrapeResult(source_url=url, success=False, error=f"{type(e).__name__}: {e}")


def scrape_corpus(
    documents: list[CorpusDocument],
    yaml_cfg: YamlConfig,
    *,
    project_root: Path | None = None,
) -> list[ScrapeResult]:
    """
    Fetch and normalize all corpus documents. Applies delay between requests.
    Per-URL failures are captured in ScrapeResult; the batch always completes.
    """
    root = project_root or Path(__file__).resolve().parents[2]
    raw_dir = root / yaml_cfg.scrape.raw_snapshots_dir if yaml_cfg.scrape.store_raw_snapshots else None

    robots = RobotsCache()
    results: list[ScrapeResult] = []

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    with httpx.Client(limits=limits) as client:
        for i, doc in enumerate(documents):
            if i > 0 and yaml_cfg.scrape.delay_seconds > 0:
                time.sleep(yaml_cfg.scrape.delay_seconds)
            r = scrape_document(
                doc,
                client=client,
                allowlist=yaml_cfg.allowlist,
                scrape=yaml_cfg.scrape,
                robots=robots,
                raw_dir=raw_dir,
            )
            results.append(r)

    return results


def main() -> None:
    """CLI: load manifest + settings, run scrape, print JSON lines to stdout."""
    import json
    import sys

    from m1_rag.corpus import iter_corpus_documents, load_corpus_manifest, manifest_path_from_config
    from m1_rag.settings import AppSettings

    settings = AppSettings.load()
    path = manifest_path_from_config(settings.yaml.corpus.manifest_path)
    manifest = load_corpus_manifest(path)
    docs = iter_corpus_documents(manifest)
    if len(docs) > settings.yaml.corpus.max_urls_per_ingest_run:
        print(
            f"abort: {len(docs)} documents exceeds corpus.max_urls_per_ingest_run",
            file=sys.stderr,
        )
        sys.exit(1)

    results = scrape_corpus(docs, settings.yaml)
    for r in results:
        line = {
            "source_url": r.source_url,
            "success": r.success,
            "error": r.error,
            "document": r.document.model_dump(mode="json") if r.document else None,
        }
        print(json.dumps(line, ensure_ascii=False))


if __name__ == "__main__":
    main()
