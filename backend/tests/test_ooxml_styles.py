"""The style cascade -- the layer that decides whether headings are found at all.

The synthetic fixtures here are hand-written XML rather than real papers because
a cascade is a *rule*, and a rule is tested by constructing the case that breaks
it.  The real papers then check that the rule survives contact with Word.
"""

from __future__ import annotations

from document_engine.ooxml.blocks import Anchor, Paragraph, Run, iter_paragraphs
from document_engine.ooxml.bytes import parse_part
from document_engine.ooxml.props import ParagraphProps, RunProps
from document_engine.ooxml.styles import StyleResolver

STYLES = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault><w:rPr><w:sz w:val="20"/><w:rFonts w:ascii="Cambria"/></w:rPr></w:rPrDefault>
    <w:pPrDefault><w:pPr><w:spacing w:after="120"/></w:pPr></w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="BaseHeading">
    <w:name w:val="Base Heading"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:keepNext/><w:spacing w:before="240"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="28"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="BaseHeading"/>
    <w:pPr><w:outlineLvl w:val="0"/><w:numPr><w:numId w:val="7"/></w:numPr></w:pPr>
    <w:rPr><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="character" w:styleId="Emphasis">
    <w:name w:val="Emphasis"/>
    <w:rPr><w:i/><w:b w:val="0"/></w:rPr>
  </w:style>
</w:styles>"""

NUMBERING = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:abstractNum w:abstractNumId="4">
    <w:lvl w:ilvl="0">
      <w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/>
      <w:pPr><w:ind w:left="720"/></w:pPr>
    </w:lvl>
    <w:lvl w:ilvl="1">
      <w:numFmt w:val="bullet"/><w:lvlText w:val="&#8226;"/>
    </w:lvl>
  </w:abstractNum>
  <w:num w:numId="7"><w:abstractNumId w:val="4"/></w:num>
</w:numbering>"""


def resolver() -> StyleResolver:
    return StyleResolver(STYLES, NUMBERING)


def paragraph(style_id=None, **props) -> Paragraph:
    anchor = Anchor("word/document.xml", 0, 1)
    return Paragraph(anchor=anchor, props=ParagraphProps(style_id=style_id, **props))


def test_styles_and_defaults_are_read() -> None:
    r = resolver()
    assert set(r.styles) == {"Normal", "BaseHeading", "Heading1", "Emphasis"}
    assert r.default_paragraph_style == "Normal"
    assert r.doc_defaults_run.size_half_points == 20
    assert r.doc_defaults_paragraph.space_after_twips == 120


def test_based_on_chain_is_walked_root_first() -> None:
    """Heading1 -> BaseHeading -> Normal -> docDefaults, nearest winning."""
    props = resolver().paragraph_style_props("Heading1")
    assert props.outline_level == 0        # from Heading1
    assert props.keep_next is True         # inherited from BaseHeading
    assert props.space_before_twips == 240 # inherited from BaseHeading
    assert props.space_after_twips == 120  # inherited from docDefaults


def test_nearer_style_overrides_its_ancestor() -> None:
    assert resolver().run_style_props("Heading1").size_half_points == 32


def test_a_heading_is_bold_because_its_style_is(document_bytes=None) -> None:
    """The case that a run-only parser gets wrong on every Springer paper."""
    r = resolver()
    p = paragraph("Heading1")
    run = Run(anchor=p.anchor, props=RunProps(), text="Introduction")
    effective = r.effective_run_props(run, p)
    assert effective.bold is True          # nothing on the run says so
    assert effective.size_pt == 16.0
    assert effective.font == "Cambria"     # all the way from docDefaults


def test_direct_formatting_beats_the_style() -> None:
    r = resolver()
    p = paragraph("Heading1")
    run = Run(anchor=p.anchor, props=RunProps(bold=False, size_half_points=24))
    effective = r.effective_run_props(run, p)
    assert effective.bold is False
    assert effective.size_pt == 12.0


def test_character_style_layers_over_the_paragraph_style() -> None:
    r = resolver()
    p = paragraph("Heading1")
    run = Run(anchor=p.anchor, props=RunProps(style_id="Emphasis"))
    effective = r.effective_run_props(run, p)
    assert effective.italic is True
    assert effective.bold is False   # Emphasis explicitly turns the heading bold off
    assert effective.size_pt == 16.0 # but leaves the size alone


def test_style_level_numbering_reaches_the_paragraph() -> None:
    """The paragraph's own XML says nothing about numbering; the style does."""
    r = resolver()
    effective = r.effective_paragraph_props(paragraph("Heading1"))
    assert effective.numbering_id == 7
    level = r.numbering_level(effective)
    assert level is not None and level.fmt == "decimal" and level.text == "%1."
    assert level.indent_left_twips == 720


def test_numbering_levels_distinguish_bullets_from_numbers() -> None:
    r = resolver()
    bullet = r.numbering_level(ParagraphProps(numbering_id=7, numbering_level=1))
    assert bullet is not None and bullet.is_bullet


def test_unknown_style_falls_back_to_defaults_rather_than_failing() -> None:
    r = resolver()
    props = r.paragraph_style_props("StyleThatIsNotThere")
    assert props.space_after_twips == 120


def test_based_on_cycle_terminates() -> None:
    cyclic = StyleResolver(
        b"""<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:style w:type="paragraph" w:styleId="A"><w:basedOn w:val="B"/></w:style>
        <w:style w:type="paragraph" w:styleId="B"><w:basedOn w:val="A"/></w:style>
        </w:styles>"""
    )
    assert cyclic.paragraph_style_props("A") is not None


def test_missing_parts_are_not_an_error() -> None:
    empty = StyleResolver()
    assert empty.styles == {}
    assert empty.numbering_level(ParagraphProps(numbering_id=1)) is None


# -- against the real papers -------------------------------------------------


def test_resolve_fills_in_every_paragraph(paper, document_bytes: bytes) -> None:
    import zipfile

    part = parse_part(document_bytes, blocks=True, name="word/document.xml")
    with zipfile.ZipFile(paper) as archive:
        StyleResolver.from_zip(archive).resolve(part.blocks)
    paragraphs = list(iter_paragraphs(part.blocks))
    assert paragraphs
    assert all(p.effective is not None for p in paragraphs)
    assert all(r.effective is not None for p in paragraphs for r in p.runs)


def test_resolution_only_adds_information(paper, document_bytes: bytes) -> None:
    """Effective props may fill blanks; they must never contradict the file."""
    import zipfile

    part = parse_part(document_bytes, blocks=True, name="word/document.xml")
    with zipfile.ZipFile(paper) as archive:
        StyleResolver.from_zip(archive).resolve(part.blocks)
    for p in iter_paragraphs(part.blocks):
        for name, value in p.props.specified().items():
            assert getattr(p.effective, name) == value
        for run in p.runs:
            for name, value in run.props.specified().items():
                assert getattr(run.effective, name) == value


def test_every_real_paper_yields_a_body_text_size(paper, document_bytes: bytes) -> None:
    """Before the cascade, a paper whose runs carry no ``w:sz`` had no measurable
    body size at all -- which is the bug this layer exists to fix."""
    import zipfile

    from document_engine.ooxml.blocks import modal_body_size_pt

    part = parse_part(document_bytes, blocks=True, name="word/document.xml")
    with zipfile.ZipFile(paper) as archive:
        StyleResolver.from_zip(archive).resolve(part.blocks)
    size = modal_body_size_pt(list(iter_paragraphs(part.blocks)))
    assert size is not None and 6.0 <= size <= 16.0
