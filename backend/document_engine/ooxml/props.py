"""Formatting properties, and the rule that combines them.

Word formatting is *inherited*, and that single fact is why this module exists
separately from the parser.  What a paragraph looks like on the page is never
written in one place: it is the document defaults, overlaid by the paragraph's
style, overlaid by every style that one is based on, overlaid finally by whatever
direct formatting the author applied.  A run adds two more layers on top.

This matters for the engine because headings in real manuscripts are recognised
by how they *look*, and a heading very often carries no direct formatting at all
-- its boldness lives in a style three levels up.  Reading ``w:rPr`` off the run,
which is what a quick implementation does, sees nothing there and concludes the
paragraph is body text.

So properties are modelled as *partial*: every field is ``None`` when the level
being described says nothing about it, and :meth:`over` layers one partial set on
another.  ``None`` means "inherit", never "off"; ``False`` means the author
explicitly turned something off, which is a different thing and beats an
inherited ``True``.

Nothing here reads XML.  These are value objects, so they can be built from a
style, from a run, or in a test, and combined by the same rule.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Optional, TypeVar

# Word's internal units.
TWIPS_PER_POINT = 20
TWIPS_PER_INCH = 1440
HALF_POINTS_PER_POINT = 2

_T = TypeVar("_T", bound="_Partial")


@dataclass(frozen=True)
class _Partial:
    """A set of properties in which ``None`` means "not specified at this level"."""

    def over(self: _T, base: Optional[_T]) -> _T:
        """This set layered on top of ``base``: anything set here wins.

        The direction reads the way inheritance does -- ``direct.over(style)`` --
        and it is deliberately not commutative, because that asymmetry *is* the
        cascade.
        """
        if base is None:
            return self
        changes = {}
        for field in fields(self):
            mine = getattr(self, field.name)
            if mine is None:
                changes[field.name] = getattr(base, field.name)
        return replace(self, **changes) if changes else self

    def specified(self) -> dict:
        """Only the fields this level actually says something about."""
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not None
        }


@dataclass(frozen=True)
class RunProps(_Partial):
    """Character-level formatting."""

    style_id: Optional[str] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[str] = None
    strike: Optional[bool] = None
    caps: Optional[bool] = None
    small_caps: Optional[bool] = None
    # "superscript" / "subscript" / "baseline".  Superscript is how affiliation
    # markers are attached to author names, so it is load-bearing, not cosmetic.
    vert_align: Optional[str] = None
    size_half_points: Optional[int] = None
    font: Optional[str] = None
    color: Optional[str] = None
    highlight: Optional[str] = None
    # True when the run is inside w:rPr of a paragraph mark rather than real text.
    is_paragraph_mark: Optional[bool] = None

    @property
    def size_pt(self) -> Optional[float]:
        if self.size_half_points is None:
            return None
        return self.size_half_points / HALF_POINTS_PER_POINT

    @property
    def is_bold(self) -> bool:
        return self.bold is True

    @property
    def is_caps(self) -> bool:
        return self.caps is True or self.small_caps is True


@dataclass(frozen=True)
class ParagraphProps(_Partial):
    """Paragraph-level formatting."""

    style_id: Optional[str] = None
    # w:outlineLvl, 0-based: 0 is "Heading 1".  Authoritative when present and,
    # on real manuscripts, almost never present -- see the parser's notes.
    outline_level: Optional[int] = None
    alignment: Optional[str] = None
    keep_next: Optional[bool] = None
    keep_lines: Optional[bool] = None
    page_break_before: Optional[bool] = None
    contextual_spacing: Optional[bool] = None
    space_before_twips: Optional[int] = None
    space_after_twips: Optional[int] = None
    line_twips: Optional[int] = None
    line_rule: Optional[str] = None
    indent_left_twips: Optional[int] = None
    indent_right_twips: Optional[int] = None
    indent_first_line_twips: Optional[int] = None
    indent_hanging_twips: Optional[int] = None
    numbering_id: Optional[int] = None
    numbering_level: Optional[int] = None

    @property
    def space_before_pt(self) -> Optional[float]:
        return _pt(self.space_before_twips)

    @property
    def space_after_pt(self) -> Optional[float]:
        return _pt(self.space_after_twips)

    @property
    def indent_left_pt(self) -> Optional[float]:
        return _pt(self.indent_left_twips)

    @property
    def is_numbered(self) -> bool:
        """Whether Word itself numbers this paragraph.

        ``numId`` 0 is Word's way of *removing* numbering that a style applied,
        so it is not a list -- a distinction that decides whether a paragraph is
        a list item or a heading that merely inherited a list style.
        """
        return bool(self.numbering_id)


@dataclass(frozen=True)
class SectionProps(_Partial):
    """Page geometry for one section, from ``w:sectPr``."""

    page_width_twips: Optional[int] = None
    page_height_twips: Optional[int] = None
    margin_left_twips: Optional[int] = None
    margin_right_twips: Optional[int] = None
    margin_top_twips: Optional[int] = None
    margin_bottom_twips: Optional[int] = None
    orientation: Optional[str] = None
    columns: Optional[int] = None
    section_type: Optional[str] = None

    @property
    def text_width_inches(self) -> Optional[float]:
        """Usable line width, which is what figure and table widths scale to."""
        if self.page_width_twips is None:
            return None
        left = self.margin_left_twips or 0
        right = self.margin_right_twips or 0
        usable = self.page_width_twips - left - right
        if usable <= 0:
            return None
        return usable / TWIPS_PER_INCH


def _pt(twips: Optional[int]) -> Optional[float]:
    return None if twips is None else twips / TWIPS_PER_POINT


__all__ = [
    "HALF_POINTS_PER_POINT",
    "ParagraphProps",
    "RunProps",
    "SectionProps",
    "TWIPS_PER_INCH",
    "TWIPS_PER_POINT",
]
