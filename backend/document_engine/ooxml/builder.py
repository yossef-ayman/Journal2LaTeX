"""Building the block tree from the expat events the byte parser already emits.

This is the extension point of Phase 1.  :func:`document_engine.ooxml.bytes.parse_part`
has always walked a part with expat to record where every ``w:t`` lives; the
builder listens to that same walk and assembles paragraphs, runs, tables,
drawings, bookmarks, fields and section breaks out of it.

Riding along on the existing traversal rather than adding a second one is not
only cheaper -- it is the only way the two views cannot disagree.  A block's
anchor and the text nodes inside it come from one pass over one buffer, so there
is no possibility of an offset meaning one thing to the writer and another to the
reader.

The builder is inert unless asked for.  ``parse_part(data)`` behaves exactly as
it did before Phase 1, which is what keeps the Document Generator untouched.

Reading OOXML properties has one trap worth naming, because getting it wrong is
silent: ``w:rPr`` means two different things depending on where it sits.  Inside
``w:pPr`` it describes the *paragraph mark* -- the pilcrow -- and says nothing
about the paragraph's text.  Inside ``w:r`` it describes the run.  A parser that
does not distinguish them reads a bold pilcrow as a bold heading.  The context
stack below exists for that distinction and a handful like it.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from document_engine.ooxml.blocks import (
    M_NS,
    MC_NS,
    R_NS,
    W_NS,
    Anchor,
    Block,
    Bookmark,
    Cell,
    Drawing,
    FieldRef,
    Paragraph,
    Row,
    Run,
    Table,
    TextBox,
    scan_tag_end,
)
from document_engine.ooxml.props import ParagraphProps, RunProps, SectionProps

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
V_NS = "urn:schemas-microsoft-com:vml"

# Property containers.  Presence on the context stack changes what a child
# element means, so they are tracked rather than merely skipped.
_CONTEXTS = {
    (W_NS, "pPr"),
    (W_NS, "rPr"),
    (W_NS, "sectPr"),
    (W_NS, "numPr"),
    (W_NS, "tblPr"),
    (W_NS, "trPr"),
    (W_NS, "tcPr"),
    (W_NS, "tblGrid"),
    (W_NS, "tabs"),
    (W_NS, "pBdr"),
    (W_NS, "rFonts"),
}


def _split(name: str) -> tuple:
    """Expat's ``"uri local"`` back into its two halves."""
    if " " in name:
        uri, local = name.rsplit(" ", 1)
        return uri, local
    return "", name


def _attr(attrs: Dict[str, str], uri: str, local: str) -> Optional[str]:
    return attrs.get(f"{uri} {local}") if uri else attrs.get(local)


def _w(attrs: Dict[str, str], local: str) -> Optional[str]:
    return attrs.get(f"{W_NS} {local}")


def _on_off(attrs: Dict[str, str]) -> bool:
    """An OOXML toggle: present means on unless ``w:val`` says otherwise.

    ``<w:b/>`` is bold; ``<w:b w:val="0"/>`` is *explicitly not* bold, which is
    not the same as saying nothing -- it overrides an inherited bold.
    """
    value = _w(attrs, "val")
    if value is None:
        return True
    return value.strip().lower() not in ("0", "false", "off")


def _int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value.strip()))
    except (TypeError, ValueError):
        return None


class BlockBuilder:
    """Assembles the block tree while the byte parser walks the part."""

    def __init__(self, data: bytes, part_name: str = "") -> None:
        self._data = data
        self._name = part_name

        self.blocks: List[Block] = []
        self.sections: List[SectionProps] = []
        self.bookmarks: List[Bookmark] = []
        self.fields: List[FieldRef] = []

        self._containers: List[List[Block]] = [self.blocks]
        self._paragraphs: List[Paragraph] = []
        self._tables: List[Table] = []
        self._rows: List[Row] = []
        self._cells: List[Cell] = []
        self._runs: List[Run] = []
        self._boxes: List[TextBox] = []
        self._drawing: Optional[Drawing] = None
        self._ctx: List[tuple] = []

        self._pending: Dict[str, object] = {}
        self._run_pending: Dict[str, object] = {}
        self._section_pending: Dict[str, object] = {}

        self._fallback_depth = 0
        self._table_depth = 0
        self._box_depth = 0
        self._in_text = False
        self._instr: Optional[FieldRef] = None

    # -- context helpers -------------------------------------------------

    def _in(self, local: str) -> bool:
        return (W_NS, local) in self._ctx

    @property
    def _in_paragraph_props(self) -> bool:
        return self._in("pPr") and not self._in("rPr") and not self._in("sectPr")

    @property
    def _in_run_props(self) -> bool:
        """Run properties proper -- not the paragraph mark's, not a style's."""
        return self._in("rPr") and not self._in("pPr")

    def _stamp(self, block: Block) -> Block:
        block.table_depth = self._table_depth
        block.in_text_box = self._box_depth > 0
        block.in_fallback = self._fallback_depth > 0
        return block

    def _anchor(self, start: int, end: int) -> Anchor:
        return Anchor(self._name, start, end)

    # -- events ----------------------------------------------------------

    def start(self, name: str, attrs: Dict[str, str], offset: int) -> None:
        uri, local = _split(name)

        if uri == MC_NS and local == "Fallback":
            self._fallback_depth += 1
            return

        if (uri, local) in _CONTEXTS:
            self._ctx.append((uri, local))
            if local == "sectPr":
                self._section_pending = {}
            # numPr and rFonts carry data of their own, handled below.
            if local not in ("numPr", "rFonts"):
                return

        if uri == W_NS and self._ctx:
            self._property(local, attrs)
            return

        if uri == W_NS:
            self._content(local, attrs, offset)
        elif uri == M_NS and local == "oMath":
            if self._paragraphs:
                self._paragraphs[-1].equation_count += 1
        elif self._drawing is not None:
            self._drawing_detail(uri, local, attrs)

    def end(self, name: str, offset: int) -> None:
        uri, local = _split(name)

        if uri == MC_NS and local == "Fallback":
            self._fallback_depth = max(0, self._fallback_depth - 1)
            return

        if (uri, local) in _CONTEXTS and self._ctx and self._ctx[-1] == (uri, local):
            self._ctx.pop()
            if local == "pPr":
                self._close_paragraph_props()
            elif local == "rPr":
                self._close_run_props()
            elif local == "sectPr":
                self._close_section()
            return

        if uri != W_NS:
            return

        if local == "t":
            self._in_text = False
        elif local == "instrText":
            self._in_text = False
            self._instr = None
        elif local == "r":
            self._close(self._runs, offset)
        elif local == "p":
            self._close(self._paragraphs, offset)
        elif local == "tc":
            self._containers.pop()
            self._close(self._cells, offset)
        elif local == "tr":
            self._close(self._rows, offset)
        elif local == "tbl":
            self._table_depth = max(0, self._table_depth - 1)
            self._close(self._tables, offset)
        elif local == "txbxContent":
            self._box_depth = max(0, self._box_depth - 1)
            self._containers.pop()
            self._close(self._boxes, offset)
        elif local in ("drawing", "pict") and self._drawing is not None:
            self._drawing.anchor = self._anchor(
                self._drawing.anchor.start, self._end_of_tag(offset)
            )
            self._drawing = None

    def chardata(self, text: str) -> None:
        if not self._in_text:
            return
        if self._instr is not None:
            self._instr.instruction += text
        elif self._runs:
            self._runs[-1].text += text

    def finish(self) -> None:
        """Close anything a malformed part left open, so callers get a tree."""
        self._ctx.clear()

    # -- content ---------------------------------------------------------

    def _content(self, local: str, attrs: Dict[str, str], offset: int) -> None:
        if local == "p":
            block = self._stamp(Paragraph(anchor=self._anchor(offset, offset)))
            self._containers[-1].append(block)
            self._paragraphs.append(block)  # type: ignore[arg-type]
            self._pending = {}
        elif local == "r":
            run = self._stamp(Run(anchor=self._anchor(offset, offset)))
            if self._paragraphs:
                self._paragraphs[-1].runs.append(run)  # type: ignore[arg-type]
            self._runs.append(run)  # type: ignore[arg-type]
            self._run_pending = {}
        elif local == "t":
            self._in_text = True
        elif local == "instrText":
            self._in_text = True
            ref = self._stamp(FieldRef(anchor=self._anchor(offset, offset), simple=False))
            self._instr = ref  # type: ignore[assignment]
            self.fields.append(ref)  # type: ignore[arg-type]
            if self._paragraphs:
                self._paragraphs[-1].fields.append(ref)  # type: ignore[arg-type]
        elif local == "fldSimple":
            ref = self._stamp(
                FieldRef(
                    anchor=self._anchor(offset, self._end_of_tag(offset)),
                    instruction=(_w(attrs, "instr") or "").strip(),
                    simple=True,
                )
            )
            self.fields.append(ref)  # type: ignore[arg-type]
            if self._paragraphs:
                self._paragraphs[-1].fields.append(ref)  # type: ignore[arg-type]
        elif local == "br":
            if self._runs:
                self._runs[-1].breaks += 1
        elif local == "tab":
            if self._runs:
                self._runs[-1].tabs += 1
        elif local == "bookmarkStart":
            mark = self._stamp(
                Bookmark(
                    anchor=self._anchor(offset, self._end_of_tag(offset)),
                    name=_w(attrs, "name") or "",
                    bookmark_id=_w(attrs, "id"),
                )
            )
            self.bookmarks.append(mark)  # type: ignore[arg-type]
            if self._paragraphs:
                self._paragraphs[-1].bookmarks.append(mark)  # type: ignore[arg-type]
        elif local == "hyperlink":
            if self._paragraphs:
                self._paragraphs[-1].hyperlink_count += 1
        elif local == "footnoteReference" or local == "endnoteReference":
            if self._paragraphs:
                self._paragraphs[-1].footnote_ref_ids.append(_w(attrs, "id") or "")
        elif local in ("drawing", "pict"):
            drawing = self._stamp(
                Drawing(anchor=self._anchor(offset, offset), kind=local)
            )
            self._drawing = drawing  # type: ignore[assignment]
            if self._paragraphs:
                self._paragraphs[-1].drawings.append(drawing)  # type: ignore[arg-type]
        elif local == "tbl":
            table = self._stamp(Table(anchor=self._anchor(offset, offset)))
            self._containers[-1].append(table)
            self._tables.append(table)  # type: ignore[arg-type]
            self._table_depth += 1
        elif local == "tr":
            row = self._stamp(Row(anchor=self._anchor(offset, offset)))
            if self._tables:
                self._tables[-1].rows.append(row)  # type: ignore[arg-type]
            self._rows.append(row)  # type: ignore[arg-type]
        elif local == "tc":
            cell = self._stamp(Cell(anchor=self._anchor(offset, offset)))
            if self._rows:
                self._rows[-1].cells.append(cell)  # type: ignore[arg-type]
            self._cells.append(cell)  # type: ignore[arg-type]
            self._containers.append(cell.blocks)
        elif local == "txbxContent":
            box = self._stamp(TextBox(anchor=self._anchor(offset, offset)))
            self._containers[-1].append(box)
            self._boxes.append(box)  # type: ignore[arg-type]
            self._containers.append(box.blocks)
            self._box_depth += 1

    def _drawing_detail(self, uri: str, local: str, attrs: Dict[str, str]) -> None:
        """Identity and size of the current image, wherever the format hides it."""
        drawing = self._drawing
        if drawing is None:
            return
        if uri == A_NS and local == "blip":
            drawing.relationship_id = _attr(attrs, R_NS, "embed") or drawing.relationship_id
        elif uri == WP_NS and local == "docPr":
            drawing.name = attrs.get("name", "") or drawing.name
        elif uri == WP_NS and local == "extent":
            drawing.width_emu = _int(attrs.get("cx"))
            drawing.height_emu = _int(attrs.get("cy"))
        elif uri == WP_NS and local == "anchor":
            drawing.inline = False
        elif uri == V_NS and local == "imagedata":
            drawing.relationship_id = _attr(attrs, R_NS, "id") or drawing.relationship_id

    # -- properties ------------------------------------------------------

    def _property(self, local: str, attrs: Dict[str, str]) -> None:
        if self._in("sectPr"):
            self._section_property(local, attrs)
        elif self._in_paragraph_props:
            self._paragraph_property(local, attrs)
        elif self._in_run_props:
            self._run_property(local, attrs)
        elif self._in("tcPr"):
            self._cell_property(local, attrs)
        elif self._in("trPr"):
            self._row_property(local, attrs)
        elif self._in("tblPr"):
            self._table_property(local, attrs)
        elif self._in("tblGrid") and local == "gridCol":
            width = _int(_w(attrs, "w"))
            if self._tables and width is not None:
                self._tables[-1].grid_columns.append(width)

    def _paragraph_property(self, local: str, attrs: Dict[str, str]) -> None:
        read_paragraph_property(self._pending, local, attrs)

    def _run_property(self, local: str, attrs: Dict[str, str]) -> None:
        read_run_property(self._run_pending, local, attrs)



    def _cell_property(self, local: str, attrs: Dict[str, str]) -> None:
        if not self._cells:
            return
        cell = self._cells[-1]
        if local == "gridSpan":
            cell.grid_span = _int(_w(attrs, "val")) or 1
        elif local == "vMerge":
            cell.vertical_merge = _w(attrs, "val") or "continue"
        elif local == "tcW":
            cell.width_twips = _int(_w(attrs, "w"))

    def _row_property(self, local: str, attrs: Dict[str, str]) -> None:
        if not self._rows:
            return
        row = self._rows[-1]
        if local == "tblHeader":
            row.is_header = _on_off(attrs)
        elif local == "trHeight":
            row.height_twips = _int(_w(attrs, "val"))

    def _table_property(self, local: str, attrs: Dict[str, str]) -> None:
        if not self._tables:
            return
        table = self._tables[-1]
        if local == "tblStyle":
            table.style_id = _w(attrs, "val")
        elif local == "tblW":
            table.width_twips = _int(_w(attrs, "w"))
            table.width_type = _w(attrs, "type")

    def _section_property(self, local: str, attrs: Dict[str, str]) -> None:
        pending = self._section_pending
        if local == "pgSz":
            pending["page_width_twips"] = _int(_w(attrs, "w"))
            pending["page_height_twips"] = _int(_w(attrs, "h"))
            pending["orientation"] = _w(attrs, "orient") or "portrait"
        elif local == "pgMar":
            pending["margin_left_twips"] = _int(_w(attrs, "left"))
            pending["margin_right_twips"] = _int(_w(attrs, "right"))
            pending["margin_top_twips"] = _int(_w(attrs, "top"))
            pending["margin_bottom_twips"] = _int(_w(attrs, "bottom"))
        elif local == "cols":
            pending["columns"] = _int(_w(attrs, "num")) or 1
        elif local == "type":
            pending["section_type"] = _w(attrs, "val")

    # -- closing ---------------------------------------------------------

    def _close_paragraph_props(self) -> None:
        if self._paragraphs:
            self._paragraphs[-1].props = ParagraphProps(**self._pending)  # type: ignore[arg-type]
        self._pending = {}

    def _close_run_props(self) -> None:
        pending = self._run_pending
        self._run_pending = {}
        if self._in("pPr"):
            # The paragraph *mark's* formatting, not the paragraph's text.  It is
            # recorded on the paragraph so a later phase can round-trip it, and
            # deliberately not written to any run: inside a text box the enclosing
            # run is still open and would otherwise be given the pilcrow's bold.
            if self._paragraphs:
                self._paragraphs[-1].mark_props = RunProps(
                    is_paragraph_mark=True, **pending  # type: ignore[arg-type]
                )
            return
        if self._runs:
            self._runs[-1].props = RunProps(**pending)  # type: ignore[arg-type]

    def _close_section(self) -> None:
        section = SectionProps(**self._section_pending)  # type: ignore[arg-type]
        self._section_pending = {}
        self.sections.append(section)
        # A sectPr inside a paragraph's properties is a section *break* carried by
        # that paragraph; one at body level is the final section of the document.
        if self._in("pPr") and self._paragraphs:
            self._paragraphs[-1].section = section

    def _close(self, stack: List, offset: int) -> None:
        if not stack:
            return
        block = stack.pop()
        block.anchor = self._anchor(block.anchor.start, self._end_of_tag(offset))

    def _end_of_tag(self, offset: int) -> int:
        try:
            return scan_tag_end(self._data, offset)
        except ValueError:  # pragma: no cover - truncated part
            return len(self._data)


def read_paragraph_property(pending: Dict[str, object], local: str, attrs: Dict[str, str]) -> None:
    """Map one ``w:pPr`` child onto a :class:`ParagraphProps` field.

    A free function because a *style* says the same things in the same elements;
    reading both through one implementation is what makes the cascade coherent.
    """
    if local == "pStyle":
        pending["style_id"] = _w(attrs, "val")
    elif local == "outlineLvl":
        pending["outline_level"] = _int(_w(attrs, "val"))
    elif local == "jc":
        pending["alignment"] = _w(attrs, "val")
    elif local == "keepNext":
        pending["keep_next"] = _on_off(attrs)
    elif local == "keepLines":
        pending["keep_lines"] = _on_off(attrs)
    elif local == "pageBreakBefore":
        pending["page_break_before"] = _on_off(attrs)
    elif local == "contextualSpacing":
        pending["contextual_spacing"] = _on_off(attrs)
    elif local == "spacing":
        pending["space_before_twips"] = _int(_w(attrs, "before"))
        pending["space_after_twips"] = _int(_w(attrs, "after"))
        pending["line_twips"] = _int(_w(attrs, "line"))
        pending["line_rule"] = _w(attrs, "lineRule")
    elif local == "ind":
        pending["indent_left_twips"] = _int(_w(attrs, "left") or _w(attrs, "start"))
        pending["indent_right_twips"] = _int(_w(attrs, "right") or _w(attrs, "end"))
        pending["indent_first_line_twips"] = _int(_w(attrs, "firstLine"))
        pending["indent_hanging_twips"] = _int(_w(attrs, "hanging"))
    elif local == "ilvl":
        pending["numbering_level"] = _int(_w(attrs, "val"))
    elif local == "numId":
        pending["numbering_id"] = _int(_w(attrs, "val"))


def read_run_property(pending: Dict[str, object], local: str, attrs: Dict[str, str]) -> None:
    """Map one ``w:rPr`` child onto a :class:`RunProps` field."""
    if local == "rStyle":
        pending["style_id"] = _w(attrs, "val")
    elif local == "b":
        pending["bold"] = _on_off(attrs)
    elif local == "i":
        pending["italic"] = _on_off(attrs)
    elif local == "u":
        pending["underline"] = _w(attrs, "val")
    elif local == "strike":
        pending["strike"] = _on_off(attrs)
    elif local == "caps":
        pending["caps"] = _on_off(attrs)
    elif local == "smallCaps":
        pending["small_caps"] = _on_off(attrs)
    elif local == "vertAlign":
        pending["vert_align"] = _w(attrs, "val")
    elif local == "sz":
        pending["size_half_points"] = _int(_w(attrs, "val"))
    elif local == "rFonts":
        pending["font"] = (
            _w(attrs, "ascii") or _w(attrs, "hAnsi") or _w(attrs, "cs")
        )
    elif local == "color":
        pending["color"] = _w(attrs, "val")
    elif local == "highlight":
        pending["highlight"] = _w(attrs, "val")


__all__ = ["BlockBuilder", "read_paragraph_property", "read_run_property"]
