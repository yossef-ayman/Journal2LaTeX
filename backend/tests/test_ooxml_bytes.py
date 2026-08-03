"""The guarantee the whole engine rests on: untouched bytes stay untouched.

If these fail, nothing else matters.  Word reports *"the file appears to be
corrupted"* when a part is re-serialised rather than spliced, and the failure
shows up at PDF export -- long after the code that caused it ran.
"""

from __future__ import annotations

import zipfile

import pytest

from document_engine.ooxml.bytes import (
    OOXMLEditError,
    escape_text,
    is_text_part,
    parse_part,
    rewrite_spans,
)


def test_untouched_part_is_the_same_object(document_bytes: bytes) -> None:
    """Not merely equal -- identical.  Equality can be an accident; identity is
    proof that no splice path ran at all."""
    part = parse_part(document_bytes)
    assert part.serialize() is document_bytes


def test_untouched_part_is_the_same_object_with_blocks(document_bytes: bytes) -> None:
    """Turning the block model on must not touch the write path."""
    part = parse_part(document_bytes, blocks=True, name="word/document.xml")
    assert part.serialize() is document_bytes


def test_blocks_off_by_default(document_bytes: bytes) -> None:
    """The Document Generator's call signature, and what it must keep getting."""
    part = parse_part(document_bytes)
    assert part.blocks == []
    assert part.sections == []


def test_block_model_does_not_change_the_legacy_view(document_bytes: bytes) -> None:
    """Same paragraphs, same text nodes, whether or not blocks were built."""
    plain = parse_part(document_bytes)
    rich = parse_part(document_bytes, blocks=True)
    assert len(plain.paragraphs) == len(rich.paragraphs)
    assert plain.counts == rich.counts
    assert [p.text() for p in plain.paragraphs] == [p.text() for p in rich.paragraphs]


def test_every_text_part_round_trips(paper) -> None:
    with zipfile.ZipFile(paper) as archive:
        names = [n for n in archive.namelist() if is_text_part(n)]
        assert names, "a Word document always has at least word/document.xml"
        for name in names:
            raw = archive.read(name)
            assert parse_part(raw, blocks=True, name=name).serialize() is raw


def test_a_single_edit_changes_only_that_text(document_bytes: bytes) -> None:
    """The claim in one sentence: edit one paragraph, and the delta is that
    paragraph -- not a reformatted file that happens to render the same."""
    part = parse_part(document_bytes)
    target = next(p for p in part.paragraphs if len(p.text().strip()) > 20)
    original = target.text()
    assert rewrite_spans(target, [(0, len(original), "REPLACED")]) == 1
    out = part.serialize()
    assert out is not document_bytes
    assert b"REPLACED" in out
    # Everything before the first edited node is byte-identical.
    first = min(n.tag_start for n in part._nodes if n.changed)
    assert out[:first] == document_bytes[:first]


def test_rewrite_spans_puts_the_value_in_one_run(document_bytes: bytes) -> None:
    part = parse_part(document_bytes)
    # Fragmentation is what this test is about, so a document that happens to
    # have none has nothing to say here rather than something to fail about.
    target = next((p for p in part.paragraphs if len(p.live_nodes) > 1), None)
    if target is None:
        pytest.skip("this document has no paragraph split across runs")
    total = len(target.text())
    rewrite_spans(target, [(0, total, "ONE")])
    changed = [n for n in target.live_nodes if n.replacement is not None]
    assert changed[0].replacement == "ONE"
    assert all(n.replacement == "" for n in changed[1:])


def test_escape_text_escapes_only_what_word_escapes() -> None:
    assert escape_text('a & b < c > d "e"') == 'a &amp; b &lt; c &gt; d "e"'


def test_malformed_part_raises_rather_than_guessing() -> None:
    with pytest.raises(OOXMLEditError):
        parse_part(b"<w:p><w:r>", blocks=True)


def test_is_text_part_covers_the_parts_that_carry_text() -> None:
    assert is_text_part("word/document.xml")
    assert is_text_part("word/header2.xml")
    assert is_text_part("word/footnotes.xml")
    assert not is_text_part("word/styles.xml")
    assert not is_text_part("word/media/image1.png")
