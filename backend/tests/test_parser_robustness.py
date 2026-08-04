"""Robustness regression tests for the DOCX analyzer.

Every test here corresponds to a way a real publisher's Word template has been
observed to break a layout-based parser.  They are written against synthetic
inputs rather than against any one paper on purpose: the bug each one pins down
is a property of a *layout convention* -- Word list numbering on headings,
superscript affiliation markers, invisible author tables, equations pasted as
pictures -- and those conventions recur across Springer, IEEE, Elsevier, MDPI
and university thesis templates alike.  A test that depended on a particular
document would only prove that document still works.

Run directly (``python test_parser_robustness.py``) or under pytest.
"""

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.document_analyzer import (  # noqa: E402
    DocumentAnalyzer,
    _looks_like_person_name,
    _strip_heading_number,
    _MAX_FRONT_MATTER_BLOCKS,
)


# --------------------------------------------------------------------- #
# AST construction helpers
# --------------------------------------------------------------------- #

def _str(text):
    out = []
    for i, word in enumerate(text.split(" ")):
        if i:
            out.append({"t": "Space"})
        out.append({"t": "Str", "c": word})
    return out


def _para(text):
    return {"t": "Para", "c": _str(text)}


def _header(level, text):
    return {"t": "Header", "c": [level, ["", [], []], _str(text)]}


def _ordered(texts):
    return {"t": "OrderedList",
            "c": [[1, {"t": "Decimal"}, {"t": "Period"}],
                  [[_para(t)] for t in texts]]}


def _math(body, display=True):
    return {"t": "Math",
            "c": [{"t": "DisplayMath" if display else "InlineMath"}, body]}


# --------------------------------------------------------------------- #
# 1. Front matter: heading numbering, superscripts, custom formatting
# --------------------------------------------------------------------- #

def test_numbered_heading_is_recognised_whatever_the_convention():
    """Four numbering conventions, one heading.

    IEEE numbers with roman numerals, Springer and Elsevier with decimals,
    theses often with "Chapter N", and some templates with letters.  All of
    them must reduce to the same title, or the body-opener landmark only works
    for whichever convention happened to be tested.
    """
    for raw in ("1. Introduction", "I. INTRODUCTION", "1 Introduction",
                "A. Introduction", "Introduction"):
        assert _strip_heading_number(raw).lower() == "introduction", raw


def test_superscript_marker_on_a_heading_does_not_hide_it():
    """A heading carrying a note marker reads the same as one without.

    Word flattens a superscript into trailing characters, so "Introduction1"
    and "Introduction*" reach the parser as different strings from
    "Introduction".  Without normalisation the body opener is invisible and the
    whole body is classified as front matter.
    """
    for raw in ("Introduction1", "Introduction *", "1. Introduction†"):
        assert _strip_heading_number(raw).lower() == "introduction", raw


def test_body_never_becomes_the_author_list_when_the_first_header_is_late():
    """The failure that motivated all of this, in its general form.

    When a template numbers its headings with Word's list numbering, pandoc
    emits no ``Header`` at all until some later heading that happens to be
    styled -- so the naive "front matter ends at the first header" rule hands
    almost the entire paper to the author extractor.  The boundary must land on
    the body opener instead.
    """
    an = DocumentAnalyzer()
    blocks = ([_para("A Study of Things"),
               _para("Jane Roe1, John Doe2"),
               _para("1 Department of Physics, Some University"),
               _para("Abstract"),
               _para("We study things and report what we found."),
               _para("Keywords: things, study")]
              + [_ordered(["Introduction"])]
              + [_para(f"Body paragraph number {i}.") for i in range(40)]
              + [_header(1, "Conclusions")])
    boundary, reason = an._front_matter_boundary(blocks, len(blocks) - 1, True)
    assert boundary <= 7, (boundary, reason)
    assert reason in ("label", "body-opener", "body-opener-header")


def test_the_boundary_is_clamped_even_when_every_signal_fails():
    """A document with no abstract, no keywords and no recognisable opener.

    Nothing here identifies where the body begins, so the only remaining
    guarantee is the ceiling: whatever happens, a paper cannot have hundreds of
    paragraphs of front matter, and the extractor must not be handed them.
    """
    an = DocumentAnalyzer()
    blocks = [_para(f"Undifferentiated paragraph {i}") for i in range(200)]
    boundary, reason = an._front_matter_boundary(blocks, len(blocks), False)
    assert boundary <= _MAX_FRONT_MATTER_BLOCKS
    assert reason in ("clamped", "prose", "label")


def test_the_abstract_is_never_cut_into():
    """A paper whose abstract mentions its own introduction.

    "... is introduced in the Introduction" inside abstract prose must not pull
    the boundary back over the abstract, which would drop the abstract and
    promote its tail into section 1.
    """
    an = DocumentAnalyzer()
    blocks = [_para("A Title"),
              _para("Jane Roe"),
              _para("Abstract"),
              _para("The method is stated in the Introduction and proved later."),
              _para("Keywords: alpha, beta"),
              _header(1, "Introduction"),
              _para("Body.")]
    boundary, _ = an._front_matter_boundary(blocks, 5, True)
    assert boundary >= 4, boundary


# --------------------------------------------------------------------- #
# 2. Authors: body text must never be mistaken for a person
# --------------------------------------------------------------------- #

def test_body_fragments_are_not_people():
    for text in ("The results are summarised in Table 2",
                 "Figure 3. Throughput against offered load",
                 "This paper proposes a new scheme.",
                 "0.42", "N/A", "Department of Computer Science"):
        assert not _looks_like_person_name(text), text


def test_real_names_survive_the_gate():
    """Including the ones a naive ASCII test rejects.

    Diacritics, hyphenated surnames, apostrophes (both the ASCII and the
    typographic one) and nobiliary particles are all ordinary in an author
    list; a gate that rejects them silently deletes authors.
    """
    for name in ("Ali Akgul", "Ali Akgül", "Emad A. Az-Zo'bi", "Baha' Shawaqfeh",
                 "Ludwig van Beethoven", "Ahmad K. Alomari", "O'Neill",
                 "Naeema Darwish Khamis Al Maashari"):
        assert _looks_like_person_name(name), name


# --------------------------------------------------------------------- #
# 3. Equations are objects, not text
# --------------------------------------------------------------------- #

def test_equations_are_collected_from_inside_style_wrappers():
    """Word wraps equations in character-style runs.

    Pandoc emits those as ``Span``/``Emph``/``Strong`` around the ``Math``
    node, so a scan of the paragraph's top level finds nothing and the equation
    survives only as flattened text.
    """
    an = DocumentAnalyzer()
    inlines = [{"t": "Span",
                "c": [["", [], []],
                      [{"t": "Emph", "c": [_math("a^2+b^2=c^2")]}]]}]
    found = an._collect_math_nodes(inlines)
    assert len(found) == 1
    assert found[0]["display"] is True
    assert "a^{2}" in found[0]["latex"] or "a^2" in found[0]["latex"]


def test_an_equation_sharing_a_paragraph_with_prose_stays_an_object():
    """The case the old code had to flatten.

    A paragraph that mixes a sentence with an equation stays a paragraph --
    splitting it would reorder the sentence -- but the equation must still be
    carried as structured data alongside the text rather than existing only as
    a run of characters inside it.
    """
    an = DocumentAnalyzer()
    counters = {"paragraphs": 0, "figures": 0, "tables": 0, "equations": 0,
                "warnings": []}
    block = {"t": "Para", "c": _str("As shown in") + [{"t": "Space"}]
             + [_math("E=mc^2", display=False)] + _str(" this holds.")}
    parsed = an._parse_block(block, "job", counters)
    assert parsed.type.value == "paragraph"
    assert parsed.content["equations"], parsed.content
    assert parsed.content["equations"][0]["display"] is False
    assert parsed.content["has_display_math"] is False


def test_a_standalone_display_equation_becomes_an_equation_block():
    an = DocumentAnalyzer()
    counters = {"paragraphs": 0, "figures": 0, "tables": 0, "equations": 0,
                "warnings": []}
    block = {"t": "Para", "c": [_math("x = y + z")] + _str(" (4)")}
    parsed = an._parse_block(block, "job", counters)
    assert parsed.type.value == "equation"
    assert parsed.content["number"] == "4"
    assert parsed.content["equations"] == [{"latex": "x = y + z", "display": True}]


# --------------------------------------------------------------------- #
# 4. Geometry of embedded drawings and equation images
# --------------------------------------------------------------------- #

_RELS = """<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Target="media/image1.png"/>
  <Relationship Id="rId2" Target="media/image2.wmf"/>
</Relationships>"""

_DOC = """<?xml version="1.0"?>
<w:document
  xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
  xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
  xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:v="urn:schemas-microsoft-com:vml"
  xmlns:o="urn:schemas-microsoft-com:office:office">
  <w:body>
    <w:p><w:r><w:drawing>
      <wp:inline><wp:extent cx="2743200" cy="1371600"/>
        <a:graphic><a:graphicData><a:blip r:embed="rId1"/></a:graphicData></a:graphic>
      </wp:inline>
    </w:drawing></w:r></w:p>
    <w:p><w:r><w:object w:dxaOrig="400" w:dyaOrig="360">
      <v:shape id="s1" style="width:20pt;height:15.8pt">
        <v:imagedata r:id="rId2"/>
      </v:shape>
      <o:OLEObject Type="Embed" ProgID="Equation.DSMT4" ShapeID="s1" r:id="rId3"/>
    </w:object></w:r></w:p>
  </w:body>
</w:document>"""


def _synthetic_docx(tmp_path):
    path = tmp_path / "geometry.docx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", _DOC)
        zf.writestr("word/_rels/document.xml.rels", _RELS)
    return path


def test_drawing_geometry_is_read_in_exact_emu(tmp_path):
    """3 inches by 1.5 inches, recorded exactly.

    The EMU extent is the only lossless record of the size the author chose;
    pandoc reports a rounded value when it reports one at all.  The aspect
    ratio is derived here so that a consumer forced to resize can do so without
    distorting the picture.
    """
    an = DocumentAnalyzer()
    geom = an._extract_drawing_geometry(_synthetic_docx(tmp_path))
    png = geom["media/image1.png"]
    assert png["emu_width"] == 2743200 and png["emu_height"] == 1371600
    assert png["width_in"] == 3.0 and png["height_in"] == 1.5
    assert abs(png["aspect_ratio"] - 2.0) < 1e-6
    assert png["inline"] is True
    assert png["is_equation"] is False


def test_a_mathtype_picture_is_sized_and_identified_as_an_equation(tmp_path):
    """Legacy Equation Editor objects are VML, not DrawingML.

    Pandoc emits them as pictures with no dimensions whatsoever, which is how
    an equation ends up captioned, floated and numbered as though it were a
    figure.  Their size lives in a CSS-like VML ``style`` attribute in points.
    """
    an = DocumentAnalyzer()
    geom = an._extract_drawing_geometry(_synthetic_docx(tmp_path))
    wmf = geom["media/image2.wmf"]
    assert wmf["is_equation"] is True
    assert abs(wmf["width_in"] - 20.0 / 72.0) < 1e-4
    assert abs(wmf["height_in"] - 15.8 / 72.0) < 1e-4
    assert wmf["emu_width"] > 0 and wmf["emu_height"] > 0


def test_the_equation_census_counts_the_source_not_the_model(tmp_path):
    an = DocumentAnalyzer()
    census = an._count_omml_equations(_synthetic_docx(tmp_path))
    assert census["ole_equations"] == 1
    assert census["omath"] == 0


def test_vml_sizes_are_parsed_in_every_absolute_unit():
    parse = DocumentAnalyzer._vml_style_size_pt
    assert parse("width:72pt;height:36pt") == (72.0, 36.0)
    w, h = parse("width:1in;height:0.5in")
    assert abs(w - 72.0) < 1e-6 and abs(h - 36.0) < 1e-6
    # A percentage is relative to a container this code cannot see, so it is
    # ignored rather than guessed at.
    assert parse("width:50%;height:50%") == (0.0, 0.0)


# --------------------------------------------------------------------- #
# 5. Failure degrades, it does not corrupt
# --------------------------------------------------------------------- #

def test_a_failing_stage_returns_the_input_unchanged():
    """The fault-isolation contract.

    A stage that raises must cost only its own enrichment.  What must never
    happen is a half-applied transformation: a partially promoted heading tree
    describes no real document, and every later stage then reads it as though
    it did.
    """
    counters = {"warnings": []}
    original = [{"t": "Para", "c": []}]

    def explode():
        raise ValueError("synthetic failure")

    result = DocumentAnalyzer._guard(counters, "heading promotion", explode, original)
    assert result is original
    assert counters["warnings"] and "heading promotion" in counters["warnings"][0]
    assert counters["degraded_stages"] == ["heading promotion"]


def test_a_malformed_docx_raises_rather_than_returning_a_wrong_model(tmp_path):
    """Garbage in must not produce a confident-looking document model."""
    bad = tmp_path / "not_really.docx"
    bad.write_bytes(b"this is not a zip archive")
    try:
        DocumentAnalyzer()._extract_drawing_geometry(bad)
    except Exception:
        pass  # raising is correct; the caller isolates it
    else:
        raise AssertionError("a corrupt DOCX must not parse silently")


def test_an_unparseable_table_still_yields_a_table_block():
    """Structure survives even when content cannot be read."""
    an = DocumentAnalyzer()
    counters = {"paragraphs": 0, "figures": 0, "tables": 0, "equations": 0,
                "warnings": []}
    parsed = an._parse_block({"t": "Table", "c": ["nonsense"]}, "job", counters)
    assert parsed.type.value == "table"
    assert counters["warnings"]


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
