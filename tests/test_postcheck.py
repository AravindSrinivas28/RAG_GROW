"""Post-check helpers."""

from m1_rag.postcheck import count_sentences, truncate_to_sentences


def test_count_sentences() -> None:
    assert count_sentences("One. Two. Three.") == 3
    assert count_sentences("No end") == 1


def test_truncate_to_three() -> None:
    t = "First. Second. Third. Fourth."
    assert truncate_to_sentences(t, 3) == "First. Second. Third."
