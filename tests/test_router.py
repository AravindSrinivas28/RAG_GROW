"""Phase 6 router."""

from m1_rag.router import RouteClass, classify_route


def test_route_advisory_should_i() -> None:
    assert classify_route("Should I invest in HDFC Large Cap?") == RouteClass.ADVISORY


def test_route_advisory_which_better() -> None:
    assert classify_route("Which fund is better, A or B?") == RouteClass.ADVISORY


def test_route_pii_pan() -> None:
    assert classify_route("What is my PAN used for?") == RouteClass.PII


def test_route_factual_expense() -> None:
    assert classify_route("What is the expense ratio for this scheme?") == RouteClass.FACTUAL


def test_route_factual_empty_defaults_factual() -> None:
    assert classify_route("") == RouteClass.FACTUAL
