"""The Document Generator must not be able to tell that Phase 1 happened.

Its OOXML foundation moved into the engine and grew a block model.  Both of
those are invisible from here, and these tests are what makes "invisible" a
claim the suite checks rather than one the commit message asserts.
"""

from __future__ import annotations

import zipfile

from document_generator.services import ooxml_bytes as legacy


def test_the_shim_re_exports_the_whole_surface() -> None:
    """The import list of every module that already depended on it."""
    for name in (
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
    ):
        assert hasattr(legacy, name), name


def test_the_shim_is_the_engine_not_a_copy() -> None:
    """Same objects, so there is exactly one implementation to be wrong."""
    from document_engine.ooxml import bytes as engine

    assert legacy.parse_part is engine.parse_part
    assert legacy.Part is engine.Part
    assert legacy.Span is engine.Span


def test_generator_consumers_still_import() -> None:
    import importlib

    for module in (
        "document_generator.services.document_inspector",
        "document_generator.services.mapping_engine",
        "document_generator.services.placeholder_engine",
        "document_generator.services.validation",
    ):
        assert importlib.import_module(module) is not None


def test_legacy_parse_signature_still_takes_one_argument(paper) -> None:
    with zipfile.ZipFile(paper) as archive:
        raw = archive.read("word/document.xml")
    part = legacy.parse_part(raw)
    assert part.paragraphs
    assert part.serialize() is raw
