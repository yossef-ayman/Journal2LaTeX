"""What the semantic layer must get right on the real documents.

These tests assert *properties* rather than transcribed answers.  Asserting that
paper 2's title is a particular string would pass forever and tell nobody
whether the extractor works; asserting that the title is the most prominent line
in the front matter, that every author name is shorter than the line it came
from, and that no section is its own ancestor, fails the moment the logic breaks
and keeps meaning something on a document nobody has seen yet.
"""

from __future__ import annotations

import pytest

from document_engine.extract import SemanticExtractor
from document_engine.extract.objects import parse_caption
from document_engine.extract.references import _marker_of
from document_engine.extract.signals import (
    DocumentSignals,
    _leading_number,
    _looks_like_prose,
)
from document_engine.ooxml.package import Package


def _document(paper):
    return SemanticExtractor.open(paper).extract(source=paper.name)


# -- the signal cascade ---------------------------------------------------


def test_prose_is_not_a_heading() -> None:
    assert _looks_like_prose("This sentence ends the way sentences do.")
    assert not _looks_like_prose("Introduction")
    assert not _looks_like_prose("Methods:")  # run-in headings are real


def test_leading_numbers_carry_their_depth() -> None:
    assert _leading_number("3.2.1 Results")[:2] == ("3.2.1", 3)
    assert _leading_number("2. 1 Social Media")[:2] == ("2.1", 2)
    assert _leading_number("IV. Discussion")[1] == 1
    assert _leading_number("Introduction") is None


def test_table_cells_are_never_headings(paper) -> None:
    """A bold column header is not a section, however prominent it looks."""
    package = Package.open(paper)
    signals = DocumentSignals(list(package.paragraphs()))
    for paragraph in signals.paragraphs:
        if paragraph.table_depth:
            assert not signals.classify(paragraph).is_heading


def test_every_heading_carries_its_evidence(paper) -> None:
    package = Package.open(paper)
    signals = DocumentSignals(list(package.paragraphs()))
    for paragraph in signals.paragraphs:
        verdict = signals.classify(paragraph)
        if verdict.is_heading:
            assert verdict.evidence, paragraph.text()[:60]
            assert 0.0 < verdict.confidence <= 1.0


def test_nothing_in_the_signals_is_hardcoded_to_these_documents() -> None:
    """A guard on the directive, not on behaviour.

    The extractors are required to be generic.  A style id, journal name or
    author name from the real corpus appearing in the source would be exactly
    the hardcoding that was ruled out, and is easier to catch here than in
    review.
    """
    import document_engine.extract.metadata as metadata
    import document_engine.extract.sections as sections
    import document_engine.extract.signals as signals

    forbidden = (
        "Heading1",
        "MANET",
        "Zayed",
        "Dysmorphic",
        "Akgül",
        "normal_paper",
    )
    for module in (signals, metadata, sections):
        with open(module.__file__, "r", encoding="utf-8") as handle:
            text = handle.read()
        for token in forbidden:
            assert token not in text, f"{token!r} is hardcoded in {module.__name__}"


# -- the document as a whole ----------------------------------------------


def test_the_section_tree_is_well_formed(paper) -> None:
    document = _document(paper)
    seen = set()
    for section in document.all_sections():
        assert id(section) not in seen, "a section appears twice in the tree"
        seen.add(id(section))
        for child in section.children:
            assert child.level > section.level, (
                "a child section must be deeper than its parent, even when the "
                "document skips levels"
            )


def test_every_node_can_be_found_by_its_id(paper) -> None:
    """Ids are what the editor will send back; a duplicate is an edit applied to
    the wrong place."""
    document = _document(paper)
    ids = [node.id for node in document._every_node()]
    assert all(ids), "every node needs an id"
    assert len(ids) == len(set(ids)), "node ids must be unique"
    sample = ids[len(ids) // 2]
    assert document.find(sample) is not None


def test_anchors_point_inside_the_part_they_name(paper) -> None:
    package = Package.open(paper)
    document = SemanticExtractor(package).extract(source=paper.name)
    sizes = {name: len(part.data) for name, part in package.parts.items()}
    for node in document._every_node():
        anchor = node.anchor
        assert anchor is not None
        limit = sizes.get(anchor.part)
        if limit is None:
            continue
        assert 0 <= anchor.start < anchor.end <= limit, node.id


def test_author_names_come_from_the_line_they_were_found_on(paper) -> None:
    """The single cheapest guard against a fabricated name."""
    document = _document(paper)
    for author in document.metadata.authors:
        assert author.block is not None
        line = author.block.text()
        assert author.name in line or author.name.split()[0] in line


def test_affiliation_links_are_by_marker_or_not_at_all(paper) -> None:
    document = _document(paper)
    meta = document.metadata
    by_id = {a.id: a for a in meta.affiliations}
    for author in meta.authors:
        for affiliation_id in author.affiliation_ids:
            assert affiliation_id in by_id
        if len(meta.affiliations) > 1 and author.affiliation_ids:
            linked = [by_id[i].marker for i in author.affiliation_ids]
            assert all(m in author.markers for m in linked if m), (
                "an author may only be tied to an affiliation by a shared "
                "marker; positional guessing is what this forbids"
            )


def test_references_are_kept_whole(paper) -> None:
    document = _document(paper)
    for reference in document.references:
        assert reference.text.strip()
        assert reference.block is not None
        # The marker is separated out; nothing else is.
        if reference.marker:
            assert not reference.text.startswith(reference.marker)


def test_tables_and_figures_are_all_accounted_for(paper) -> None:
    package = Package.open(paper)
    document = SemanticExtractor(package).extract(source=paper.name)
    top_level = [t for t in package.tables() if not t.table_depth]
    assert len(document.tables) == len(top_level)
    for table in document.tables:
        assert table.rows == len(table.cells)
        assert table.block is not None


def test_captions_are_paired_with_the_right_kind(paper) -> None:
    document = _document(paper)
    for figure in document.figures:
        if figure.caption:
            assert figure.caption.kind == "figure"
    for table in document.tables:
        if table.caption:
            assert table.caption.kind == "table"


def test_caption_labels_parse_without_an_english_word_list() -> None:
    class _Fake:
        anchor = None
        runs: list = []
        table_depth = 0
        in_fallback = False
        drawings: list = []
        equation_count = 0

        def __init__(self, text):
            self._text = text

        def text(self):
            return self._text

    assert parse_caption(_Fake("Figure 3. A chart")).number == "3"
    assert parse_caption(_Fake("Table IV: Results")).kind == "table"
    assert parse_caption(_Fake("Eq. (5)")).kind == "equation"
    assert parse_caption(_Fake("3.2 Methodology")) is None


def test_reference_markers_are_read_but_not_invented() -> None:
    assert _marker_of("[12] Doe, J.") == "12"
    assert _marker_of("12. Doe, J.") == "12"
    assert _marker_of("Doe, J. (2019)") is None


def test_warnings_describe_what_was_not_found(paper) -> None:
    """An engine that admits what it missed is the point of the confidence
    fields; this checks the admissions are real rather than decorative."""
    document = _document(paper)
    for warning in document.warnings:
        assert isinstance(warning, str) and warning.strip()
    if document.metadata.title is None:
        assert any("title" in w for w in document.warnings)
    if not document.references:
        assert any("reference" in w for w in document.warnings)


def test_observations_explain_the_decisions(paper) -> None:
    document = _document(paper)
    observations = document.observations
    assert observations["body_size_pt"] is not None
    assert 6.0 <= observations["body_size_pt"] <= 16.0
    assert observations["paragraphs"] > 0
    assert "heading_styles" in observations


def test_extraction_does_not_modify_the_package(paper) -> None:
    """The extractor is read-only, and this is what makes that a fact.

    Every guarantee about editing existing bytes depends on reading not being a
    write path in disguise.
    """
    package = Package.open(paper)
    SemanticExtractor(package).extract(source=paper.name)
    assert package.changed_parts() == []
    serialized = package.serialize()
    for name, data in serialized.items():
        assert data is package.entries[name]
