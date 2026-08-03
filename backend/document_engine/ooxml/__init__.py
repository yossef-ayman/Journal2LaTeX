"""Layer 0 -- the physical model of a Word package.

Everything here knows about OOXML and nothing about research papers.  It records
where things are in the original bytes and what formatting they resolve to; it
has no opinion about which paragraph is a title.

:mod:`document_engine.ooxml.bytes` is the foundation of the whole engine: it
parses a part purely to record byte offsets and splices only changed ranges back
into the original bytes, so a part with no changes is returned as the same
object.  Fidelity is arithmetic here, not effort.

One name is deliberately ambiguous and worth knowing about.  ``Paragraph``
re-exported from here is the *text-node* paragraph of :mod:`.bytes`, because
that is what every existing caller means by it and renaming it would edit
modules that this phase is not allowed to touch.  The richer Phase 1 paragraph
is :class:`document_engine.ooxml.blocks.Paragraph`; import it from
:mod:`.blocks` or :mod:`.package` by its own name.
"""

from document_engine.ooxml.blocks import (
    Anchor,
    Block,
    Bookmark,
    Cell,
    Drawing,
    FieldRef,
    Row,
    Run,
    Table,
    TextBox,
    iter_paragraphs,
    iter_tables,
    modal_body_size_pt,
)
from document_engine.ooxml.builder import BlockBuilder
from document_engine.ooxml.props import ParagraphProps, RunProps, SectionProps
from document_engine.ooxml.styles import NumberingLevel, Style, StyleResolver
from document_engine.ooxml.bytes import (
    OOXMLEditError,
    Paragraph,
    Span,
    Part,
    TextNode,
    W_NS,
    escape_text,
    is_text_part,
    parse_part,
    rewrite_spans,
)

__all__ = [
    "Anchor",
    "Block",
    "BlockBuilder",
    "Bookmark",
    "Cell",
    "Drawing",
    "FieldRef",
    "NumberingLevel",
    "OOXMLEditError",
    "ParagraphProps",
    "Row",
    "Run",
    "RunProps",
    "SectionProps",
    "Style",
    "StyleResolver",
    "Table",
    "TextBox",
    "iter_paragraphs",
    "iter_tables",
    "modal_body_size_pt",
    "Paragraph",
    "Span",
    "Part",
    "TextNode",
    "W_NS",
    "escape_text",
    "is_text_part",
    "parse_part",
    "rewrite_spans",
]
