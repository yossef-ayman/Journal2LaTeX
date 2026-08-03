"""The orchestrator: a Word package in, an understood :class:`Document` out.

Nothing here decides anything.  Every judgement lives in the module that owns
it -- headings in :mod:`.signals`, front matter in :mod:`.metadata`, structure
in :mod:`.sections`, objects in :mod:`.objects`, the bibliography in
:mod:`.references` -- and this file only runs them in the one order their
dependencies allow and collects what they say, including what they were unsure
about.

The order matters in exactly one place: the signals have to be measured across
the whole document before any single paragraph can be classified, because every
threshold in them is relative to the rest of the file.
"""

from __future__ import annotations

from typing import List, Optional

from document_engine.extract.metadata import MetadataExtractor
from document_engine.extract.objects import (
    extract_equations,
    extract_figures,
    extract_tables,
)
from document_engine.extract.references import (
    extract_references,
    trailing_bibliography,
)
from document_engine.extract.sections import SectionBuilder
from document_engine.extract.signals import DocumentSignals
from document_engine.model.nodes import Document, Section, TextNode
from document_engine.ooxml.blocks import Paragraph
from document_engine.ooxml.package import Package


class SemanticExtractor:
    """Reads one already-parsed :class:`Package`.

    Read-only by construction: it holds the package, records byte anchors into
    it, and has no code path that writes.  Applying an edit is a separate phase
    working from these anchors.
    """

    def __init__(self, package: Package) -> None:
        self.package = package

    @classmethod
    def open(cls, path) -> "SemanticExtractor":
        return cls(Package.open(path))

    def extract(self, source: str = "") -> Document:
        part = self.package.document
        blocks = list(part.blocks)
        paragraphs = [b for b in blocks if isinstance(b, Paragraph)]

        signals = self._signals = DocumentSignals(paragraphs)
        document = Document(
            id="document",
            source=source or part.name or "word/document.xml",
        )

        builder = SectionBuilder(signals, getattr(self.package, "styles", None))
        front, sections = builder.build(blocks)
        document.sections = sections

        document.metadata = MetadataExtractor(signals).extract(front)
        document.tables = extract_tables(blocks)
        document.figures = extract_figures(blocks)
        document.equations = extract_equations(blocks)
        self._headers_and_footers(document)
        self._references(document, blocks)
        self._abstract(document)

        document.observations = signals.observations()
        document.observations["front_matter_paragraphs"] = len(front)
        document.observations["sections"] = sum(1 for _ in document.all_sections())
        self._warn(document)
        return document

    # -- the pieces that need the whole document to be in hand ------------

    def _abstract(self, document: Document) -> None:
        """A heading-borne abstract wins over a front-matter one, being explicit."""
        for section in document.all_sections():
            if section.kind == "abstract":
                document.metadata.abstract = section
                return
        if document.metadata.abstract is None:
            document.warnings.append("no abstract was identified")

    def _references(self, document: Document, blocks) -> None:
        named = [s for s in document.all_sections() if s.kind == "references"]
        if named:
            document.references = extract_references(named[0], blocks)
            return

        # No heading said so.  Look at the end of the document by shape, which
        # is how a thesis or report with an unlabelled bibliography is caught.
        # Headings are excluded: a bibliography contains entries, and letting a
        # trailing section title in would put it at the head of the list.
        signals = self._signals
        trailing = [
            b
            for b in blocks
            if isinstance(b, Paragraph)
            and not b.in_fallback
            and not b.table_depth
            and not signals.classify(b).is_heading
        ]
        found = trailing_bibliography(trailing[-200:])
        if found:
            document.references = found
            document.warnings.append(
                f"the reference list was identified by shape, not by a heading "
                f"({len(found)} entries)"
            )
            return
        document.warnings.append("no reference list was identified")

    def _headers_and_footers(self, document: Document) -> None:
        for name, part in self.package.parts.items():
            if "header" not in name and "footer" not in name:
                continue
            target = document.headers if "header" in name else document.footers
            for block in getattr(part, "blocks", []):
                if not isinstance(block, Paragraph) or block.in_fallback:
                    continue
                text = block.text().strip()
                if not text:
                    continue
                target.append(
                    TextNode(
                        id=f"{name}:{block.anchor.start}" if block.anchor else name,
                        anchor=block.anchor,
                        text=text,
                        block=block,
                        evidence=[f"from {name}"],
                    )
                )

    def _warn(self, document: Document) -> None:
        meta = document.metadata
        if meta.title is None:
            document.warnings.append("no title was identified")
        elif meta.title.confidence < 0.7:
            document.warnings.append(
                f"the title was a guess (confidence {meta.title.confidence:.2f})"
            )
        if not meta.authors:
            document.warnings.append("no authors were identified")
        if not document.sections:
            document.warnings.append("no sections were identified")
        unlinked = [a.name for a in meta.authors if not a.affiliation_ids]
        if unlinked and meta.affiliations:
            document.warnings.append(
                f"{len(unlinked)} author(s) could not be tied to an affiliation"
            )


__all__ = ["SemanticExtractor"]
