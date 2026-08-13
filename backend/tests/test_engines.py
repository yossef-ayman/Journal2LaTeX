"""Tests for the conversion engines.

Each test names the real failure it prevents.  The inputs are synthetic
because the point is to pin a *behaviour*, not a document: a test built from
one publisher's paper only proves that paper still works, and every one of
these behaviours has to hold for Springer, IEEE, Elsevier, MDPI, a thesis and
an arbitrary Word file alike.

Run directly (``python test_engines.py``) or under pytest.
"""

import sys
import zipfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engines.citation_engine import CitationEngine  # noqa: E402
from app.engines.crossref_engine import CrossReferenceEngine  # noqa: E402
from app.engines.journal_rules import (  # noqa: E402
    JournalRulesResolver, BIOGRAPHY_LAYOUTS,
)
from app.engines.latex_log import LatexLogParser, parse_log  # noqa: E402
from app.engines.validation import DeliveryValidator  # noqa: E402


# --------------------------------------------------------------------- #
# JournalRules
# --------------------------------------------------------------------- #

def test_a_template_with_no_rules_still_resolves():
    """Every template that exists today has no rules block.

    The resolver has to be total, or adding it to the pipeline breaks every
    conversion that worked the day before.
    """
    rules = JournalRulesResolver().resolve({})
    assert rules.citation.style == "numeric"
    assert rules.bibliography.mode == "inline"
    assert rules.biography.layouts[-1] == "plain"


def test_declared_rules_beat_inferred_ones():
    """A human's explicit answer must be able to correct the engine's guess."""
    rules = JournalRulesResolver().resolve({
        "template_id": "x",
        "rules": {"citation": {"style": "superscript", "command": "supercite",
                               "group_multiple": False}},
    })
    assert rules.citation.style == "superscript"
    assert rules.citation.command == "supercite"
    assert rules.citation.group_multiple is False
    assert rules.provenance["citation"] == "declared"


def test_a_biography_layout_chain_always_ends_in_something_that_typesets():
    """A chain that can run out leaves a biography unrendered.

    A biography set plainly is worse than one wrapped elegantly and better
    than one that is missing, so 'plain' terminates every chain whether or not
    the template remembered to list it.
    """
    rules = JournalRulesResolver().resolve(
        {"rules": {"biography": {"layouts": ["wrapfigure"]}}})
    assert rules.biography.layouts[-1] == "plain"
    assert all(l in BIOGRAPHY_LAYOUTS for l in rules.biography.layouts)


def test_rules_are_inferred_from_what_the_template_provides_not_its_name(tmp_path):
    """The replacement for ``"NSP" in class_file``.

    A class that defines a photo biography environment is offering that
    layout, whatever the journal is called; a class that is renamed or forked
    keeps working, and a class whose name merely contains the same letters
    does not get someone else's layout.
    """
    (tmp_path / "journal.cls").write_text(
        r"\newenvironment{biographyps}[2]{}{}"
        "\n" r"\RequirePackage{natbib}"
        "\n" r"\RequirePackage{wrapfig}",
        encoding="utf-8")
    rules = JournalRulesResolver().resolve({}, tmp_path)
    assert rules.biography.photo_environment == "biographyps"
    assert rules.biography.layouts[0] == "journal_env"
    assert "wrapfigure" in rules.biography.layouts
    assert rules.provenance["biography"] == "probed"


def test_an_unreadable_template_directory_does_not_break_resolution(tmp_path):
    rules = JournalRulesResolver().resolve({}, tmp_path / "does_not_exist")
    assert rules.citation.command == "cite"


# --------------------------------------------------------------------- #
# LaTeX log
# --------------------------------------------------------------------- #

_LOG = """This is pdfTeX, Version 3.141592653
LaTeX Warning: Reference `fig:nope' on page 1 undefined on input line 5.
LaTeX Warning: Citation `ghost' on page 1 undefined on input line 5.
LaTeX Warning: Label `sec:intro' multiply defined.
Overfull \\hbox (34.5pt too wide) in paragraph at lines 12--14
Underfull \\vbox (badness 4321) has occurred while \\output is active
LaTeX Warning: Float too large for page by 22.4pt on input line 30.
Missing character: There is no ✓ in font cmr10!
Output written on main.pdf (7 pages, 123456 bytes).
"""


def test_the_log_parser_finds_every_category():
    report = LatexLogParser().parse_text(_LOG)
    kinds = {d.category for d in report.diagnostics}
    for expected in ("undefined_reference", "undefined_citation",
                     "multiply_defined_label", "overfull_hbox",
                     "underfull_vbox", "float_too_large", "missing_character"):
        assert expected in kinds, expected
    assert report.pages == 7
    assert report.worst_overflow_pt() == 34.5


def test_wrapped_log_lines_are_rejoined_before_matching():
    """TeX hard-wraps at 79 columns, mid-message.

    This is the classic reason a log parser reports a suspiciously clean
    document: the warning is there, split across two lines, and every
    line-anchored pattern misses it.
    """
    message = ("LaTeX Warning: Reference `a-very-long-label-name-goes-here' "
               "on page 1 undefined on input line 42.")
    head, tail = message[:79], message[79:]
    assert len(head) == 79
    report = LatexLogParser().parse_text(head + "\n" + tail + "\n")
    assert [d.target for d in report.of("undefined_reference")] == \
        ["a-very-long-label-name-goes-here"]


def test_unwrapping_does_not_swallow_the_line_after_a_long_one():
    """The failure mode of a naive unwrapper.

    Once two segments are joined the result exceeds the wrap width forever, so
    a rule that tests the accumulated line collapses the whole log into one
    line and finds nothing at all.
    """
    filler = "x" * 79
    report = LatexLogParser().parse_text(
        filler + "\n" + filler + "\n"
        "LaTeX Warning: Citation `key' on page 2 undefined on input line 9.\n")
    assert [d.target for d in report.of("undefined_citation")] == ["key"]


def test_a_missing_log_is_reported_as_unknown_not_as_clean():
    report = parse_log(Path("/nonexistent/main.log"))
    assert report.parsed is False
    assert report.diagnostics == []


def test_an_overfull_box_outranks_an_underfull_one():
    """Overfull puts ink in the margin; underfull only stretches white space.

    Ranking them equally buries the visible defects in a long document.
    """
    report = LatexLogParser().parse_text(_LOG)
    overfull = report.of("overfull_hbox")[0]
    underfull = report.of("underfull_vbox")[0]
    assert overfull.severity == "warning"
    assert underfull.severity == "info"


# --------------------------------------------------------------------- #
# Citation Engine
# --------------------------------------------------------------------- #

_REFS = ["[1] Roe, J. (2019). Alpha.", "[2] Doe, A. (2020). Beta.",
         "[3] Poe, B. (2021). Gamma.", "[4] Moe, C. (2022). Delta."]


def test_every_word_citation_shape_is_detected():
    forms = {c.form for c in CitationEngine().detect(
        r"[1] and [2,4] and [2-4] and (1) and \textsuperscript{3} "
        r"and (Roe, 2019) and Doe (2020) and \href{u}{[3]}")}
    for expected in ("bracket_numeric", "paren_numeric", "superscript",
                     "paren_author_year", "narrative", "hyperlink"):
        assert expected in forms, expected


def test_a_range_is_expanded_into_the_references_it_names():
    citation = [c for c in CitationEngine().detect("see [2-4]")][0]
    assert citation.numbers == (2, 3, 4)


def test_a_page_range_is_not_a_citation():
    """[100-200] is a page span, and expanding it invents 101 citations."""
    assert CitationEngine().detect("pages [100-200]") == []


def test_a_bracketed_year_is_not_a_citation_number():
    """No reference list has two thousand entries.

    Reading "(2020)" as a citation manufactures a missing-reference error for
    text that is perfectly correct, which is worse than missing a citation:
    it puts noise in the report the reader is meant to trust.
    """
    assert not [c for c in CitationEngine().detect("published in (2020)")
                if c.numbers]


def test_a_narrative_citation_wins_over_the_bare_year_inside_it():
    """"Doe (2020)" is one citation, not a number and a name.

    The numeric detector reaching the parenthesis first would read it as a
    citation to reference number 2020.
    """
    citations = CitationEngine().detect("as Doe (2020) showed")
    assert [c.form for c in citations] == ["narrative"]


def test_citations_resolve_to_bibliography_keys():
    analysis = CitationEngine().analyse(_REFS, "see [1] and [3]")
    keys = [k for c in analysis.citations for k in c.keys]
    assert keys == ["1", "3"]


def test_a_citation_with_no_reference_is_an_error():
    analysis = CitationEngine().analyse(_REFS, "see [9]")
    assert not analysis.ok
    assert any(i.kind == "missing_reference" for i in analysis.issues)


def test_duplicate_reference_numbering_is_detected():
    analysis = CitationEngine().analyse(
        ["[1] Alpha.", "[1] Beta.", "[2] Gamma."], "see [1]")
    assert any(i.kind == "duplicate_numbering" and i.severity == "error"
               for i in analysis.issues)


def test_unused_references_are_reported():
    analysis = CitationEngine().analyse(_REFS, "see [1]")
    issue = next(i for i in analysis.issues if i.kind == "unused_reference")
    assert issue.severity == "warning"


def test_a_gap_in_the_cited_numbers_is_a_broken_sequence():
    analysis = CitationEngine().analyse(_REFS, "see [1] then [4]")
    assert any(i.kind == "broken_sequence" for i in analysis.issues)


def test_references_numbered_out_of_first_use_order_are_reported():
    analysis = CitationEngine().analyse(_REFS, "see [3] then [1] then [2]")
    assert any(i.kind == "out_of_order_numbering" for i in analysis.issues)


def test_the_renderer_never_hardcodes_cite():
    """The whole point of the rules layer.

    Every command in the output has to come from the journal's declared rules;
    if any of them is baked in, a journal that spells it differently silently
    gets the wrong one.
    """
    engine = CitationEngine()
    rules = JournalRulesResolver().resolve(
        {"rules": {"citation": {"command": "mycite"}}})
    analysis = engine.analyse(_REFS, "see [1,2]", rules)
    assert engine.render("see [1,2]", analysis, rules) == r"see \mycite{1,2}"


def test_author_year_rendering_distinguishes_the_two_shapes():
    """(Roe, 2019) is an aside; Roe (2019) is the subject of the sentence.

    Swapping the two makes the prose ungrammatical, so they cannot share a
    command.
    """
    engine = CitationEngine()
    rules = JournalRulesResolver().resolve(
        {"rules": {"citation": {"style": "author_year"}}})
    text = "as (Roe, 2019) and Doe (2020) showed"
    out = engine.render(text, engine.analyse(_REFS, text, rules), rules)
    assert r"\citep{1}" in out
    assert r"\citet{2}" in out


def test_ungrouped_rendering_emits_one_command_per_key():
    engine = CitationEngine()
    rules = JournalRulesResolver().resolve(
        {"rules": {"citation": {"group_multiple": False}}})
    out = engine.render("see [1,2]", engine.analyse(_REFS, "see [1,2]", rules),
                        rules)
    assert out == r"see \cite{1}\cite{2}"


def test_superscript_rendering_wraps_the_command():
    engine = CitationEngine()
    rules = JournalRulesResolver().resolve(
        {"rules": {"citation": {"style": "superscript"}}})
    out = engine.render("see [1]", engine.analyse(_REFS, "see [1]", rules), rules)
    assert out == r"see \textsuperscript{\cite{1}}"


def test_an_unresolved_citation_is_left_visible_rather_than_rendered():
    """Rendering it would bury the defect in the compilation log.

    Left as the author wrote it, it stays where the validation report can
    point at it.
    """
    engine = CitationEngine()
    rules = JournalRulesResolver().resolve({})
    out = engine.render("see [9]", engine.analyse(_REFS, "see [9]", rules), rules)
    assert out == "see [9]"


def test_already_rendered_commands_are_recognised_not_re_rendered():
    """The engine also runs over LaTeX during validation.

    A document whose citations are all already correct would otherwise be
    reported as having no citations and every reference as uncited -- the most
    misleading report the engine could produce.
    """
    engine = CitationEngine()
    rules = JournalRulesResolver().resolve({})
    text = r"see \cite{1} and \cite{2,3}"
    analysis = engine.analyse(_REFS, text, rules)
    assert [c.form for c in analysis.citations] == ["command", "command"]
    assert not any(i.kind == "no_citations" for i in analysis.issues)
    assert engine.render(text, analysis, rules) == text


# --------------------------------------------------------------------- #
# Cross Reference Engine
# --------------------------------------------------------------------- #

def _project(tmp_path, body):
    path = tmp_path / "main.tex"
    path.write_text("\\documentclass{article}\n\\begin{document}\n"
                    + body + "\n\\end{document}\n", encoding="utf-8")
    return path


def test_a_reference_to_a_missing_label_is_an_error(tmp_path):
    analysis = CrossReferenceEngine().analyse(
        _project(tmp_path, r"See Fig.~\ref{fig:nope}."))
    assert not analysis.ok
    assert any(i.kind == "undefined_reference" for i in analysis.issues)


def test_a_duplicate_label_is_an_error(tmp_path):
    """LaTeX keeps the last one and silently misdirects every earlier
    reference; nothing in the PDF distinguishes this from a correct document."""
    analysis = CrossReferenceEngine().analyse(
        _project(tmp_path, r"\label{a}\label{a}\ref{a}"))
    assert any(i.kind == "duplicate_label" and i.severity == "error"
               for i in analysis.issues)


def test_the_whole_ref_family_counts_as_a_reference(tmp_path):
    """A document written with \\cref would otherwise appear to have no
    references at all, and every label would be reported as unused."""
    analysis = CrossReferenceEngine().analyse(
        _project(tmp_path, r"\label{fig:a}\Cref{fig:a}\eqref{fig:a}"))
    assert not any(i.kind == "unreferenced_object" for i in analysis.issues)
    assert len(analysis.references) == 2


def test_a_commented_out_reference_is_not_a_reference(tmp_path):
    analysis = CrossReferenceEngine().analyse(
        _project(tmp_path, "% \\ref{fig:nope}\ntext"))
    assert analysis.ok


def test_an_escaped_percent_does_not_start_a_comment(tmp_path):
    analysis = CrossReferenceEngine().analyse(
        _project(tmp_path, r"100\% of \ref{fig:nope}"))
    assert any(i.kind == "undefined_reference" for i in analysis.issues)


def test_labels_in_included_files_are_found(tmp_path):
    """A project split across files would otherwise look almost unlabelled."""
    (tmp_path / "body.tex").write_text(r"\label{fig:a}", encoding="utf-8")
    analysis = CrossReferenceEngine().analyse(
        _project(tmp_path, r"\input{body}\ref{fig:a}"))
    assert analysis.ok


def test_a_circular_include_terminates(tmp_path):
    (tmp_path / "a.tex").write_text(r"\input{main}", encoding="utf-8")
    analysis = CrossReferenceEngine().analyse(_project(tmp_path, r"\input{a}"))
    assert analysis is not None


def test_an_unlabelled_figure_is_reported_against_the_document_model(tmp_path):
    """Valid LaTeX, invisible to the compiler, impossible to reference.

    Only the parsed model knows the paper has three figures.
    """
    analysis = CrossReferenceEngine().analyse(
        _project(tmp_path, r"\label{fig:a}\ref{fig:a}"),
        expected={"figure": 3})
    issue = next(i for i in analysis.issues if i.kind == "unlabelled_object")
    assert issue.detail["objects"] == 3 and issue.detail["labels"] == 1


def test_a_label_is_classified_by_its_enclosing_environment(tmp_path):
    """Template boilerplate labels carry no prefix."""
    analysis = CrossReferenceEngine().analyse(
        _project(tmp_path, "\\begin{table}\\label{plain}\\end{table}"))
    assert [l.kind for l in analysis.labels] == ["table"]


def test_journal_declared_label_prefixes_are_honoured(tmp_path):
    rules = JournalRulesResolver().resolve(
        {"rules": {"labels": {"figure": "f:"}}})
    analysis = CrossReferenceEngine().analyse(
        _project(tmp_path, r"\label{f:a}"), rules)
    assert analysis.labels[0].kind == "figure"


# --------------------------------------------------------------------- #
# Delivery validation
# --------------------------------------------------------------------- #

def _block(kind, content=None):
    return SimpleNamespace(type=SimpleNamespace(value=kind),
                           content=content or {})


def _model(refs=(), blocks=()):
    return SimpleNamespace(references=list(refs),
                           sections=[SimpleNamespace(blocks=list(blocks))])


def _build(tmp_path, tex, media=None):
    rendered = tmp_path / "rendered"
    (rendered / "media").mkdir(parents=True)
    (rendered / "main.tex").write_text(tex, encoding="utf-8")
    for name, data in (media or {}).items():
        (rendered / "media" / name).write_bytes(data)
    return rendered


_PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)


def test_a_clean_project_passes(tmp_path):
    rendered = _build(tmp_path, "\\documentclass{article}\n\\begin{document}\n"
                                "\\includegraphics{media/a.png}\n"
                                "\\label{fig:a}\\ref{fig:a}\n"
                                "\\end{document}\n",
                      {"a.png": _PNG})
    report = DeliveryValidator().validate(rendered, _model())
    assert report.verdict in ("pass", "warn"), report.to_dict()["findings"]
    assert report.checks["labels"] == "pass"


def test_an_included_image_that_is_not_in_the_project_fails(tmp_path):
    """The commonest reason a downloaded archive fails on another machine."""
    rendered = _build(tmp_path, r"\includegraphics{media/gone.png}")
    report = DeliveryValidator().validate(rendered, _model())
    assert report.verdict == "fail"
    assert any(f.kind == "missing_image" for f in report.findings)


def test_an_extensionless_inclusion_resolves(tmp_path):
    """LaTeX tries known extensions; a checker that does not reports every
    correctly written inclusion as missing."""
    rendered = _build(tmp_path, r"\includegraphics{media/a}", {"a.png": _PNG})
    report = DeliveryValidator().validate(rendered, _model())
    assert not any(f.kind == "missing_image" for f in report.findings)


def test_a_file_whose_content_contradicts_its_extension_is_reported(tmp_path):
    """Word documents routinely carry a PNG saved as .jpg.

    LaTeX believes the extension and fails on the content.
    """
    rendered = _build(tmp_path, "text", {"a.jpg": _PNG})
    report = DeliveryValidator().validate(rendered, _model())
    assert any(f.kind == "wrong_extension" for f in report.findings)


def test_empty_and_duplicated_media_are_reported(tmp_path):
    rendered = _build(tmp_path, "text",
                      {"a.png": _PNG, "b.png": _PNG, "c.png": b""})
    report = DeliveryValidator().validate(rendered, _model())
    kinds = {f.kind for f in report.findings}
    assert "empty_media" in kinds and "duplicate_media" in kinds


def test_a_missing_log_does_not_read_as_a_clean_compile(tmp_path):
    rendered = _build(tmp_path, "text")
    report = DeliveryValidator().validate(rendered, _model(),
                                          log_path=tmp_path / "absent.log")
    assert any(f.kind == "log_unavailable" for f in report.findings)


def test_an_archive_with_escaping_paths_fails(tmp_path):
    rendered = _build(tmp_path, "text")
    archive = tmp_path / "p.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("main.tex", "text")
        zf.writestr("../escape.tex", "bad")
    report = DeliveryValidator().validate(rendered, _model(), zip_path=archive)
    assert report.verdict == "fail"
    assert any(f.kind == "unsafe_paths" for f in report.findings)


def test_an_archive_missing_project_files_is_reported(tmp_path):
    rendered = _build(tmp_path, "text", {"a.png": _PNG})
    archive = tmp_path / "p.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("main.tex", "text")
    report = DeliveryValidator().validate(rendered, _model(), zip_path=archive)
    assert any(f.kind == "incomplete_archive" for f in report.findings)


def test_the_compiled_pdf_is_not_expected_inside_the_archive(tmp_path):
    """It is a build product, not a source file."""
    rendered = _build(tmp_path, "text")
    (rendered / "main.pdf").write_bytes(b"%PDF-1.4")
    archive = tmp_path / "p.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("main.tex", "text")
    report = DeliveryValidator().validate(rendered, _model(), zip_path=archive)
    assert not any(f.kind == "incomplete_archive" for f in report.findings)


def test_an_equation_image_is_not_counted_as_a_figure(tmp_path):
    """Numbering it as one produces a figure list full of formulae."""
    rendered = _build(tmp_path, "text")
    model = _model(blocks=[_block("figure", {"is_equation": True}),
                           _block("figure")])
    report = DeliveryValidator().validate(rendered, model)
    assert report.stats["objects"] == {"figure": 1}


def test_the_validator_never_writes_to_the_project(tmp_path):
    """A validator that repairs cannot be trusted to report."""
    rendered = _build(tmp_path, r"\includegraphics{media/gone.png}",
                      {"a.png": _PNG})
    before = {p.relative_to(rendered).as_posix(): p.read_bytes()
              for p in rendered.rglob("*") if p.is_file()}
    DeliveryValidator().validate(rendered, _model())
    after = {p.relative_to(rendered).as_posix(): p.read_bytes()
             for p in rendered.rglob("*") if p.is_file()}
    assert before == after


def test_the_verdict_separates_deliverable_from_broken(tmp_path):
    """Collapsing warn and fail makes the report alarmist or useless."""
    clean = _build(tmp_path / "a", "text", {"x.png": _PNG})
    assert DeliveryValidator().validate(clean, _model()).verdict in ("pass", "warn")
    broken = _build(tmp_path / "b", r"\includegraphics{media/gone.png}")
    assert DeliveryValidator().validate(broken, _model()).verdict == "fail"


# --------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------- #

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
