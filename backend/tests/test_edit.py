"""What the writing engine must guarantee on the real documents.

The claims worth testing here are not "the edit worked" -- that is the easy part
-- but the four properties that separate editing a document from rebuilding one:

* **only the affected bytes move.**  Measured by identity of every other part
  and by the exact byte delta of the one that changed;
* **nothing happens without a decision.**  A pending or rejected suggestion is
  not a slow accept;
* **a stale suggestion is refused, not guessed at.**  This is the guard against
  silently corrupting somebody's manuscript;
* **the same inputs give the same bytes.**  Determinism is asserted by hashing
  two independent runs, not by inspecting the code for clocks.
"""

from __future__ import annotations

import hashlib
import io
import zipfile

import pytest

from document_engine.edit.diff import changed_span, diff_words, tokenize
from document_engine.edit.preview import PreviewEngine
from document_engine.edit.suggestions import (
    Suggestion,
    SuggestionError,
    SuggestionSet,
)
from document_engine.edit.writer import WordWriter, _paragraph_index
from document_engine.extract import SemanticExtractor
from document_engine.ooxml.package import Package


def _engine(paper) -> PreviewEngine:
    return PreviewEngine.open(paper)


def _title_edit(engine, suffix=" (Revised)"):
    """Propose one edit to the title, whatever the title turns out to be."""
    document = engine.analyze()
    title = document.metadata.title
    if title is None:  # pragma: no cover - every real paper has one
        pytest.skip("no title to edit")
    suggestions = SuggestionSet()
    suggestions.propose(title.id, title.text, title.text + suffix, kind="manual")
    return document, suggestions


def _reopen(data: bytes) -> PreviewEngine:
    archive = zipfile.ZipFile(io.BytesIO(data))
    names = archive.namelist()
    return PreviewEngine({name: archive.read(name) for name in names}, names)


# -- the decision model ---------------------------------------------------


def test_a_suggestion_needs_a_node() -> None:
    with pytest.raises(SuggestionError):
        Suggestion(node_id="", original="a", suggested="b")


def test_suggestion_ids_are_deterministic() -> None:
    """Ids survive a reload, or the user's clicks do not."""
    first = Suggestion(node_id="n1", original="a", suggested="b")
    second = Suggestion(node_id="n1", original="a", suggested="b")
    assert first.id == second.id
    assert Suggestion(node_id="n1", original="a", suggested="c").id != first.id


def test_a_set_deduplicates_the_same_proposal() -> None:
    suggestions = SuggestionSet()
    one = suggestions.propose("n1", "a", "b")
    two = suggestions.propose("n1", "a", "b")
    assert one is two and len(suggestions) == 1


def test_an_edited_suggestion_keeps_what_was_suggested() -> None:
    """Accept / reject / *edit* -- the third case has to be reviewable after."""
    suggestion = Suggestion(node_id="n1", original="a", suggested="b")
    suggestion.edit("c")
    assert suggestion.replacement == "c"
    assert suggestion.suggested == "b"
    assert suggestion.source == "user" and suggestion.is_accepted


def test_a_decision_set_round_trips_through_json() -> None:
    suggestions = SuggestionSet()
    suggestions.propose("n1", "a", "b").accept()
    suggestions.propose("n2", "c", "d").reject()
    restored = SuggestionSet.from_list(suggestions.as_list())
    assert restored.counts() == suggestions.counts()
    assert {s.id for s in restored} == {s.id for s in suggestions}


# -- the diff -------------------------------------------------------------


def test_the_changed_span_is_the_smallest_one() -> None:
    span = changed_span("the quick brown fox", "the quick red fox")
    assert span is not None
    start, end, replacement = span
    assert "the quick " == "the quick brown fox"[:start]
    assert replacement == "red"
    assert "the quick brown fox"[end:] == " fox"


def test_an_unchanged_string_has_no_span() -> None:
    assert changed_span("same", "same") is None


def test_the_diff_reconstructs_both_sides() -> None:
    """The only property a diff really owes anyone."""
    original, suggested = "one two three four", "one two and three five"
    hunks = diff_words(original, suggested)
    left = "".join(h.text for h in hunks if h.kind in ("equal", "delete"))
    right = "".join(h.text for h in hunks if h.kind in ("equal", "insert"))
    assert left == original and right == suggested


def test_tokenization_keeps_punctuation_separate() -> None:
    assert tokenize("Hello, world") == ["Hello", ",", " ", "world"]


# -- the paragraph index --------------------------------------------------


def test_block_and_byte_paragraphs_agree_in_every_part(paper) -> None:
    """The index is the one place a bug would write to the wrong paragraph."""
    package = Package.open(paper)
    for name, part in package.parts.items():
        index = _paragraph_index(part)
        from document_engine.ooxml.blocks import iter_paragraphs

        for block in iter_paragraphs(part.blocks, skip_fallback=False):
            byte_paragraph = index.get(id(block))
            assert byte_paragraph is not None, f"{name}: unindexed paragraph"
            assert byte_paragraph.text() == block.text()


# -- writing --------------------------------------------------------------


def test_nothing_is_written_without_a_decision(paper) -> None:
    engine = _engine(paper)
    _, suggestions = _title_edit(engine)
    preview = engine.preview(suggestions)   # left pending on purpose
    assert preview.result.applied == []
    assert preview.parts_untouched == preview.parts_total


def test_a_rejected_suggestion_is_not_a_slow_accept(paper) -> None:
    engine = _engine(paper)
    _, suggestions = _title_edit(engine)
    suggestions.reject_all()
    preview = engine.preview(suggestions)
    assert preview.result.applied == []
    assert preview.parts_untouched == preview.parts_total


def test_an_accepted_edit_reaches_the_document(paper) -> None:
    engine = _engine(paper)
    document, suggestions = _title_edit(engine)
    suggestions.accept_all()
    preview = engine.preview(suggestions)
    assert len(preview.result.applied) == 1
    assert not preview.result.refused
    reread = _reopen(preview.to_bytes()).analyze()
    assert reread.metadata.title is not None
    assert reread.metadata.title.text.endswith("(Revised)")


def test_only_the_affected_part_is_rewritten(paper) -> None:
    """The central claim of the phase, measured rather than asserted."""
    engine = _engine(paper)
    _, suggestions = _title_edit(engine)
    suggestions.accept_all()
    preview = engine.preview(suggestions)
    changed = [item for item in preview.impact if item.changed]
    assert [item.name for item in changed] == ["word/document.xml"]
    # Splicing text in adds exactly the characters that were added.  Any
    # re-serialisation of the part would move this number.
    assert changed[0].delta == len(" (Revised)")


def test_the_original_package_is_never_touched_by_a_preview(paper) -> None:
    engine = _engine(paper)
    before = dict(engine._entries)
    _, suggestions = _title_edit(engine)
    suggestions.accept_all()
    engine.preview(suggestions)
    engine.preview(suggestions)
    for name, data in before.items():
        assert engine._entries[name] is data


def test_the_same_decisions_produce_the_same_bytes(paper) -> None:
    engine = _engine(paper)
    _, suggestions = _title_edit(engine)
    suggestions.accept_all()
    first = engine.preview(suggestions).to_bytes()
    second = engine.preview(SuggestionSet.from_list(suggestions.as_list())).to_bytes()
    assert hashlib.sha1(first).hexdigest() == hashlib.sha1(second).hexdigest()


def test_a_stale_suggestion_is_refused(paper) -> None:
    """The guard that makes editing the wrong document impossible rather than
    unlikely."""
    engine = _engine(paper)
    document = engine.analyze()
    title = document.metadata.title
    suggestions = SuggestionSet()
    suggestions.propose(
        title.id, "a title this document does not have", "something else"
    ).accept()
    preview = engine.preview(suggestions)
    assert not preview.result.applied
    assert len(preview.result.refused) == 1
    assert "no longer reads" in preview.result.refused[0].reason


def test_an_unknown_node_is_refused(paper) -> None:
    engine = _engine(paper)
    suggestions = SuggestionSet()
    suggestions.propose("node-that-does-not-exist", "a", "b").accept()
    preview = engine.preview(suggestions)
    assert not preview.result.applied
    assert "no node with that id" in preview.result.refused[0].reason


def test_a_table_cannot_be_edited_as_text(paper) -> None:
    """Refusing is the correct answer; inventing one is not."""
    engine = _engine(paper)
    document = engine.analyze()
    if not document.tables:
        pytest.skip("this paper has no tables")
    table = document.tables[0]
    suggestions = SuggestionSet()
    suggestions.propose(table.id, "", "anything").accept()
    preview = engine.preview(suggestions)
    assert not preview.result.applied
    assert preview.result.refused


def test_several_edits_apply_independently(paper) -> None:
    """Multiple accepted edits, including two in different parts of the file."""
    engine = _engine(paper)
    document = engine.analyze()
    suggestions = SuggestionSet()
    expected = 0
    title = document.metadata.title
    if title is not None:
        suggestions.propose(title.id, title.text, title.text + " X")
        expected += 1
    for reference in document.references[:3]:
        suggestions.propose(reference.id, reference.text, reference.text + " Y")
        expected += 1
    suggestions.accept_all()
    preview = engine.preview(suggestions)
    assert len(preview.result.applied) == expected
    assert not preview.result.refused
    changed = [item for item in preview.impact if item.changed]
    assert changed and changed[0].delta == expected * 2


def test_the_result_still_parses_as_the_same_document(paper) -> None:
    """An edit that broke the OOXML would show up here before Word ever saw it."""
    engine = _engine(paper)
    document, suggestions = _title_edit(engine)
    suggestions.accept_all()
    reread = _reopen(engine.preview(suggestions).to_bytes()).analyze()
    assert len(list(reread.all_sections())) == len(list(document.all_sections()))
    assert len(reread.tables) == len(document.tables)
    assert len(reread.figures) == len(document.figures)
    assert len(reread.references) == len(document.references)


def test_the_written_package_is_a_valid_zip_with_the_same_entries(paper) -> None:
    engine = _engine(paper)
    _, suggestions = _title_edit(engine)
    suggestions.accept_all()
    data = engine.preview(suggestions).to_bytes()
    archive = zipfile.ZipFile(io.BytesIO(data))
    assert archive.testzip() is None
    assert archive.namelist() == list(engine._order)


def test_the_writer_does_not_reach_the_production_pipeline() -> None:
    """Phase 3 writes documents; the converter must not know it exists."""
    import app.services.document_analyzer as analyzer

    with open(analyzer.__file__, "r", encoding="utf-8") as handle:
        assert "document_engine" not in handle.read()


def test_the_writer_needs_no_extractor_state(paper) -> None:
    """A writer built on a freshly opened package behaves the same as one built
    inside the preview engine -- the writer holds no hidden state."""
    package = Package.open(paper)
    document = SemanticExtractor(package).extract(source=paper.name)
    title = document.metadata.title
    suggestions = SuggestionSet()
    suggestions.propose(title.id, title.text, title.text + " Z").accept()
    result = WordWriter(package, document).apply(suggestions)
    assert len(result.applied) == 1
    assert result.changed_parts == ["word/document.xml"]
