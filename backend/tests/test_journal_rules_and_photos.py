"""Phase C regression tests: JournalRules adoption and author-photo rendering.

Two classes of defect are guarded here.

The first is a journal decision written in Python.  A test like
``"NSP" in class_file`` is invisible to whoever adds the next template,
impossible to override from a template, and wrong for any journal whose class
file happens to share those letters.  Every such decision now comes from the
resolved rules, and one test below asserts that no journal or class name
remains in the renderer at all.

The second is an author photograph treated as a manuscript figure.  It carries
no caption and illustrates a person rather than a result, so numbering one
shifts every real figure number in the paper and puts a portrait in the List of
Figures -- a defect that compiles cleanly and looks deliberate.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engines.journal_rules import (  # noqa: E402
    AUTHOR_PHOTO_MODES, AuthorPhotoRules, JournalRulesResolver,
    _defines_environment,
)


def _resolver():
    return JournalRulesResolver()


# --------------------------------------------------------------------- #
# 1-3. rules.json, template.json, and precedence between them
# --------------------------------------------------------------------- #

def test_rules_json_is_loaded(tmp_path):
    (tmp_path / "rules.json").write_text(json.dumps(
        {"author_photo": {"image_width": "2cm"},
         "citation": {"command": "mycite"}}), encoding="utf-8")
    rules = _resolver().resolve({}, tmp_path)
    assert rules.author_photo.image_width == "2cm"
    assert rules.citation.command == "mycite"


def test_rules_json_may_nest_under_a_rules_key(tmp_path):
    """Both shapes are what people actually write."""
    (tmp_path / "rules.json").write_text(json.dumps(
        {"rules": {"author_photo": {"image_width": "2cm"}}}), encoding="utf-8")
    assert _resolver().resolve({}, tmp_path).author_photo.image_width == "2cm"


def test_the_template_json_rules_block_still_works(tmp_path):
    """Backward compatibility: templates configured before rules.json existed
    must keep behaving identically."""
    rules = _resolver().resolve(
        {"rules": {"author_photo": {"image_width": "9cm"}}}, tmp_path)
    assert rules.author_photo.image_width == "9cm"


def test_rules_json_wins_over_the_template_json_block(tmp_path):
    """The documented precedence: rules.json > template.json > defaults."""
    (tmp_path / "rules.json").write_text(json.dumps(
        {"author_photo": {"image_width": "1cm"}}), encoding="utf-8")
    rules = _resolver().resolve(
        {"rules": {"author_photo": {"image_width": "9cm"}}}, tmp_path)
    assert rules.author_photo.image_width == "1cm"


def test_a_key_only_template_json_declares_is_still_honoured(tmp_path):
    """Each layer overwrites only what it actually declares, so a rules.json
    that sets one field does not silently reset the others."""
    (tmp_path / "rules.json").write_text(json.dumps(
        {"author_photo": {"image_width": "1cm"}}), encoding="utf-8")
    rules = _resolver().resolve(
        {"rules": {"author_photo": {"placement": "H", "image_width": "9cm"}}},
        tmp_path)
    assert rules.author_photo.image_width == "1cm"
    assert rules.author_photo.placement == "H"


def test_a_malformed_rules_file_does_not_fail_the_job(tmp_path):
    """A stray comma should not stop every conversion for that journal until
    somebody notices."""
    (tmp_path / "rules.json").write_text("{ not json,", encoding="utf-8")
    assert _resolver().resolve({}, tmp_path).author_photo.mode == "floatingfigure"


def test_a_template_with_no_configuration_at_all_still_resolves(tmp_path):
    """Every template that exists today has neither file."""
    rules = _resolver().resolve({}, tmp_path)
    assert rules.author_photo.mode in AUTHOR_PHOTO_MODES
    assert rules.citation.command == "cite"


# --------------------------------------------------------------------- #
# 4-5, 11. Author-photo configuration and the exact LaTeX produced
# --------------------------------------------------------------------- #

def test_the_default_author_photo_latex_is_exactly_the_required_format():
    """Pinned character for character, because the journal specified it."""
    out = AuthorPhotoRules().render("media/author_photo.jpg")
    assert out == (
        "\\begin{floatingfigure}[h]{3.5cm}\n"
        "\\centering\n"
        "\\includegraphics[width=3cm,height=3.4cm]{media/author_photo.jpg}\n"
        "\\end{floatingfigure}\n"
    )


def test_only_the_path_varies_between_documents():
    a = AuthorPhotoRules().render("media/one.jpg")
    b = AuthorPhotoRules().render("media/two.png")
    assert a.replace("one.jpg", "PATH") == b.replace("two.png", "PATH")


def test_every_dimension_comes_from_the_rules(tmp_path):
    (tmp_path / "rules.json").write_text(json.dumps({"author_photo": {
        "mode": "wrapfigure", "placement": "l", "column_width": "4cm",
        "image_width": "3.8cm", "image_height": "5cm", "keep_aspect": True,
    }}), encoding="utf-8")
    out = _resolver().resolve({}, tmp_path).author_photo.render("media/x.png")
    assert out == (
        "\\begin{wrapfigure}[l]{4cm}\n\\centering\n"
        "\\includegraphics[width=3.8cm,height=5cm,keepaspectratio]{media/x.png}\n"
        "\\end{wrapfigure}\n"
    )


def test_a_template_can_name_its_own_environment(tmp_path):
    (tmp_path / "rules.json").write_text(json.dumps(
        {"author_photo": {"mode": "floatingfigure",
                          "environment": "authorportrait"}}), encoding="utf-8")
    out = _resolver().resolve({}, tmp_path).author_photo.render("media/x.png")
    assert out.startswith("\\begin{authorportrait}[h]{3.5cm}")


def test_a_journal_that_prints_no_photographs_emits_nothing(tmp_path):
    (tmp_path / "rules.json").write_text(json.dumps(
        {"author_photo": {"mode": "none"}}), encoding="utf-8")
    assert _resolver().resolve({}, tmp_path).author_photo.render("media/x.png") == ""


def test_an_unknown_mode_falls_back_rather_than_emitting_broken_latex(tmp_path):
    (tmp_path / "rules.json").write_text(json.dumps(
        {"author_photo": {"mode": "teleport"}}), encoding="utf-8")
    assert _resolver().resolve({}, tmp_path).author_photo.mode == "floatingfigure"


# --------------------------------------------------------------------- #
# 6-9. Photos, equations and figures in the rendered output
# --------------------------------------------------------------------- #

def test_an_author_photo_is_never_captioned_or_numbered():
    """It illustrates a person, not a result."""
    out = AuthorPhotoRules().render("media/p.jpg")
    assert "\\caption" not in out
    assert "\\label" not in out
    assert "\\begin{figure}" not in out


def test_the_required_package_is_named_only_by_the_mode_that_needs_it():
    assert AuthorPhotoRules(mode="floatingfigure").package() == "floatflt"
    assert AuthorPhotoRules(mode="wrapfigure").package() == "wrapfig"
    assert AuthorPhotoRules(mode="figure").package() == ""
    assert AuthorPhotoRules(mode="none").package() == ""


def test_the_figure_mode_needs_no_package_and_still_typesets():
    out = AuthorPhotoRules(mode="figure").render("media/p.jpg")
    assert "minipage" in out and "includegraphics" in out


# --------------------------------------------------------------------- #
# 10. No journal or class name may remain in the renderer
# --------------------------------------------------------------------- #

_RENDERER = Path(__file__).resolve().parents[1] / \
    "app" / "services" / "latex_renderer.py"


def test_no_journal_or_class_name_is_tested_in_the_renderer():
    """The defect this whole phase exists to remove.

    Comments may still mention a class by name as an example; executable code
    may not branch on one.
    """
    code = []
    for line in _RENDERER.read_text(encoding="utf-8").split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        code.append(line.split("  #")[0])
    body = "\n".join(code)
    for needle in ('"NSP"', "'NSP'", '"JSAP"', "'JSAP'", "is_nsp"):
        assert needle not in body, needle


def test_the_renderer_asks_the_rules_for_the_biography_environment():
    body = _RENDERER.read_text(encoding="utf-8")
    assert "journal_rules.biography" in body
    assert "journal_rules.author_photo" in body


def test_no_author_photo_dimension_is_written_into_the_renderer():
    body = _RENDERER.read_text(encoding="utf-8")
    for literal in ("3.5cm", "3.4cm", "width=3cm"):
        assert literal not in body, literal


# --------------------------------------------------------------------- #
# The probe: what makes the decision rule-driven rather than name-driven
# --------------------------------------------------------------------- #

def test_a_plain_tex_environment_definition_is_recognised():
    """Publisher classes define environments the plain-TeX way.

    Recognising only ``\\newenvironment`` would report that a class which
    plainly provides a biography environment provides nothing, and the decision
    made on that answer would strip the journal's own layout from every
    document it typesets.
    """
    source = r"\def\biographyps#1#2{...}" "\n" r"\def\endbiographyps{...}"
    assert _defines_environment(source, "biographyps")


def test_a_lone_def_is_not_an_environment():
    """Treating an ordinary command as one would wrap content in
    \\begin/\\end that the macro never expected."""
    assert not _defines_environment(r"\def\biographyps#1#2{...}", "biographyps")


def test_the_newenvironment_form_is_still_recognised():
    assert _defines_environment(r"\newenvironment{biography}{}{}", "biography")


def test_a_probed_environment_reaches_the_resolved_rules(tmp_path):
    (tmp_path / "journal.cls").write_text(
        "\\def\\biographyps#1#2{}\n\\def\\endbiographyps{}\n"
        "\\def\\biography#1{}\n\\def\\endbiography{}\n", encoding="utf-8")
    rules = _resolver().resolve({}, tmp_path)
    assert rules.biography.photo_environment == "biographyps"
    assert rules.biography.layouts[0] == "journal_env"


def test_a_declared_rule_still_overrides_what_was_probed(tmp_path):
    (tmp_path / "journal.cls").write_text(
        "\\def\\biographyps#1#2{}\n\\def\\endbiographyps{}\n", encoding="utf-8")
    (tmp_path / "rules.json").write_text(json.dumps(
        {"biography": {"layouts": ["minipage"]}}), encoding="utf-8")
    rules = _resolver().resolve({}, tmp_path)
    assert rules.biography.layouts == ("minipage", "plain")


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
