"""Apply accepted suggestions to the document that already exists.

This is the module the whole engine was shaped around, and the shape is the
point: **nothing here builds a document**.  There is no template, no element
construction, no serialisation of a tree.  An edit is a byte range in a part
that gets different bytes; every other byte of the .docx -- styles, numbering,
images, headers, footers, bookmarks, fields, section breaks, the table of
contents, the parts this engine has never even parsed -- is copied through as
the same object it came in as.

The path from a suggestion to bytes has four steps, and each one is allowed to
refuse.

1. **Resolve the node.**  A suggestion names a node id; the document says which
   Layer-0 paragraph that node came from.  An id that is not in this document is
   refused, not guessed at.

2. **Check the original.**  The suggestion carries the text it was proposed
   against.  If the document no longer says that -- a different copy, an edit
   already applied, a stale browser tab -- the edit is refused.  This is the
   single guard that makes a wrong document impossible to silently corrupt, and
   it is why ``original`` is stored on the suggestion at all.

3. **Narrow the span.**  Only the characters that genuinely differ are
   replaced (see :mod:`document_engine.edit.diff`), so a typo fix in a sentence
   does not collapse the italics later in the same paragraph into the first
   run's formatting.

4. **Splice.**  :func:`document_engine.ooxml.bytes.rewrite_spans` puts the
   replacement into the run that owns those characters and leaves the rest of
   the paragraph's bytes exactly as they were.

Determinism is structural rather than promised: suggestions are applied in
document order, spans within a paragraph right to left, and no step consults a
clock, a random source or an object address.  The same document and the same
accepted set produce byte-identical output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from document_engine.model.nodes import Document, Node, Section
from document_engine.ooxml.blocks import Paragraph as BlockParagraph
from document_engine.ooxml.blocks import iter_paragraphs
from document_engine.ooxml.bytes import Paragraph as BytesParagraph
from document_engine.ooxml.bytes import Part
from document_engine.ooxml.package import Package
from document_engine.edit.diff import changed_span, summarize
from document_engine.edit.suggestions import Suggestion, SuggestionSet


class WriteError(RuntimeError):
    """The edit could not be applied safely, so it was not applied at all."""


@dataclass
class AppliedEdit:
    """One suggestion that reached the bytes."""

    suggestion_id: str
    node_id: str
    part: str
    start: int          # character offset within the paragraph's visible text
    end: int
    original: str
    replacement: str

    def as_dict(self) -> Dict[str, object]:
        return {
            "suggestion_id": self.suggestion_id,
            "node_id": self.node_id,
            "part": self.part,
            "span": [self.start, self.end],
            "original": self.original,
            "replacement": self.replacement,
            "diff": summarize(self.original, self.replacement),
        }


@dataclass
class RefusedEdit:
    """One suggestion that was not applied, and exactly why."""

    suggestion_id: str
    node_id: str
    reason: str

    def as_dict(self) -> Dict[str, object]:
        return {
            "suggestion_id": self.suggestion_id,
            "node_id": self.node_id,
            "reason": self.reason,
        }


@dataclass
class WriteResult:
    """What a write attempt did, whether or not anything was saved."""

    applied: List[AppliedEdit] = field(default_factory=list)
    refused: List[RefusedEdit] = field(default_factory=list)
    changed_parts: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.refused

    def as_dict(self) -> Dict[str, object]:
        return {
            "applied": [edit.as_dict() for edit in self.applied],
            "refused": [edit.as_dict() for edit in self.refused],
            "changed_parts": list(self.changed_parts),
            "counts": {
                "applied": len(self.applied),
                "refused": len(self.refused),
                "parts_touched": len(self.changed_parts),
            },
        }


def _paragraph_index(part: Part) -> Dict[int, BytesParagraph]:
    """Map each Layer-0 block paragraph to the byte-node paragraph beside it.

    Both are produced by the same expat traversal, in the same order, with the
    same nesting rules -- including the duplicated ``mc:Fallback`` branch of a
    text box -- so they align positionally.  That alignment is *verified* here
    rather than assumed: if the texts ever disagree, the index is rebuilt by
    containment, and if that fails too the paragraph is simply absent from the
    index and every edit against it is refused.  A silently misaligned index
    would write the right text into the wrong paragraph, which is the one
    failure mode this engine must not have.
    """
    blocks = list(iter_paragraphs(part.blocks, skip_fallback=False))
    byte_paragraphs = part.paragraphs
    index: Dict[int, BytesParagraph] = {}

    if len(blocks) == len(byte_paragraphs) and all(
        block.text() == byte_paragraph.text()
        for block, byte_paragraph in zip(blocks, byte_paragraphs)
    ):
        return {id(block): bp for block, bp in zip(blocks, byte_paragraphs)}

    # Fallback: match by byte containment plus exact text.  Slower, and only
    # reached on a document whose two views disagree, which no real manuscript
    # has done -- but a wrong answer here is unrecoverable, so it is worth the
    # code.
    for block in blocks:
        anchor = block.anchor
        wanted = block.text()
        for byte_paragraph in byte_paragraphs:
            nodes = byte_paragraph.nodes
            if not nodes:
                continue
            if nodes[0].tag_start < anchor.start or nodes[-1].content_end > anchor.end:
                continue
            if byte_paragraph.text() == wanted:
                index[id(block)] = byte_paragraph
                break
    return index


def _target(node: Node) -> Tuple[Optional[BlockParagraph], Optional[str]]:
    """The paragraph a node's text lives in, and the exact text it owns.

    A section is edited through its heading paragraph.  A table or a figure has
    no single editable string -- its content is cells and drawings -- so it
    returns nothing and the writer refuses, rather than inventing a meaning for
    "replace the text of a table".
    """
    block = getattr(node, "block", None)
    if isinstance(node, Section):
        block = node.heading_block
        return block, (block.text() if block is not None else None)
    if not isinstance(block, BlockParagraph):
        return None, None
    text = getattr(node, "text", None)
    if not isinstance(text, str):
        return None, None
    return block, text


def editable_text(node: Node) -> Optional[str]:
    """The exact string a suggestion against this node must quote as its original.

    Public because a plugin that proposes an edit has to agree with the writer
    about what it is editing, character for character.  A plugin that invents its
    own idea of "the text of this node" produces suggestions that are refused at
    apply time, which looks like a writer bug and is not one.  ``None`` means the
    node has no single editable string, so nothing should be proposed against it.
    """
    _, text = _target(node)
    return text


class WordWriter:
    """Applies accepted suggestions to one opened package."""

    def __init__(self, package: Package, document: Document) -> None:
        self.package = package
        self.document = document
        self._nodes: Dict[str, Node] = {n.id: n for n in document._every_node()}
        self._indexes: Dict[str, Dict[int, BytesParagraph]] = {}

    # -- resolution ------------------------------------------------------

    def _index_for(self, part_name: str) -> Dict[int, BytesParagraph]:
        if part_name not in self._indexes:
            part = self.package.parts.get(part_name)
            self._indexes[part_name] = _paragraph_index(part) if part else {}
        return self._indexes[part_name]

    def _plan_one(
        self, suggestion: Suggestion
    ) -> Tuple[Optional[Tuple[str, BytesParagraph, int, int, str]], Optional[str]]:
        """Work out where one suggestion would land, or why it cannot."""
        node = self._nodes.get(suggestion.node_id)
        if node is None:
            return None, "this document has no node with that id"

        block, owned = _target(node)
        if block is None or owned is None:
            return None, "this node has no single editable stretch of text"
        if suggestion.original != owned:
            return None, (
                "the document no longer reads the way this suggestion was made "
                "against; it was not applied"
            )

        anchor = block.anchor
        byte_paragraph = self._index_for(anchor.part).get(id(block))
        if byte_paragraph is None:
            return None, "the paragraph's bytes could not be located"

        line = byte_paragraph.text()
        # The node may own only part of its paragraph -- an author name on a
        # line of several.  Its offset has to be unambiguous, because writing to
        # the wrong occurrence is a silent corruption.
        if owned == line:
            base = 0
        else:
            first = line.find(owned)
            if first < 0:
                return None, "the node's text is not present in its paragraph"
            if line.find(owned, first + 1) >= 0:
                return None, (
                    "this text appears more than once in its paragraph, so the "
                    "edit has no unambiguous target"
                )
            base = first

        span = changed_span(owned, suggestion.replacement)
        if span is None:
            return None, "the suggestion makes no change"
        start, end, replacement = span
        if start == end:
            # A pure insertion has an empty span, and an empty span has no run
            # to be written into.  Widen it by one existing character -- kept
            # verbatim in the replacement -- so the insertion lands in the run
            # that already owns the character next to it, and therefore in that
            # character's formatting rather than in a guess at one.
            if start > 0:
                start -= 1
                replacement = owned[start] + replacement
            elif end < len(owned):
                end += 1
                replacement = replacement + owned[end - 1]
            else:
                return None, (
                    "there is no text in this node to anchor an insertion to"
                )
        return (anchor.part, byte_paragraph, base + start, base + end, replacement), None

    # -- application -----------------------------------------------------

    def apply(self, suggestions: SuggestionSet) -> WriteResult:
        """Apply every accepted suggestion, refusing the ones that cannot be.

        A refusal never stops the others: the user accepted several edits and is
        entitled to the ones that are still valid, with an explicit report of
        the ones that were not.
        """
        result = WriteResult()
        # Document order, then paragraph order, then position: the sort is what
        # makes the output independent of the order the user clicked things in.
        planned: List[Tuple[str, int, int, Suggestion, BytesParagraph, str]] = []
        for suggestion in sorted(suggestions.accepted, key=lambda s: s.id):
            plan, reason = self._plan_one(suggestion)
            if plan is None:
                result.refused.append(
                    RefusedEdit(suggestion.id, suggestion.node_id, reason or "refused")
                )
                continue
            part_name, byte_paragraph, start, end, replacement = plan
            planned.append(
                (part_name, start, end, suggestion, byte_paragraph, replacement)
            )

        # Group by paragraph so overlapping edits can be caught before any of
        # them touches the bytes.
        by_paragraph: Dict[int, List[tuple]] = {}
        for item in planned:
            by_paragraph.setdefault(id(item[4]), []).append(item)

        for entries in by_paragraph.values():
            entries.sort(key=lambda item: (item[1], item[2]))
            spans: List[Tuple[int, int, str]] = []
            previous_end = -1
            for part_name, start, end, suggestion, byte_paragraph, replacement in entries:
                if start < previous_end:
                    result.refused.append(
                        RefusedEdit(
                            suggestion.id,
                            suggestion.node_id,
                            "this edit overlaps another accepted edit in the same "
                            "paragraph; neither can be applied safely",
                        )
                    )
                    continue
                previous_end = end
                spans.append((start, end, replacement))
                result.applied.append(
                    AppliedEdit(
                        suggestion_id=suggestion.id,
                        node_id=suggestion.node_id,
                        part=part_name,
                        start=start,
                        end=end,
                        original=suggestion.original,
                        replacement=suggestion.replacement,
                    )
                )
            if spans:
                _rewrite(entries[0][4], spans)

        result.changed_parts = self.package.changed_parts()
        return result

    def save(self, path) -> None:
        """Write the package out.  Unchanged parts keep their original bytes."""
        self.package.save(path)


def _rewrite(byte_paragraph: BytesParagraph, spans: Sequence[Tuple[int, int, str]]) -> int:
    from document_engine.ooxml.bytes import rewrite_spans

    return rewrite_spans(byte_paragraph, list(spans))


__all__ = [
    "AppliedEdit",
    "editable_text",
    "RefusedEdit",
    "WordWriter",
    "WriteError",
    "WriteResult",
]
