"""Byte-level OOXML text editing -- moved, and re-exported from here.

The implementation now lives in :mod:`document_engine.ooxml.bytes`, because the
Document Engine is built on it and it is no longer specific to template filling.
This module stays as a re-export so every existing import inside the Document
Generator keeps working unchanged, which is the point: promoting a shared
foundation must not edit the module that already depends on it.

New code should import from ``document_engine.ooxml`` directly.
"""

from document_engine.ooxml.bytes import (  # noqa: F401
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
    "OOXMLEditError",
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
