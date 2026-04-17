"""Phase 2 scraping (mocked HTTP)."""

from datetime import datetime, timezone
from io import BytesIO

import httpx
from pydantic import HttpUrl

from m1_rag.corpus import CorpusDocument
from m1_rag.scrape import (
    RobotsCache,
    _content_hash,
    html_to_text,
    normalize_response,
    pdf_to_text,
    scrape_document,
)
from m1_rag.settings import YamlConfig


def test_content_hash_stable() -> None:
    assert _content_hash("hello") == _content_hash("hello")
    assert _content_hash("a") != _content_hash("b")


def test_html_to_text_trafilatura() -> None:
    html = "<html><body><article><p>Expense ratio 0.12%</p></article></body></html>"
    t = html_to_text(html, "https://groww.in/mutual-funds/x")
    assert "Expense" in t
    assert "0.12" in t


def test_normalize_response_html() -> None:
    doc = CorpusDocument(
        url=HttpUrl("https://groww.in/mutual-funds/x"),
        amc_id="hdfc",
        scheme_name="Test Fund",
        document_type="scheme_page",
        category="large_cap",
        origin="entry",
    )
    body = b"<html><body><main><p>Minimum SIP Rs 500</p></main></body></html>"
    out = normalize_response(
        body,
        mime_type="text/html",
        final_url="https://groww.in/mutual-funds/x",
        source_url="https://groww.in/mutual-funds/x",
        corpus_doc=doc,
        fetched_at=datetime.now(timezone.utc),
        store_raw=False,
        raw_path=None,
    )
    assert out.mime_type == "text/html"
    assert "500" in out.text
    assert out.manifest_document_type == "scheme_page"
    assert len(out.content_hash) == 64


def test_pdf_to_text_empty_pdf() -> None:
    from pypdf import PdfWriter

    buf = BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    w.write(buf)
    assert pdf_to_text(buf.getvalue()) == ""


def _minimal_yaml(**overrides: object) -> YamlConfig:
    base = {
        "allowlist": {
            "hosts": ["groww.in"],
            "path_prefixes_by_host": {"groww.in": ["/mutual-funds/"]},
        },
        "scrape": {
            "user_agent": "TestBot/1.0",
            "delay_seconds": 0.0,
            "timeout_seconds": 10.0,
            "max_retries": 0,
            "respect_robots_txt": False,
        },
    }
    base.update(overrides)
    return YamlConfig.model_validate(base)


def test_scrape_document_mock_transport() -> None:
    html = b"<html><body><p>Exit load 1 percent</p></body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=html,
            headers={"content-type": "text/html; charset=utf-8"},
        )

    transport = httpx.MockTransport(handler)
    corpus_doc = CorpusDocument(
        url=HttpUrl("https://groww.in/mutual-funds/sample-fund-direct-growth"),
        amc_id="hdfc",
        scheme_name="Sample",
        document_type="scheme_page",
        category="multi_cap",
        origin="entry",
    )
    yaml_cfg = _minimal_yaml()

    with httpx.Client(transport=transport) as client:
        r = scrape_document(
            corpus_doc,
            client=client,
            allowlist=yaml_cfg.allowlist,
            scrape=yaml_cfg.scrape,
            robots=RobotsCache(),
            raw_dir=None,
        )

    assert r.success, r.error
    assert r.document is not None
    assert "Exit load" in r.document.text


def test_allowlist_rejects_before_fetch() -> None:
    def boom(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not fetch")

    transport = httpx.MockTransport(boom)
    corpus_doc = CorpusDocument(
        url=HttpUrl("https://evil.example.com/page"),
        amc_id=None,
        scheme_name=None,
        document_type="regulatory",
        category=None,
        origin="entry",
    )
    yaml_cfg = _minimal_yaml(
        allowlist={"hosts": ["groww.in"], "path_prefixes_by_host": {}},
    )

    with httpx.Client(transport=transport) as client:
        r = scrape_document(
            corpus_doc,
            client=client,
            allowlist=yaml_cfg.allowlist,
            scrape=yaml_cfg.scrape,
            robots=RobotsCache(),
            raw_dir=None,
        )
    assert not r.success
    assert r.error and "not allowed" in r.error
