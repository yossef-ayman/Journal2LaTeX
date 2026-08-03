"""The .docx as a whole: parts, relationships, and one resolver over all of them.

A manuscript is not one XML file.  The title may live in ``word/document.xml``,
the running head in ``word/header2.xml``, a footnote in ``word/footnotes.xml``,
and every image is a relationship id that means nothing without
``word/_rels/document.xml.rels``.  A reader that opens only the main part sees a
paper with no figures and no headers.

:class:`Package` opens the zip once, keeps every entry's original bytes, parses
the text parts into anchored blocks, and hands out one :class:`StyleResolver`
shared by all of them -- because styles are a property of the document, not of
the part you happened to be reading.

It is read-mostly on purpose.  :meth:`save` writes the package back with each
part's bytes taken from :meth:`Part.serialize`, which returns the *original
object* when nothing in that part changed.  An edit to the abstract therefore
rewrites the abstract's bytes and copies every other byte of the file through
untouched, which is what "modify the existing document" has to mean if it is to
survive Word's own validator.
"""

from __future__ import annotations

import zipfile
from typing import Dict, Iterator, List, Optional, Tuple

from document_engine.ooxml.blocks import Block, Paragraph as BlockParagraph
from document_engine.ooxml.blocks import iter_paragraphs, iter_tables
from document_engine.ooxml.bytes import Part, is_text_part, parse_part
from document_engine.ooxml.styles import StyleResolver

_RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


class Package:
    """An opened .docx, parsed but not interpreted."""

    # Zip entries carry a modification time, and a writer that stamps "now" on
    # every entry produces a different file each time it runs even when not one
    # byte of content changed.  The engine promises byte-identical output for
    # the same input and the same decisions, so the original entry metadata is
    # kept and reused, and anything with no original falls back to this fixed
    # date -- the earliest a zip can represent -- rather than to the clock.
    _EPOCH = (1980, 1, 1, 0, 0, 0)

    def __init__(
        self,
        entries: Dict[str, bytes],
        order: Optional[List[str]] = None,
        infos: Optional[Dict[str, zipfile.ZipInfo]] = None,
    ):
        self.entries = entries
        self.infos: Dict[str, zipfile.ZipInfo] = dict(infos or {})
        # Zip entry order is preserved because Word writes ``[Content_Types].xml``
        # first and some consumers are stricter about that than the spec is.
        self.order = order or list(entries)
        self.parts: Dict[str, Part] = {}
        self.styles = StyleResolver(
            entries.get("word/styles.xml"), entries.get("word/numbering.xml")
        )
        for name in self.order:
            if not is_text_part(name):
                continue
            part = parse_part(entries[name], blocks=True, name=name)
            self.styles.resolve(part.blocks)
            self.parts[name] = part

    # -- opening ---------------------------------------------------------

    @classmethod
    def open(cls, path) -> "Package":
        with zipfile.ZipFile(path) as archive:
            order = archive.namelist()
            entries = {name: archive.read(name) for name in order}
            infos = {info.filename: info for info in archive.infolist()}
        return cls(entries, order, infos)

    # -- reading ---------------------------------------------------------

    @property
    def document(self) -> Optional[Part]:
        return self.parts.get("word/document.xml")

    def paragraphs(self, part: Optional[str] = None) -> Iterator[BlockParagraph]:
        """Every paragraph, in the main document unless a part is named."""
        target = self.parts.get(part or "word/document.xml")
        if target is None:
            return iter(())
        return iter_paragraphs(target.blocks)

    def tables(self, part: Optional[str] = None):
        target = self.parts.get(part or "word/document.xml")
        if target is None:
            return iter(())
        return iter_tables(target.blocks)

    def relationships(self, part: str = "word/document.xml") -> Dict[str, Tuple[str, str]]:
        """``rId`` -> (type, target) for one part's relationships.

        Parsed with a deliberately small reader: the rels part is flat, and the
        only thing the engine needs from it is where an image or hyperlink
        points.
        """
        folder, _, filename = part.rpartition("/")
        rels_name = f"{folder}/_rels/{filename}.rels" if folder else f"_rels/{filename}.rels"
        data = self.entries.get(rels_name)
        if not data:
            return {}
        from xml.parsers import expat

        found: Dict[str, Tuple[str, str]] = {}

        def start(name: str, attrs: Dict[str, str]) -> None:
            if name.rsplit(" ", 1)[-1] != "Relationship":
                return
            rid = attrs.get("Id")
            if rid:
                found[rid] = (attrs.get("Type", ""), attrs.get("Target", ""))

        parser = expat.ParserCreate(namespace_separator=" ")
        parser.StartElementHandler = start
        try:
            parser.Parse(data, True)
        except expat.ExpatError:  # pragma: no cover - malformed rels part
            return {}
        return found

    # -- writing ---------------------------------------------------------

    def serialize(self) -> Dict[str, bytes]:
        """Every entry's output bytes, unchanged parts sharing their input object."""
        out = dict(self.entries)
        for name, part in self.parts.items():
            out[name] = part.serialize()
        return out

    def save(self, path) -> None:
        self.write_to(path)

    def write_to(self, target) -> None:
        """Write the package to a path or an open binary stream.

        Every caller that produces .docx bytes goes through here.  When
        :meth:`Preview.to_bytes` had its own ``writestr`` loop it stamped the
        current clock into each entry header, so the same decisions produced
        different bytes a second apart -- true of the file's metadata, not of
        its content, but indistinguishable from the outside.
        """
        payload = self.serialize()
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in self.order:
                archive.writestr(self._info_for(name), payload[name])

    def _info_for(self, name: str) -> zipfile.ZipInfo:
        """The entry header to write, carrying the original's metadata.

        Reusing the original :class:`zipfile.ZipInfo` object would also carry
        its stored sizes and CRC, which are wrong the moment a part's bytes
        change, so a fresh header is built and only the fields that describe the
        entry rather than its content are copied across.
        """
        original = self.infos.get(name)
        info = zipfile.ZipInfo(
            name, date_time=original.date_time if original else self._EPOCH
        )
        info.compress_type = (
            original.compress_type if original else zipfile.ZIP_DEFLATED
        )
        if original is not None:
            info.create_system = original.create_system
            info.external_attr = original.external_attr
            info.internal_attr = original.internal_attr
        return info

    def changed_parts(self) -> List[str]:
        """Which parts would actually be rewritten -- identity, not equality."""
        return [
            name
            for name, part in self.parts.items()
            if part.serialize() is not self.entries[name]
        ]


__all__ = ["Package"]
