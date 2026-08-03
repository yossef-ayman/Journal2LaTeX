"""The block model: does it see the document the byte parser sees?

The two views come from one traversal, so any disagreement between them is a
bug in the builder rather than a difference of opinion -- which is exactly what
makes these assertions worth making.
"""

from __future__ import annotations

from document_engine.ooxml.blocks import (
    Anchor,
    Drawing,
    Paragraph,
    Run,
    Table,
    iter_paragraphs,
    iter_tables,
    modal_body_size_pt,
    scan_tag_end,
)
from document_engine.ooxml.bytes import parse_part
from document_engine.ooxml.props import ParagraphProps, RunProps


def _parse(document_bytes: bytes):
    return parse_part(document_bytes, blocks=True, name="word/document.xml")


def test_paragraph_count_matches_the_byte_parser(document_bytes: bytes) -> None:
    """Counting *all* branches, including mc:Fallback, must agree exactly."""
    part = _parse(document_bytes)
    everything = list(iter_paragraphs(part.blocks, skip_fallback=False))
    assert len(everything) == part.counts["paragraphs"]


def test_fallback_paragraphs_are_hidden_by_default(document_bytes: bytes) -> None:
    """A text box written twice must be read once and written twice."""
    part = _parse(document_bytes)
    visible = list(iter_paragraphs(part.blocks))
    everything = list(iter_paragraphs(part.blocks, skip_fallback=False))
    assert len(visible) <= len(everything)
    assert all(not p.in_fallback for p in visible)


def test_table_count_matches_including_nested(document_bytes: bytes) -> None:
    part = _parse(document_bytes)
    assert len(list(iter_tables(part.blocks, skip_fallback=False))) == part.counts["tables"]


def test_rows_and_cells_match(document_bytes: bytes) -> None:
    part = _parse(document_bytes)
    tables = list(iter_tables(part.blocks, skip_fallback=False))
    rows = sum(len(t.rows) for t in tables)
    cells = sum(len(r.cells) for t in tables for r in t.rows)
    assert rows == part.counts["table_rows"]
    assert cells == part.counts["table_cells"]


def test_paragraph_text_matches_the_byte_parser(document_bytes: bytes) -> None:
    """The strongest cross-check available: the same characters, in the same
    order, reached by two different code paths over one buffer."""
    part = _parse(document_bytes)
    blocks_text = "".join(
        p.text() for p in iter_paragraphs(part.blocks, skip_fallback=False)
    )
    nodes_text = "".join(p.text() for p in part.paragraphs)
    assert blocks_text == nodes_text


def test_every_anchor_is_inside_the_part_and_well_ordered(document_bytes: bytes) -> None:
    part = _parse(document_bytes)
    for paragraph in iter_paragraphs(part.blocks, skip_fallback=False):
        anchor = paragraph.anchor
        assert 0 <= anchor.start < anchor.end <= len(document_bytes)
        assert anchor.part == "word/document.xml"
        for run in paragraph.runs:
            # A run's bytes lie inside its paragraph's bytes.  If this ever
            # fails, a writer would splice a run into another paragraph.
            assert anchor.start <= run.anchor.start
            assert run.anchor.end <= anchor.end


def test_anchor_slices_back_to_real_xml(document_bytes: bytes) -> None:
    part = _parse(document_bytes)
    paragraph = next(iter_paragraphs(part.blocks))
    fragment = paragraph.anchor.slice(document_bytes)
    assert fragment.startswith(b"<w:p")
    assert fragment.rstrip().endswith(b"</w:p>") or fragment.rstrip().endswith(b"/>")


def test_run_text_reassembles_the_paragraph(document_bytes: bytes) -> None:
    part = _parse(document_bytes)
    for paragraph in list(iter_paragraphs(part.blocks))[:50]:
        assert paragraph.text() == "".join(r.text for r in paragraph.runs)


def test_drawings_and_bookmarks_are_counted(document_bytes: bytes) -> None:
    part = _parse(document_bytes)
    drawings = sum(
        len(p.drawings) for p in iter_paragraphs(part.blocks, skip_fallback=False)
    )
    assert drawings == part.counts["drawings"]
    assert len(part.bookmarks) == part.counts["bookmarks"]


def test_hyperlinks_are_counted(document_bytes: bytes) -> None:
    part = _parse(document_bytes)
    total = sum(
        p.hyperlink_count for p in iter_paragraphs(part.blocks, skip_fallback=False)
    )
    assert total == part.counts["hyperlinks"]


def test_breaks_are_counted(document_bytes: bytes) -> None:
    part = _parse(document_bytes)
    total = sum(
        p.break_count for p in iter_paragraphs(part.blocks, skip_fallback=False)
    )
    # Breaks outside any run are possible but vanishingly rare; the block model
    # attributes them to runs, so it may see slightly fewer, never more.
    assert total <= part.counts["breaks"]


def test_every_document_has_at_least_one_section(document_bytes: bytes) -> None:
    part = _parse(document_bytes)
    assert part.sections
    section = part.sections[-1]
    assert section.page_width_twips and section.page_width_twips > 0
    assert section.text_width_inches and 3.0 < section.text_width_inches < 12.0


def test_scan_tag_end_is_quote_aware() -> None:
    data = b'<w:t w:val="a>b"/>rest'
    assert scan_tag_end(data, 0) == data.index(b"rest")


def test_modal_body_size_is_weighted_by_text() -> None:
    """Forty headings must not outvote four hundred paragraphs of body text."""
    def paragraph(size: int, text: str) -> Paragraph:
        anchor = Anchor("p", 0, 1)
        return Paragraph(
            anchor=anchor,
            runs=[Run(anchor=anchor, props=RunProps(size_half_points=size), text=text)],
        )

    paragraphs = [paragraph(28, "H") for _ in range(40)]
    paragraphs += [paragraph(20, "body text here") for _ in range(5)]
    assert modal_body_size_pt(paragraphs) == 10.0


def test_modal_body_size_is_none_without_sizes() -> None:
    assert modal_body_size_pt([]) is None
