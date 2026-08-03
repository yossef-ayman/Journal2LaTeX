"""Layer 1 -- the semantic model.

Layer 0 (:mod:`document_engine.ooxml`) knows OOXML and nothing about research
papers.  This layer knows what a research paper is, and points back into Layer 0
by byte-range anchor rather than by copying anything.
"""

from document_engine.model.nodes import (
    Affiliation,
    Author,
    Block,
    Caption,
    Document,
    Equation,
    Figure,
    Footnote,
    ListItem,
    Metadata,
    Node,
    Reference,
    Section,
    TableNode,
    TextNode,
)

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
