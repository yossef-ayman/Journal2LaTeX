"""The semantic document model -- Layer 1.

Layer 0 says *what is in the file*: paragraphs, runs, tables, byte ranges.  This
layer says *what the file means*: this is the title, these are the authors, that
is Section 3.2, this table has a caption above it.

Two rules make the difference between a model that can edit a document and one
that can only describe it.

**Nothing here copies bytes.**  Every node carries the :class:`Anchor` of the
block it came from, so "the abstract" is a byte range in ``word/document.xml``,
not a string that once resembled one.  Editing the abstract is then a splice,
and everything else in the file is copied through untouched.

**Every node keeps its block.**  ``node.block`` is the Layer-0 object, so a
consumer that needs formatting -- the resolved font of the title, the grid of a
table -- asks the physical layer rather than having it duplicated up here and
allowed to drift.

The extractors are allowed to be unsure, and say so: every node carries a
``confidence`` and the ``evidence`` that produced it.  A field the parser
guessed at with 0.4 confidence is a field the UI should show the user first.
That is the difference between an engine that admits what it does not know and
one that quietly gets the author list wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from document_engine.ooxml.blocks import Anchor
from document_engine.ooxml.blocks import Paragraph as BlockParagraph
from document_engine.ooxml.blocks import Table as BlockTable


@dataclass
class Node:
    """Anything the engine has identified, and how sure it is."""

    # Stable across re-parses of the same bytes, because it is derived from the
    # anchor rather than from a position in a list.  Version history and
    # semantic search both need that and neither is being built yet.
    id: str = ""
    anchor: Optional[Anchor] = None
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)

    def note(self, reason: str) -> None:
        self.evidence.append(reason)


@dataclass
class TextNode(Node):
    """A node whose content is a stretch of text in one paragraph."""

    text: str = ""
    block: Optional[BlockParagraph] = None


@dataclass
class Affiliation(Node):
    """One institution, and the marker that ties authors to it."""

    text: str = ""
    marker: str = ""
    block: Optional[BlockParagraph] = None


@dataclass
class Author(Node):
    """One person.  ``markers`` are the superscripts after the name."""

    name: str = ""
    markers: List[str] = field(default_factory=list)
    email: Optional[str] = None
    is_corresponding: bool = False
    affiliation_ids: List[str] = field(default_factory=list)
    block: Optional[BlockParagraph] = None


@dataclass
class Caption(TextNode):
    """A caption, and what it belongs to."""

    kind: str = "figure"       # "figure" | "table" | "equation"
    label: str = ""            # "Figure 3", "Table 1"
    number: Optional[str] = None
    above: bool = False


@dataclass
class Figure(Node):
    """An image, chart or shape, with its caption if one was found."""

    caption: Optional[Caption] = None
    relationship_ids: List[str] = field(default_factory=list)
    width_emu: Optional[int] = None
    height_emu: Optional[int] = None
    inline: bool = True
    block: Optional[BlockParagraph] = None


@dataclass
class TableNode(Node):
    """A table: its caption, its shape, and its cells as text.

    The cell text is a convenience for the UI.  The authoritative table is
    ``block``, which still knows about merges, widths and formatting.
    """

    caption: Optional[Caption] = None
    rows: int = 0
    columns: int = 0
    header_rows: int = 0
    cells: List[List[str]] = field(default_factory=list)
    block: Optional[BlockTable] = None


@dataclass
class Equation(TextNode):
    """A display or inline equation, numbered if the document numbers them."""

    number: Optional[str] = None
    display: bool = True


@dataclass
class ListItem(TextNode):
    """One numbered or bulleted paragraph."""

    level: int = 0
    ordered: bool = True
    marker_format: Optional[str] = None


@dataclass
class Reference(TextNode):
    """One bibliography entry, kept whole.

    Deliberately not parsed into author/year/title fields.  Getting that wrong
    silently corrupts a citation, and the engine has no need for the parts yet;
    when a Citation plugin arrives it can parse this text and attach its result
    without the core model having guessed first.
    """

    marker: Optional[str] = None
    ordered: bool = False


@dataclass
class Footnote(TextNode):
    """A footnote or endnote, identified by the id its reference points at."""

    note_id: str = ""
    part: str = "word/footnotes.xml"


@dataclass
class Block(Node):
    """A body-level item inside a section, in document order.

    ``kind`` is one of ``paragraph``, ``list_item``, ``table``, ``figure``,
    ``equation``, ``caption``.  ``item`` is the typed node.
    """

    kind: str = "paragraph"
    item: Optional[Node] = None


@dataclass
class Section(Node):
    """A heading and everything under it, including nested subsections."""

    title: str = ""
    level: int = 1
    number: Optional[str] = None
    kind: str = "body"   # "abstract" | "keywords" | "references" | "body" | ...
    heading_block: Optional[BlockParagraph] = None
    content: List[Block] = field(default_factory=list)
    children: List["Section"] = field(default_factory=list)

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def text(self) -> str:
        parts = []
        for item in self.content:
            value = getattr(item.item, "text", None)
            if value:
                parts.append(value)
        return "\n".join(parts)


@dataclass
class Metadata(Node):
    """The front matter: everything before the first real section."""

    title: Optional[TextNode] = None
    subtitle: Optional[TextNode] = None
    authors: List[Author] = field(default_factory=list)
    affiliations: List[Affiliation] = field(default_factory=list)
    corresponding: List[Author] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    abstract: Optional[Section] = None
    keywords: List[str] = field(default_factory=list)
    keywords_node: Optional[TextNode] = None
    doi: Optional[str] = None
    received: Optional[str] = None
    accepted: Optional[str] = None
    published: Optional[str] = None


@dataclass
class Document(Node):
    """One manuscript, understood.

    ``source`` names the package the anchors point into; without it an anchor is
    an offset with no file, and an edit could be applied to the wrong document.
    """

    source: str = ""
    metadata: Metadata = field(default_factory=Metadata)
    sections: List[Section] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
    tables: List[TableNode] = field(default_factory=list)
    equations: List[Equation] = field(default_factory=list)
    footnotes: List[Footnote] = field(default_factory=list)
    headers: List[TextNode] = field(default_factory=list)
    footers: List[TextNode] = field(default_factory=list)
    # Measurements the extractors made about *this* document rather than
    # assumed about documents in general -- body size, heading sizes, the style
    # ids that turned out to be headings.  Kept because they explain every
    # decision below them and are the first thing to look at when one is wrong.
    observations: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def all_sections(self):
        for section in self.sections:
            yield from section.walk()

    def every_section(self):
        """Every section including the abstract, which is held in the metadata.

        ``all_sections`` deliberately walks the body only -- callers that render
        a table of contents do not want the abstract in it.  Anything that needs
        to *reach a node* (the writer resolving a suggestion, ``find``) has to
        see the abstract too, or an edit to an abstract paragraph is refused as
        an unknown node, which is a lie about why it failed.
        """
        abstract = self.metadata.abstract
        if abstract is not None:
            yield from abstract.walk()
        yield from self.all_sections()

    def find(self, node_id: str) -> Optional[Node]:
        for node in self._every_node():
            if node.id == node_id:
                return node
        return None

    def _every_node(self):
        meta = self.metadata
        for node in (meta.title, meta.subtitle, meta.keywords_node):
            if node is not None:
                yield node
        yield from meta.authors
        yield from meta.affiliations
        for section in self.every_section():
            yield section
            for item in section.content:
                if item.item is not None:
                    yield item.item
        yield from self.references
        yield from self.figures
        yield from self.tables
        yield from self.equations
        yield from self.footnotes


__all__ = [
    "Affiliation",
    "Author",
    "Block",
    "Caption",
    "Document",
    "Equation",
    "Figure",
    "Footnote",
    "ListItem",
    "Metadata",
    "Node",
    "Reference",
    "Section",
    "TableNode",
    "TextNode",
]
