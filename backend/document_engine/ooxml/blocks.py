"""The block model: what is in a part, and where it is in the bytes.

Layer 0 of the engine.  Everything here is physical -- paragraphs, tables, runs,
drawings, bookmarks, fields, section breaks -- and nothing here has an opinion
about which paragraph is a title.  That judgement belongs to Phase 2 and would be
wrong to make in a module that cannot see the whole document.

Two properties are load-bearing and worth stating plainly:

**Every block carries an anchor**, a byte range into the original part.  That is
what lets a later phase edit a document by rewriting the bytes a block occupies
rather than regenerating the file around it.  A block is a pointer with metadata,
never a copy.

**The builder rides along on the existing parse.**  It is driven by the same
expat pass that :mod:`document_engine.ooxml.bytes` already runs to locate text
nodes, so switching the block model on costs one traversal, not two, and cannot
disagree with the text nodes about where anything is.  When it is off -- the
default, and what the Document Generator uses -- none of this code runs.

The one non-obvious member is :attr:`Block.in_fallback`.  Word writes text-box
content twice, inside ``mc:AlternateContent``: once in ``mc:Choice`` for a modern
Word and once in ``mc:Fallback`` for an old one.  Both are real elements in the
file and both must be preserved on write, but a reader that treats them as two
separate paragraphs sees every text box duplicated.  Marking the fallback branch
lets the semantic layer read one and still write both.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from document_engine.ooxml.props import ParagraphProps, RunProps, SectionProps

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def scan_tag_end(data: bytes, offset: int) -> int:
    """Byte index just past the ``>`` closing the tag that starts at ``offset``.

    Quote-aware, because an attribute value may legitimately contain ``>``.
    """
    index = offset
    quote = 0
    length = len(data)
    while index < length:
        char = data[index]
        if quote:
            if char == quote:
                quote = 0
        elif char in (0x22, 0x27):
            quote = char
        elif char == 0x3E:  # '>'
            return index + 1
        index += 1
    raise ValueError("unterminated tag")


@dataclass(frozen=True)
class Anchor:
    """Where something is in the original bytes of a part."""

    part: str
    start: int
    end: int

    def slice(self, data: bytes) -> bytes:
        return data[self.start : self.end]

    def __len__(self) -> int:
        return max(0, self.end - self.start)


@dataclass
class Block:
    """Base for anything that occupies a byte range in a part."""

    anchor: Anchor
    # Depth of enclosing table cells: 0 for body-level, 1 inside a table, and so
    # on.  Nested tables are ordinary in journal templates.
    table_depth: int = 0
    in_text_box: bool = False
    # See the module docstring: the duplicated mc:Fallback branch of a text box.
    in_fallback: bool = False


@dataclass
class Run(Block):
    """One ``w:r`` -- a stretch of text sharing character formatting."""

    props: RunProps = field(default_factory=RunProps)
    text: str = ""
    # Resolved against styles by StyleResolver; None until that has been done.
    effective: Optional[RunProps] = None
    # Line breaks and tabs inside the run, which carry no character but do carry
    # layout, so a reader that ignores them mis-measures a wrapped title.
    breaks: int = 0
    tabs: int = 0


@dataclass
class Drawing(Block):
    """A ``w:drawing`` or ``w:pict``: an image, chart, shape or SmartArt."""

    kind: str = "drawing"
    relationship_id: Optional[str] = None
    name: str = ""
    width_emu: Optional[int] = None
    height_emu: Optional[int] = None
    inline: bool = True


@dataclass
class Bookmark(Block):
    """A ``w:bookmarkStart``: the target half of every cross reference."""

    name: str = ""
    bookmark_id: Optional[str] = None


@dataclass
class FieldRef(Block):
    """A field instruction -- ``PAGE``, ``REF``, ``SEQ``, ``TOC``, a citation.

    Recorded rather than evaluated.  A field's *result* is ordinary text in the
    document and is already covered by the text nodes; what a reader needs, and
    cannot recover from the result, is that the text was computed and by what.
    """

    instruction: str = ""
    simple: bool = True


@dataclass
class Paragraph(Block):
    """One ``w:p`` with its runs and everything anchored inside it."""

    props: ParagraphProps = field(default_factory=ParagraphProps)
    runs: List[Run] = field(default_factory=list)
    drawings: List[Drawing] = field(default_factory=list)
    bookmarks: List[Bookmark] = field(default_factory=list)
    fields: List[FieldRef] = field(default_factory=list)
    footnote_ref_ids: List[str] = field(default_factory=list)
    equation_count: int = 0
    # Formatting of the paragraph mark itself (w:pPr/w:rPr).  Kept apart from the
    # runs on purpose: a bold pilcrow is not a bold heading.
    mark_props: Optional[RunProps] = None
    # Set by StyleResolver.
    effective: Optional[ParagraphProps] = None
    # A section break carried on this paragraph's mark, if any.
    section: Optional[SectionProps] = None
    hyperlink_count: int = 0

    def text(self) -> str:
        return "".join(run.text for run in self.runs)

    @property
    def is_empty(self) -> bool:
        return not self.text().strip() and not self.drawings

    @property
    def break_count(self) -> int:
        return sum(run.breaks for run in self.runs)


@dataclass
class Cell(Block):
    """A ``w:tc``."""

    blocks: List[Block] = field(default_factory=list)
    grid_span: int = 1
    vertical_merge: Optional[str] = None  # "restart" | "continue"
    width_twips: Optional[int] = None

    def text(self) -> str:
        return "\n".join(
            block.text() for block in self.blocks if isinstance(block, Paragraph)
        )


@dataclass
class Row(Block):
    """A ``w:tr``."""

    cells: List[Cell] = field(default_factory=list)
    is_header: bool = False
    height_twips: Optional[int] = None


@dataclass
class Table(Block):
    """A ``w:tbl``."""

    rows: List[Row] = field(default_factory=list)
    style_id: Optional[str] = None
    grid_columns: List[int] = field(default_factory=list)
    width_twips: Optional[int] = None
    width_type: Optional[str] = None

    @property
    def dimensions(self) -> tuple:
        return (len(self.rows), max((len(r.cells) for r in self.rows), default=0))


@dataclass
class TextBox(Block):
    """A ``w:txbxContent``: paragraphs living inside a shape."""

    blocks: List[Block] = field(default_factory=list)


def iter_paragraphs(blocks: Sequence[Block], skip_fallback: bool = True):
    """Every paragraph in a block tree, in document order.

    ``skip_fallback`` is on by default because a caller that wants to *read* the
    document wants each text box once; a caller that wants to write to every
    branch asks for all of them.
    """
    for block in blocks:
        if skip_fallback and block.in_fallback:
            continue
        if isinstance(block, Paragraph):
            yield block
        elif isinstance(block, Table):
            for row in block.rows:
                for cell in row.cells:
                    yield from iter_paragraphs(cell.blocks, skip_fallback)
        elif isinstance(block, TextBox):
            yield from iter_paragraphs(block.blocks, skip_fallback)


def iter_tables(blocks: Sequence[Block], skip_fallback: bool = True):
    """Every table, including tables nested inside table cells."""
    for block in blocks:
        if skip_fallback and block.in_fallback:
            continue
        if isinstance(block, Table):
            yield block
            for row in block.rows:
                for cell in row.cells:
                    yield from iter_tables(cell.blocks, skip_fallback)
        elif isinstance(block, TextBox):
            yield from iter_tables(block.blocks, skip_fallback)


def modal_body_size_pt(paragraphs: Sequence[Paragraph]) -> Optional[float]:
    """The document's own body text size, measured rather than assumed.

    Heading detection compares a paragraph's size against the size of ordinary
    text.  Hard-coding that baseline at 10 or 11 point breaks on the next
    template; taking the *mode*, weighted by how much text is set at each size,
    asks the document what its body size is.

    Weighted by character count on purpose: a paper with forty headings and four
    hundred body paragraphs should not have its baseline dragged by a caption
    style, and short paragraphs are exactly where the odd sizes live.
    """
    weights: Dict[float, int] = {}
    for paragraph in paragraphs:
        for run in paragraph.runs:
            props = run.effective or run.props
            size = props.size_pt
            length = len(run.text.strip())
            if size is None or length == 0:
                continue
            weights[size] = weights.get(size, 0) + length
    if not weights:
        return None
    # Ties broken towards the smaller size: body text is smaller than headings,
    # and a tie means the document is telling us very little either way.
    return min(weights, key=lambda size: (-weights[size], size))


__all__ = [
    "Anchor",
    "Block",
    "Bookmark",
    "Cell",
    "Drawing",
    "FieldRef",
    "M_NS",
    "MC_NS",
    "Paragraph",
    "R_NS",
    "Row",
    "Run",
    "Table",
    "TextBox",
    "W_NS",
    "iter_paragraphs",
    "iter_tables",
    "modal_body_size_pt",
    "scan_tag_end",
]
