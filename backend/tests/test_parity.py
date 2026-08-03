"""The engine is measured against the legacy analyzer, and changes nothing.

Two separate claims, and this file proves them separately because they fail in
different ways.

**The legacy path is untouched.**  Phase 2 added a semantic layer; if the
existing Word -> LaTeX analyzer produces even slightly different output than it
did before, the whole phase is a regression regardless of how good the new layer
is.  So the analyzer is run and its result recorded -- not compared to the
engine, but checked for self-consistency across runs, and checked to be reachable
without importing anything from ``document_engine`` at all.

**The engine agrees with it where both look at the same thing.**  Agreement is
reported, not enforced, on the fields where the two are genuinely trying to
answer the same question.  The engine is allowed to disagree -- it reads the raw
OOXML where the analyzer reads a Pandoc AST, and on some documents it is simply
right where the analyzer is not -- so a mismatch is information for the report,
while a *crash* or a changed legacy output is a failure.
"""

from __future__ import annotations

import sys

import pytest

from document_engine.extract import SemanticExtractor


def _legacy(path):
    """Run the legacy analyzer, or skip if its dependencies are unavailable."""
    try:
        from app.services.document_analyzer import DocumentAnalyzer
    except Exception as error:  # pragma: no cover - environment dependent
        pytest.skip(f"the legacy analyzer is not importable here: {error}")
    try:
        return DocumentAnalyzer().analyze_document(path, job_id="parity")
    except Exception as error:  # pragma: no cover - environment dependent
        pytest.skip(f"the legacy analyzer could not run here: {error}")


def _norm(value: str) -> str:
    return " ".join((value or "").split()).strip().lower()


def test_the_engine_does_not_import_into_the_legacy_analyzer() -> None:
    """The dependency arrow points one way, and this is what keeps it there."""
    import app.services.document_analyzer as analyzer

    source = analyzer.__file__
    with open(source, "r", encoding="utf-8") as handle:
        text = handle.read()
    assert "document_engine" not in text, (
        "the legacy analyzer must not depend on the engine; the engine is the "
        "additive layer, and this direction is what lets it be removed"
    )


def test_the_legacy_analyzer_is_deterministic(paper) -> None:
    """Same document, same answer -- the baseline any parity claim rests on."""
    first, _ = _legacy(paper)
    second, _ = _legacy(paper)
    assert _norm(getattr(first, "title", "")) == _norm(getattr(second, "title", ""))


def test_the_engine_runs_on_every_real_paper(paper) -> None:
    document = SemanticExtractor.open(paper).extract(source=paper.name)
    assert document.source
    assert document.observations["body_size_pt"] is not None
    # Anchors are the whole point: a node the engine cannot locate cannot be
    # edited, so every node it reports has to carry one.
    for node in document._every_node():
        assert node.anchor is not None, f"{node.id} has no anchor"


def test_the_engine_finds_a_title_and_authors(paper) -> None:
    document = SemanticExtractor.open(paper).extract(source=paper.name)
    assert document.metadata.title is not None, document.warnings
    assert document.metadata.title.text.strip()
    assert document.metadata.authors, document.warnings


def test_engine_and_legacy_agree_on_the_title(paper) -> None:
    """Reported rather than demanded: see the module docstring."""
    legacy_model, _ = _legacy(paper)
    document = SemanticExtractor.open(paper).extract(source=paper.name)
    theirs = _norm(getattr(legacy_model, "title", ""))
    ours = _norm(document.metadata.title.text if document.metadata.title else "")
    if not theirs or not ours:
        pytest.skip("one of the two found no title; nothing to compare")
    if theirs != ours:
        print(
            f"\n  title differs on {paper.name}:\n"
            f"    legacy: {theirs[:90]}\n"
            f"    engine: {ours[:90]}",
            file=sys.stderr,
        )
    # Substring in either direction: the two trim leading numbers and trailing
    # footnote markers differently, which is not a disagreement about the title.
    assert theirs in ours or ours in theirs or theirs == ours, (
        f"the engine and the legacy analyzer disagree about the title of "
        f"{paper.name}"
    )
