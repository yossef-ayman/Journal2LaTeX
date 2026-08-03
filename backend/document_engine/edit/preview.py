"""See the result before committing to it.

"Generate a preview before saving" only means something if the preview cannot
become the save by accident.  So a preview is computed on a **clone**: the
package is reopened from its original entry bytes, the accepted edits are
applied to that copy, and the caller's package is left in exactly the state it
was in.  A user who previews ten different combinations of accepted suggestions
still has an unmodified document at the end of it.

What comes back is deliberately three things at once, because a reviewer needs
all three and they answer different questions:

* **the edits** -- what would be written, each with its word-level diff;
* **the impact** -- which parts would be rewritten and by how many bytes, which
  is the direct evidence for "only the affected ranges changed";
* **the bytes** -- optionally the whole rendered .docx, for a viewer or a PDF
  conversion, produced without the original ever being written to.

The byte report is the part worth trusting.  Every part of the package is
compared by *identity* against the input, not by equality: an untouched part is
the same object it was read as, so "142 of 143 parts untouched" is a statement
about what happened rather than a claim about what should have.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from document_engine.extract.extractor import SemanticExtractor
from document_engine.model.nodes import Document
from document_engine.ooxml.package import Package
from document_engine.edit.suggestions import SuggestionSet
from document_engine.edit.writer import WordWriter, WriteResult


@dataclass
class PartImpact:
    """How one part of the package would change."""

    name: str
    original_bytes: int
    new_bytes: int
    changed: bool

    @property
    def delta(self) -> int:
        return self.new_bytes - self.original_bytes

    def as_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "original_bytes": self.original_bytes,
            "new_bytes": self.new_bytes,
            "delta": self.delta,
            "changed": self.changed,
        }


@dataclass
class Preview:
    """The outcome of applying a decision set, without having saved anything."""

    result: WriteResult
    impact: List[PartImpact] = field(default_factory=list)
    parts_total: int = 0
    parts_untouched: int = 0
    document: Optional[Document] = None
    _package: Optional[Package] = None

    @property
    def ok(self) -> bool:
        return self.result.ok

    def to_bytes(self) -> bytes:
        """The previewed document as a .docx, built from the clone."""
        if self._package is None:  # pragma: no cover - constructed internally
            raise RuntimeError("this preview has no package behind it")
        buffer = io.BytesIO()
        self._package.write_to(buffer)
        return buffer.getvalue()

    def save(self, path) -> None:
        """Commit the preview.  Same bytes as :meth:`to_bytes`, on disk."""
        if self._package is None:  # pragma: no cover - constructed internally
            raise RuntimeError("this preview has no package behind it")
        self._package.save(path)

    def as_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = dict(self.result.as_dict())
        payload["impact"] = [item.as_dict() for item in self.impact if item.changed]
        payload["package"] = {
            "parts_total": self.parts_total,
            "parts_untouched": self.parts_untouched,
            "parts_rewritten": self.parts_total - self.parts_untouched,
        }
        return payload


class PreviewEngine:
    """Applies a decision set to a copy and reports what it would do."""

    def __init__(self, entries: Dict[str, bytes], order: Optional[List[str]] = None):
        # Held as raw bytes rather than as a Package, so the engine has nothing
        # mutable to leak into a preview in the first place.
        self._entries = dict(entries)
        self._order = list(order or entries)

    @classmethod
    def from_package(cls, package: Package) -> "PreviewEngine":
        return cls(package.entries, package.order)

    @classmethod
    def open(cls, path) -> "PreviewEngine":
        with zipfile.ZipFile(path) as archive:
            order = archive.namelist()
            entries = {name: archive.read(name) for name in order}
        return cls(entries, order)

    def analyze(self, source: str = "") -> Document:
        """The document as it currently stands, for proposing suggestions against."""
        package = Package(dict(self._entries), list(self._order))
        return SemanticExtractor(package).extract(source=source)

    def preview(self, suggestions: SuggestionSet, source: str = "") -> Preview:
        """Apply the accepted suggestions to a clone and report the outcome."""
        package = Package(dict(self._entries), list(self._order))
        document = SemanticExtractor(package).extract(source=source)
        result = WordWriter(package, document).apply(suggestions)

        payload = package.serialize()
        impact: List[PartImpact] = []
        untouched = 0
        for name in self._order:
            original = self._entries[name]
            new = payload[name]
            # Identity, not equality: this is what proves the part was copied
            # rather than rebuilt into something that happens to match.
            changed = new is not original
            if not changed:
                untouched += 1
            impact.append(PartImpact(name, len(original), len(new), changed))

        return Preview(
            result=result,
            impact=impact,
            parts_total=len(self._order),
            parts_untouched=untouched,
            document=document,
            _package=package,
        )


__all__ = ["PartImpact", "Preview", "PreviewEngine"]
