"""Phase 9: golden router / refusal cases from golden_cases.yaml."""

from pathlib import Path

import pytest
import yaml

from m1_rag.router import RouteClass, classify_route


def _golden_path() -> Path:
    return Path(__file__).resolve().parents[1] / "phases" / "phase_9_quality" / "golden_cases.yaml"


def _load() -> dict:
    raw = yaml.safe_load(_golden_path().read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


@pytest.mark.parametrize(
    "case_id,query",
    [
        (c["id"], c["query"])
        for c in _load().get("refusal_router", [])
        if isinstance(c, dict) and "id" in c
    ],
)
def test_golden_refusal_router(case_id: str, query: str) -> None:
    r = classify_route(query)
    assert r == RouteClass.ADVISORY, f"{case_id}: expected advisory route"


@pytest.mark.parametrize(
    "case_id,query",
    [
        (c["id"], c["query"])
        for c in _load().get("pii_router", [])
        if isinstance(c, dict) and "id" in c
    ],
)
def test_golden_pii_router(case_id: str, query: str) -> None:
    r = classify_route(query)
    assert r == RouteClass.PII, f"{case_id}: expected PII route"


@pytest.mark.parametrize(
    "case_id,query",
    [
        (c["id"], c["query"])
        for c in _load().get("factual_router", [])
        if isinstance(c, dict) and "id" in c
    ],
)
def test_golden_factual_router(case_id: str, query: str) -> None:
    r = classify_route(query)
    assert r == RouteClass.FACTUAL, f"{case_id}: expected factual route"


def test_citation_host_helper() -> None:
    from m1_rag.observability import citation_host_allowed

    assert citation_host_allowed("https://groww.in/mutual-funds/x", ["groww.in"])
    assert citation_host_allowed("https://www.amfiindia.in/foo", ["amfiindia.in"])
    assert not citation_host_allowed("https://evil.example.com/", ["groww.in"])
