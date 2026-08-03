"""Tables, figures, equations -- and the captions that name them.

A caption is the only thing in a document that says what an object *is*, so
getting the pairing right matters more than getting the caption text pretty.
The rule used here is proximity plus agreement: the nearest non-empty paragraph
above or below an object, that begins with a label naming the same kind of
object, is its caption.  Tables conventionally caption above and figures below,
but both conventions are broken often enough that the label is trusted over the
position and the position only breaks ties.

The label pattern is generic.  ``Figure 3``, ``Fig. 3``, ``Table IV``, ``Tab 2``
and ``Equation (5)`` all parse; so does a localised label, because the pattern
is *word, separator, number* rather than a list of English words -- the English
words only decide which *kind* it is, and an unrecognised word yields a caption
of unknown kind rather than no caption at all.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence

from document_engine.model.nodes import Caption, Equation, Figure, TableNode
from document_engine.ooxml.blocks import Paragraph, Table

_LABEL = re.compile(
    r"^\s*(?P<word>[A-Za-zÀ-ɏ]{2,12})\.?\s*"
    r"(?P<number>\d+(?:\.\d+)*|[IVXLC]{1,6}|\(\s*\d+\s*\))"
    r"\s*[:.—–-]?\s*(?P<rest>.*)$"
)

_KINDS = {
    "figure": "figure",
    "fig": "figure",
    "figs": "figure",
    "image": "figure",
    "chart": "figure",
    "graph": "figure",
    "plate": "figure",
    "scheme": "figure",
    "table": "table",
    "tab": "table",
    "tbl": "table",
    "equation": "equation",
    "eq": "equation",
    "formula": "equation",
}

# How far to look for a caption.  Two paragraphs, because an object is often
# separated from its caption by one empty paragraph and never by more.
_REACH = 2


def parse_caption(paragraph: Paragraph) -> Optional[Caption]:
    """Read one paragraph as a caption, or decide it is not one."""
    text = paragraph.text().strip()
    if not text:
        return None
    match = _LABEL.match(text)
    if match is None:
        return None
    word = match.group("word").lower()
    kind = _KINDS.get(word)
    if kind is None:
        # A word we do not recognise followed by a number is a section number
        # far more often than a caption, so require the rest to be a phrase.
        return None
    number = match.group("number").strip("() ")
    return Caption(
        id=f"caption:{paragraph.anchor.start}" if paragraph.anchor else "caption",
        anchor=paragraph.anchor,
        text=match.group("rest").strip() or text,
        block=paragraph,
        kind=kind,
        label=f"{match.group('word')} {number}",
        number=number,
        confidence=0.9,
        evidence=[f"begins with a {kind} label"],
    )


def _nearest_caption(
    blocks: Sequence[object], index: int, kind: str
) -> Optional[Caption]:
    """Look above then below, and take the first label of the right kind."""
    for direction, above in ((-1, True), (1, False)):
        step = 0
        cursor = index + direction
        while 0 <= cursor < len(blocks) and step < _REACH:
            block = blocks[cursor]
            if isinstance(block, Paragraph):
                if block.text().strip():
                    caption = parse_caption(block)
                    if caption is not None and caption.kind == kind:
                        caption.above = above
                        caption.note("adjacent to the object it names")
                        return caption
                    step += 1
            else:
                break
            cursor += direction
    return None


def _cell_text(table: Table) -> List[List[str]]:
    grid: List[List[str]] = []
    for row in table.rows:
        line: List[str] = []
        for cell in row.cells:
            pieces = [
                b.text().strip()
                for b in cell.blocks
                if isinstance(b, Paragraph) and b.text().strip()
            ]
            line.append(" ".join(pieces))
        grid.append(line)
    return grid


def extract_tables(blocks: Sequence[object]) -> List[TableNode]:
    out: List[TableNode] = []
    for index, block in enumerate(blocks):
        if not isinstance(block, Table) or block.in_fallback or block.table_depth:
            continue
        cells = _cell_text(block)
        rows, columns = block.dimensions
        header = 1 if block.rows and block.rows[0].is_header else 0
        node = TableNode(
            id=f"table:{block.anchor.start}" if block.anchor else f"table:{index}",
            anchor=block.anchor,
            caption=_nearest_caption(blocks, index, "table"),
            rows=rows,
            columns=columns,
            header_rows=header,
            cells=cells,
            block=block,
            confidence=1.0,
            evidence=["a w:tbl element"],
        )
        if node.caption is None:
            node.note("no caption found within two paragraphs")
            node.confidence = 0.9
        out.append(node)
    return out


def extract_figures(blocks: Sequence[object]) -> List[Figure]:
    out: List[Figure] = []
    for index, block in enumerate(blocks):
        if not isinstance(block, Paragraph) or block.in_fallback or not block.drawings:
            continue
        first = block.drawings[0]
        node = Figure(
            id=f"figure:{block.anchor.start}" if block.anchor else f"figure:{index}",
            anchor=block.anchor,
            caption=_nearest_caption(blocks, index, "figure"),
            relationship_ids=[d.relationship_id for d in block.drawings if d.relationship_id],
            width_emu=first.width_emu,
            height_emu=first.height_emu,
            inline=first.inline,
            block=block,
            confidence=1.0,
            evidence=[f"{len(block.drawings)} drawing(s) in one paragraph"],
        )
        if node.caption is None:
            node.note("no caption found within two paragraphs")
            node.confidence = 0.9
        out.append(node)
    return out


def extract_equations(blocks: Sequence[object]) -> List[Equation]:
    """Office Math elements, and the number the document gives them.

    The equation *content* stays in the block: OMML is not text and flattening
    it here would lose it.  What this records is that an equation is at this
    anchor, how it is numbered, and whether it stands on its own line.
    """
    out: List[Equation] = []
    for index, block in enumerate(blocks):
        if not isinstance(block, Paragraph) or block.in_fallback:
            continue
        if not block.equation_count:
            continue
        text = block.text().strip()
        trailing = re.search(r"\(\s*(\d+(?:\.\d+)*)\s*\)\s*$", text)
        out.append(
            Equation(
                id=f"equation:{block.anchor.start}" if block.anchor else f"eq:{index}",
                anchor=block.anchor,
                text=text,
                block=block,
                number=trailing.group(1) if trailing else None,
                display=not text or bool(trailing) or block.table_depth == 0,
                confidence=1.0,
                evidence=[f"{block.equation_count} m:oMath element(s)"],
            )
        )
    return out


__all__ = [
    "extract_equations",
    "extract_figures",
    "extract_tables",
    "parse_caption",
]
