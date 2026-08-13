"""Regression tests for citation unification.

The defect class these guard against is the worst kind the converter can
produce: a document that compiles cleanly and is wrong.  A citation key written
one way in the body and another way in the reference list gives a PDF full of
``[?]``; a range silently dropped gives a paper that cites four sources where
the author cited five.  Neither raises an error anywhere.

The keys asserted here are the *shipped defaults*.  Where a test pins a
particular spelling it also says why, and the override path is tested beside it
so a template that needs different keys is covered too.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engines.citation_engine import CitationEngine  # noqa: E402
from app.engines.journal_rules import JournalRulesResolver  # noqa: E402
from app.services.citation_mapper import CitationMapper  # noqa: E402


_REFS = [
    "[1] Roe, J. (2019). Alpha. J. Things 3, 1-9.",
    "[2] Doe, A. (2020). Beta. J. Stuff 4, 10-20.",
    "[3] Poe, B. (2021). Gamma. J. Other 5, 21-30.",
    "[4] Moe, C. (2022). Delta. J. More 6, 31-40.",
    "[5] Noe, D. (2023). Epsilon. J. Extra 7, 41-50.",
]


def _rules(**declared):
    return JournalRulesResolver().resolve({"rules": declared} if declared else {})


def _render(text, refs=_REFS, rules=None):
    rules = rules or _rules()
    engine = CitationEngine()
    return engine.render(text, engine.analyse(refs, text, rules), rules)


# --------------------------------------------------------------------- #
# The forms
# --------------------------------------------------------------------- #

def test_a_single_bracketed_citation():
    assert _render("as shown in [1].") == "as shown in \\cite{1}."


def test_a_bracketed_list():
    assert _render("as shown in [1,3].") == "as shown in \\cite{1,3}."


def test_a_bracketed_list_with_spaces():
    """Word puts a space after the comma as often as not."""
    assert _render("as shown in [1, 3].") == "as shown in \\cite{1,3}."


def test_a_bracketed_range_is_expanded():
    """[1-5] names five references, and the emitted key list must name all
    five: a class that collapses them back to "1--5" can only do so if it was
    told about every one."""
    assert _render("as shown in [1-5].") == "as shown in \\cite{1,2,3,4,5}."


def test_an_en_dash_range_is_expanded_too():
    """Word autocorrects a typed hyphen into an en dash inside number ranges,
    so the two spellings must behave identically."""
    assert _render("see [1–5].") == _render("see [1-5].")


def test_a_parenthesised_citation():
    assert _render("as shown in (1).") == "as shown in \\cite{1}."


def test_a_parenthesised_list():
    assert _render("as shown in (1,3).") == "as shown in \\cite{1,3}."


def test_a_mixed_group_of_singles_and_ranges():
    assert _render("see [1,3-5].") == "see \\cite{1,3,4,5}."


def test_a_superscript_citation():
    out = _render("as shown\\textsuperscript{2} here.")
    assert "\\cite{2}" in out


def test_a_hyperlinked_citation():
    """Word's cross-reference-to-bibliography produces a link whose visible
    text is the bracketed number."""
    out = _render("as shown in \\href{#ref3}{[3]}.")
    assert out == "as shown in \\cite{3}."


def test_several_forms_in_one_document():
    out = _render("First [1], then (2), then [3-5], then \\textsuperscript{2}.")
    for expected in ("\\cite{1}", "\\cite{2}", "\\cite{3,4,5}"):
        assert expected in out, expected


def test_surrounding_prose_is_preserved_exactly():
    text = "Before the citation [2] and after it, with punctuation; and more."
    out = _render(text)
    assert out.startswith("Before the citation ")
    assert out.endswith(" and after it, with punctuation; and more.")


# --------------------------------------------------------------------- #
# What must NOT become a citation
# --------------------------------------------------------------------- #

def test_a_page_range_is_not_a_citation():
    assert _render("see pages [100-200].") == "see pages [100-200]."


def test_a_year_in_parentheses_is_not_a_citation():
    assert _render("published in (2019).") == "published in (2019)."


def test_an_equation_number_is_not_rewritten():
    """Equation numbers are set by \\tag, outside the prose the engine scans;
    a bare "(12)" following an equation must survive untouched."""
    assert _render("as in (12) above.", refs=_REFS[:3]) == "as in (12) above."


def test_a_number_naming_no_reference_is_left_visible():
    """Rendering it would produce a "[?]" in the PDF and bury the defect in
    the compilation log; left alone it stays where the report can point at it."""
    assert _render("see [9].") == "see [9]."


def test_a_table_number_in_prose_is_untouched():
    assert "Table 2" in _render("as Table 2 shows.")


# --------------------------------------------------------------------- #
# Keys: the guarantee that citations and the bibliography cannot drift
# --------------------------------------------------------------------- #

def test_the_default_key_is_the_reference_number():
    """So the generated LaTeX reads the way the manuscript did, and an author
    reviewing main.tex can check a citation without a lookup table."""
    rules = _rules()
    assert rules.bibliography.key_for(1) == "1"
    assert rules.bibliography.key_for(12) == "12"


def test_a_template_can_still_choose_another_prefix():
    """Backward compatibility: a class or a hand-maintained .bib that needs
    alphabetic keys sets a prefix, and everything downstream follows."""
    rules = _rules(bibliography={"key_prefix": "ref"})
    assert rules.bibliography.key_for(1) == "ref1"
    assert _render("see [1,2].", rules=rules) == "see \\cite{ref1,ref2}."


def test_the_engine_and_the_bibliography_use_the_same_function():
    """The whole point of the phase.

    The key is written in two distant places -- the \\cite in the body and the
    \\bibitem in the reference list.  Before unification each computed it with
    its own copy of the same expression, in different modules, and they agreed
    only by coincidence.
    """
    for prefix in ("", "ref", "bib-"):
        rules = _rules(bibliography={"key_prefix": prefix} if prefix else {})
        engine = CitationEngine()
        entries = engine.build_bibliography(_REFS, rules)
        for position, entry in enumerate(entries, start=1):
            # What the renderer writes into \bibitem:
            rendered_key = rules.bibliography.key_for(position)
            assert entry.key == rendered_key, (prefix, position)


def test_every_emitted_citation_key_exists_in_the_bibliography():
    """No \\cite may name a key no \\bibitem will define."""
    rules = _rules()
    engine = CitationEngine()
    text = "Citing [1], [2,4], [1-5] and (3)."
    analysis = engine.analyse(_REFS, text, rules)
    bibitem_keys = {rules.bibliography.key_for(i)
                    for i in range(1, len(analysis.entries) + 1)}
    for citation in analysis.citations:
        for key in citation.keys:
            assert key in bibitem_keys, key


def test_a_key_is_position_not_the_number_word_printed():
    """A list numbered 1, 2, 3, 6 still typesets as four consecutive entries.

    The fourth entry's key must therefore be 4 -- matching where \\bibitem
    actually puts it -- while a citation that says "[6]" must still resolve to
    it.  Keying by the printed number would produce \\cite{6} against
    \\bibitem{4}.
    """
    refs = ["[1] Alpha.", "[2] Beta.", "[3] Gamma.", "[6] Zeta."]
    rules = _rules()
    engine = CitationEngine()
    analysis = engine.analyse(refs, "see [6].", rules)
    assert [e.key for e in analysis.entries] == ["1", "2", "3", "4"]
    assert analysis.citations[0].keys == ("4",)
    assert engine.render("see [6].", analysis, rules) == "see \\cite{4}."


def test_no_citation_is_silently_lost():
    """Every detected citation either becomes a command or survives verbatim.

    A citation that vanished would be undetectable in the output: the sentence
    still reads, and nothing reports it.
    """
    text = "Claims [1], [2,3], [4-5], (1) and \\textsuperscript{2} appear here."
    engine = CitationEngine()
    rules = _rules()
    analysis = engine.analyse(_REFS, text, rules)
    out = engine.render(text, analysis, rules)
    assert out.count("\\cite{") == len([c for c in analysis.citations
                                        if c.resolved])
    cited = {k for c in analysis.citations for k in c.keys}
    for key in cited:
        assert ("{" + key + "}") in out or ("," + key) in out \
            or ("{" + key + ",") in out, key


# --------------------------------------------------------------------- #
# The adapter: existing callers must be unaffected
# --------------------------------------------------------------------- #

def _doc(refs=_REFS):
    return SimpleNamespace(references=list(refs))


def test_the_mapper_keeps_its_three_argument_signature(tmp_path):
    """The renderer has always called it with three positional arguments, and
    a service that changes its own call signature breaks every caller."""
    out, report = CitationMapper().map_citations(_doc(), "see [1].", tmp_path)
    assert out == "see \\cite{1}."
    assert isinstance(report, dict)


def test_the_report_keeps_every_key_it_had(tmp_path):
    _, report = CitationMapper().map_citations(_doc(), "see [1] and [9].",
                                               tmp_path)
    for key in ("total_citations", "mapped_citations", "broken_citations",
                "unused_bibliography", "duplicated_bibliography",
                "missing_bibliography", "citation_style_detected"):
        assert key in report, key
    assert report["total_citations"] == 2
    assert report["mapped_citations"] == 1
    assert report["broken_citations"] == 1


def test_the_report_is_still_written_where_it_was(tmp_path):
    CitationMapper().map_citations(_doc(), "see [1].", tmp_path / "intermediate")
    written = tmp_path / "intermediate" / "citation_report.json"
    assert written.is_file()
    assert json.loads(written.read_text(encoding="utf-8"))["total_citations"] == 1


def test_the_style_names_are_the_ones_callers_already_recognise(tmp_path):
    _, report = CitationMapper().map_citations(_doc(), "see [1].", tmp_path)
    assert report["citation_style_detected"] == "Numbered (IEEE/Vancouver)"
    _, report = CitationMapper().map_citations(
        _doc(), "as Roe (2019) showed.", tmp_path)
    assert report["citation_style_detected"] == "Author-Date (APA/Harvard)"


def test_uncited_references_are_reported_by_key(tmp_path):
    _, report = CitationMapper().map_citations(_doc(), "see [1].", tmp_path)
    assert report["unused_bibliography"] == ["2", "3", "4", "5"]


def test_a_document_with_no_references_does_not_crash(tmp_path):
    out, report = CitationMapper().map_citations(
        _doc([]), "prose with [1] in it.", tmp_path)
    assert out == "prose with [1] in it."
    assert report["total_citations"] >= 0


def test_the_mapper_accepts_rules_and_honours_them(tmp_path):
    """How the renderer guarantees the keys match: it resolves the rules once
    and hands the same object to the mapper and to the bibliography."""
    rules = _rules(bibliography={"key_prefix": "ref"},
                   citation={"command": "mycite"})
    out, _ = CitationMapper().map_citations(_doc(), "see [1,2].", tmp_path,
                                            rules)
    assert out == "see \\mycite{ref1,ref2}."


def test_there_is_only_one_citation_implementation():
    """The mapper must delegate, not re-implement.

    Two answers to "which reference does this name" is one too many; they
    disagreed about ranges, bare years and superscripts before unification.
    """
    source = Path(__file__).resolve().parents[1] / \
        "app" / "services" / "citation_mapper.py"
    text = source.read_text(encoding="utf-8")
    assert "CitationEngine" in text
    # No citation command may be built in the adapter: that decision belongs
    # to the engine, which asks the rules.
    assert "\\\\cite" not in text and '"\\\\citep{"' not in text
    assert "re.sub" not in text


if __name__ == "__main__":
    import inspect
    import tempfile
    import traceback

    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not (name.startswith("test_") and callable(fn)):
            continue
        with tempfile.TemporaryDirectory() as td:
            kwargs = {"tmp_path": Path(td)} \
                if "tmp_path" in inspect.signature(fn).parameters else {}
            try:
                fn(**kwargs)
                print(f"PASS {name}")
                passed += 1
            except Exception:
                print(f"FAIL {name}")
                traceback.print_exc()
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
