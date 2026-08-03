"""What the assistant must guarantee, on the real manuscripts.

The interesting claims are not "the grammar plugin found something" -- a plugin
that found nothing would still be correct on a clean document -- but the
properties that make an assistant safe to put in front of an author:

* **a plugin cannot write.**  Asserted structurally: the context object it is
  handed has no package, no writer and no bytes on it;
* **everything it proposes is applyable.**  A suggestion the writer refuses is
  a suggestion the user was invited to accept and then denied, which reads as a
  bug in the writer and is not one;
* **nothing is proposed that changes nothing.**  Fifty no-op suggestions are
  fifty wasted decisions;
* **every suggestion is reviewable** -- node, original, suggested, reason,
  confidence -- because that is the contract the UI renders;
* **the same document gives the same review.**  Twice, byte for byte;
* **the document is never touched by reviewing it.**
"""

from __future__ import annotations

import hashlib

import pytest

from document_engine.assist import (
    Context,
    DocumentAssistant,
    NullProvider,
    Registry,
    SuggestionPlugin,
    all_plugins,
    default_registry,
)
from document_engine.assist.assistant import ProviderPlugin
from document_engine.assist.plugins.consistency import _majority, _spelling_key
from document_engine.assist.plugins.journal import _style_of, _to_sentence, _to_title
from document_engine.edit.preview import PreviewEngine
from document_engine.edit.suggestions import SuggestionSet
from document_engine.edit.writer import editable_text

ALL = [plugin.name for plugin in all_plugins()]


def _review(paper, plugins=None):
    engine = PreviewEngine.open(paper)
    document = engine.analyze(source=paper.name)
    assistant = DocumentAssistant(default_registry())
    return engine, document, assistant.review(document, plugins or ALL)


def _one_per_node(review) -> SuggestionSet:
    """Accept at most one suggestion per node.

    Two plugins may both rewrite the same sentence -- grammar fixing its spacing
    and consistency fixing a spelling in it -- and the writer refuses the second
    as overlapping, correctly.  Testing "everything applies" therefore means
    testing one decision per node; the overlap refusal has its own test below.
    """
    chosen, seen = SuggestionSet(), set()
    for suggestion in review.suggestions:
        if suggestion.node_id in seen:
            continue
        seen.add(suggestion.node_id)
        chosen.add(suggestion)
    return chosen


# -- the shape of a plugin ------------------------------------------------


def test_a_plugin_is_handed_nothing_it_could_write_with() -> None:
    """The safety property, asserted rather than documented."""
    context = Context(document=None, plugin_name="x")  # type: ignore[arg-type]
    for attribute in ("package", "writer", "parts", "entries", "save", "apply"):
        assert not hasattr(context, attribute)


def test_every_shipped_plugin_has_a_distinct_name() -> None:
    names = [plugin.name for plugin in all_plugins()]
    assert len(names) == len(set(names))
    assert len(names) == 10


def test_registering_the_same_name_twice_is_an_error() -> None:
    registry = Registry(all_plugins())
    with pytest.raises(ValueError):
        registry.register(all_plugins()[0])


def test_an_unknown_plugin_name_is_refused_not_ignored() -> None:
    with pytest.raises(ValueError):
        default_registry().select(["no-such-plugin"])


def test_rewriting_plugins_are_off_by_default() -> None:
    """Anything that changes the author's words needs to be asked for."""
    defaults = {plugin.name for plugin in default_registry().select()}
    assert "academic" not in defaults
    assert "grammar" in defaults


def test_a_failing_plugin_does_not_cost_the_others() -> None:
    class Exploding(SuggestionPlugin):
        name = "exploding"
        title = "Exploding"

        def run(self, context):
            raise RuntimeError("boom")

    registry = Registry(all_plugins())
    registry.register(Exploding())
    from document_engine.model.nodes import Document

    review = DocumentAssistant(registry).review(Document(), ALL + ["exploding"])
    failed = [run for run in review.plugins if run.error]
    assert [run.name for run in failed] == ["exploding"]
    assert "boom" in failed[0].error
    assert not review.ok


def test_the_null_provider_runs_and_finds_nothing() -> None:
    """The seam a real assistant plugs into is exercised on every run."""
    from document_engine.model.nodes import Document

    assistant = DocumentAssistant(Registry(), provider=NullProvider())
    plugin = assistant.registry.get("ai:null")
    assert isinstance(plugin, ProviderPlugin)
    assert plugin.enabled_by_default is False
    review = assistant.review(Document(), ["ai:null"])
    assert len(review.suggestions) == 0 and review.ok


# -- what a review contains -----------------------------------------------


def test_every_suggestion_is_reviewable(paper) -> None:
    """Node, original, suggested, reason, confidence -- the stated contract."""
    _, _, review = _review(paper)
    for suggestion in review.suggestions:
        assert suggestion.node_id
        assert suggestion.original and suggestion.suggested
        assert suggestion.original != suggestion.suggested
        assert suggestion.reason.strip()
        assert 0.0 <= suggestion.confidence <= 1.0
        assert suggestion.source in ALL
        assert suggestion.status == "pending"


def test_no_plugin_proposes_a_no_op(paper) -> None:
    _, _, review = _review(paper)
    assert not [s for s in review.suggestions if s.is_noop]


def test_every_suggestion_quotes_the_document(paper) -> None:
    """The one mistake that would make suggestions unapplyable in bulk."""
    _, document, review = _review(paper)
    nodes = {node.id: node for node in document._every_node()}
    for suggestion in review.suggestions:
        node = nodes.get(suggestion.node_id)
        assert node is not None, f"{suggestion.source} proposed against a stranger"
        assert editable_text(node) == suggestion.original


def test_a_note_is_not_smuggled_in_as_a_suggestion(paper) -> None:
    _, _, review = _review(paper)
    for note in review.notes:
        assert note.plugin in ALL
        assert note.message.strip()
        assert note.severity in ("info", "warning")


def test_the_review_is_the_same_twice(paper) -> None:
    _, _, first = _review(paper)
    _, _, second = _review(paper)
    assert [s.id for s in first.suggestions] == [s.id for s in second.suggestions]
    assert [n.as_dict() for n in first.notes] == [n.as_dict() for n in second.notes]


def test_reviewing_changes_nothing(paper) -> None:
    engine = PreviewEngine.open(paper)
    before = dict(engine._entries)
    document = engine.analyze(source=paper.name)
    DocumentAssistant(default_registry()).review(document, ALL)
    for name, data in before.items():
        assert engine._entries[name] is data


# -- and that the editing engine accepts all of it ------------------------


def test_everything_proposed_can_actually_be_applied(paper) -> None:
    engine, _, review = _review(paper)
    chosen = _one_per_node(review)
    if not len(chosen):
        pytest.skip("this document has nothing to suggest")
    chosen.accept_all()
    preview = engine.preview(chosen, source=paper.name)
    assert not preview.result.refused, [r.reason for r in preview.result.refused]
    assert len(preview.result.applied) == len(chosen)


def test_applying_a_whole_review_touches_one_part_only(paper) -> None:
    engine, _, review = _review(paper)
    chosen = _one_per_node(review)
    if not len(chosen):
        pytest.skip("this document has nothing to suggest")
    chosen.accept_all()
    preview = engine.preview(chosen, source=paper.name)
    changed = [item.name for item in preview.impact if item.changed]
    assert changed == ["word/document.xml"]
    assert preview.parts_untouched == preview.parts_total - 1


def test_the_edited_document_still_parses_as_itself(paper) -> None:
    import io
    import zipfile

    engine, document, review = _review(paper)
    chosen = _one_per_node(review)
    if not len(chosen):
        pytest.skip("this document has nothing to suggest")
    chosen.accept_all()
    data = engine.preview(chosen, source=paper.name).to_bytes()
    archive = zipfile.ZipFile(io.BytesIO(data))
    assert archive.testzip() is None
    reread = PreviewEngine(
        {name: archive.read(name) for name in archive.namelist()},
        archive.namelist(),
    ).analyze()
    assert len(list(reread.all_sections())) == len(list(document.all_sections()))
    assert len(reread.tables) == len(document.tables)
    assert len(reread.figures) == len(document.figures)
    assert len(reread.references) == len(document.references)


def test_accepting_the_same_review_twice_gives_the_same_bytes(paper) -> None:
    engine, _, review = _review(paper)
    chosen = _one_per_node(review)
    if not len(chosen):
        pytest.skip("this document has nothing to suggest")
    chosen.accept_all()
    first = engine.preview(chosen, source=paper.name).to_bytes()
    second = engine.preview(
        SuggestionSet.from_list(chosen.as_list()), source=paper.name
    ).to_bytes()
    assert hashlib.sha1(first).hexdigest() == hashlib.sha1(second).hexdigest()


def test_nothing_is_written_by_a_review_alone(paper) -> None:
    """A suggestion is a proposal until somebody accepts it."""
    engine, _, review = _review(paper)
    preview = engine.preview(review.suggestions, source=paper.name)
    assert preview.result.applied == []
    assert preview.parts_untouched == preview.parts_total


def test_two_disjoint_edits_to_one_node_both_apply(paper) -> None:
    """Two plugins may touch one paragraph without colliding.

    The writer diffs each suggestion against the *same* original text, so an
    edit at the head and an edit at the tail produce spans that do not meet and
    both land.  Refusing them would be the bug: the author accepted both.
    """
    engine, document, _ = _review(paper)
    title = document.metadata.title
    if title is None or not editable_text(title).strip():
        pytest.skip("no title")
    original = editable_text(title)
    suggestions = SuggestionSet()
    suggestions.propose(title.id, original, original + " A", kind="tail")
    suggestions.propose(title.id, original, "B " + original, kind="head")
    suggestions.accept_all()
    preview = engine.preview(suggestions, source=paper.name)
    assert not preview.result.refused, [r.reason for r in preview.result.refused]
    assert len(preview.result.applied) == 2


def test_two_overlapping_edits_to_one_node_refuse_rather_than_collide(paper) -> None:
    """Two rewrites of the same characters: the second is refused, not merged."""
    engine, document, _ = _review(paper)
    title = document.metadata.title
    if title is None:
        pytest.skip("no title")
    original = editable_text(title)
    head = original.split(" ", 1)[0]
    if len(head) < 3:
        pytest.skip("title has no word long enough to rewrite twice")
    suggestions = SuggestionSet()
    # Both rewrite the same leading word, so their spans cannot help but meet.
    suggestions.propose(title.id, original, "Xx" + original[len(head):], kind="one")
    suggestions.propose(title.id, original, "Yy" + original[len(head):], kind="two")
    suggestions.accept_all()
    preview = engine.preview(suggestions, source=paper.name)
    assert len(preview.result.applied) == 1
    assert len(preview.result.refused) == 1
    assert "overlap" in preview.result.refused[0].reason


# -- the rules that must not be document-specific -------------------------


def test_consistency_follows_the_document_not_a_dictionary() -> None:
    """A majority is required, and a tie decides nothing."""
    assert _majority({"organise": 3, "organize": 1}) == "organise"
    assert _majority({"organise": 1, "organize": 3}) == "organize"
    assert _majority({"organise": 2, "organize": 2}) is None
    assert _majority({"organise": 4}) is None
    assert _spelling_key("organise") == _spelling_key("organize")
    assert _spelling_key("behaviour") == _spelling_key("behavior")


def test_heading_case_is_recognised_and_converted() -> None:
    assert _style_of("Results and Discussion") == "title"
    assert _style_of("Results and discussion") == "sentence"
    assert _style_of("RESULTS AND DISCUSSION") == "upper"
    assert _to_title("2. results and discussion") == "2. Results and Discussion"
    assert _to_sentence("2. Results and Discussion") == "2. Results and discussion"
    # An acronym survives both directions.
    assert _to_sentence("Attacks on MANET Routing") == "Attacks on MANET routing"


def test_no_plugin_hardcodes_anything_from_the_sample_documents() -> None:
    """The genericity rule, checked rather than promised."""
    import ast
    import pathlib

    def _code_only(source: str) -> str:
        """The source with comments and docstrings removed.

        Prose may name a term as an illustration -- "Mobile Ad Hoc Network
        (MANET)" is the clearest way to explain what an acronym definition
        looks like.  Executable code may not, because that is where a rule
        stops being general.  Stripping by ``ast`` rather than by hunting for
        triple quotes is what makes the distinction reliable.
        """
        lines = source.splitlines()
        tree = ast.parse(source)
        blank = set()
        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            body = getattr(node, "body", None)
            if not body:
                continue
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                if isinstance(first.value.value, str):
                    blank.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
        kept = [
            line
            for number, line in enumerate(lines, start=1)
            if number not in blank and not line.lstrip().startswith("#")
        ]
        return "\n".join(kept)

    banned = ("manet", "dsr", "aodv", "normal_paper", "the_role", "with_charts")
    root = pathlib.Path(__file__).resolve().parent.parent / "document_engine" / "assist"
    for path in sorted(root.rglob("*.py")):
        code = _code_only(path.read_text(encoding="utf-8")).lower()
        for term in banned:
            assert term not in code, f"{path.name}: {term}"


def test_the_assistant_does_not_reach_the_production_pipeline() -> None:
    import app.services.document_analyzer as analyzer

    with open(analyzer.__file__, "r", encoding="utf-8") as handle:
        body = handle.read()
    assert "document_engine" not in body and "assist" not in body
