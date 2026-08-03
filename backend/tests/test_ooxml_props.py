"""Partial properties and the layering rule.

Small, fast, and where the subtlest bug in the engine would live: ``None`` means
"inherit" and ``False`` means "explicitly off".  Conflating them makes an author
who switched bold *off* inside a bold style come out bold.
"""

from __future__ import annotations

from document_engine.ooxml.builder import _int, _on_off
from document_engine.ooxml.props import (
    TWIPS_PER_INCH,
    ParagraphProps,
    RunProps,
    SectionProps,
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def test_none_inherits() -> None:
    style = RunProps(bold=True, size_half_points=24)
    direct = RunProps(italic=True)
    assert direct.over(style) == RunProps(bold=True, italic=True, size_half_points=24)


def test_false_beats_an_inherited_true() -> None:
    """The whole reason properties are three-valued."""
    style = RunProps(bold=True)
    assert RunProps(bold=False).over(style).bold is False


def test_layering_is_not_commutative() -> None:
    a, b = RunProps(bold=True), RunProps(bold=False)
    assert a.over(b).bold is True
    assert b.over(a).bold is False


def test_over_none_is_the_identity() -> None:
    props = RunProps(bold=True)
    assert props.over(None) is props


def test_specified_reports_only_this_level() -> None:
    assert RunProps(bold=True).specified() == {"bold": True}


def test_sizes_convert_from_word_units() -> None:
    assert RunProps(size_half_points=23).size_pt == 11.5
    assert ParagraphProps(space_after_twips=240).space_after_pt == 12.0


def test_numbering_id_zero_means_numbering_removed() -> None:
    """``numId=0`` cancels a style's numbering; it is not a list."""
    assert ParagraphProps(numbering_id=0).is_numbered is False
    assert ParagraphProps(numbering_id=3).is_numbered is True


def test_text_width_is_the_page_minus_its_margins() -> None:
    section = SectionProps(
        page_width_twips=12240, margin_left_twips=1440, margin_right_twips=1440
    )
    assert section.text_width_inches == (12240 - 2880) / TWIPS_PER_INCH


def test_text_width_is_none_when_geometry_is_absurd() -> None:
    assert SectionProps(page_width_twips=100, margin_left_twips=999).text_width_inches is None


def test_on_off_toggle_semantics() -> None:
    assert _on_off({}) is True                       # <w:b/>
    assert _on_off({f"{W} val": "1"}) is True
    assert _on_off({f"{W} val": "true"}) is True
    assert _on_off({f"{W} val": "0"}) is False       # <w:b w:val="0"/>
    assert _on_off({f"{W} val": "false"}) is False
    assert _on_off({f"{W} val": "off"}) is False


def test_int_tolerates_what_word_writes() -> None:
    assert _int("240") == 240
    assert _int("240.5") == 240
    assert _int(None) is None
    assert _int("auto") is None
