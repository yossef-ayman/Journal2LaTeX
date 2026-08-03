"""Byte-level OOXML text editing.

This module replaces text inside a Word part **without ever re-serialising the
XML**.  That distinction is the whole point of the file, and it is worth being
explicit about why, because the obvious approach — parse with ElementTree, edit
the tree, ``ET.tostring`` it back — is what this code exists to avoid.

Re-serialising a Word part is lossy in ways Word notices and LibreOffice does
not:

* the XML declaration loses ``standalone="yes"``;
* namespace declarations are moved to wherever the serialiser wants them and are
  renamed (``ns0:``) unless every prefix in the document was pre-registered —
  and prefixes that appear only inside ``mc:Ignorable`` or ``w14:``-style
  attribute *values* cannot be registered from the parse alone, so
  ``mc:Ignorable="w14 wp14"`` can end up naming prefixes that no longer exist;
* attribute order changes, ``<w:t/>`` and ``<w:t></w:t>`` are normalised into
  each other, and whitespace between elements is rewritten.

Any one of those is enough for Word to report *"The file appears to be
corrupted"* when exporting to PDF, even though the same file opens fine.  They
are also enough to shift spacing and paragraph positions.

So: the original part bytes are parsed only to *locate* things.  Every ``w:t``
whose text is unchanged keeps its exact original bytes, including its start tag,
its attributes and its whitespace.  Only the byte ranges of text that genuinely
changed are spliced.  A generated document therefore differs from its template
in exactly the bytes of the values that were replaced, and nowhere else.

The parser is :mod:`xml.parsers.expat` from the standard library, which reports
a byte offset for every event.  No third-party dependency is introduced: the
converter is stdlib-only for OOXML and stays that way.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple
from xml.parsers import expat

from document_engine.ooxml.blocks import scan_tag_end
from document_engine.ooxml.builder import BlockBuilder

W_NS ="http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# A span replacement over a paragraph's concatenated visible text.
Span = Tuple[int, int, str]

# Parts of a .docx that carry visible text.  Everything else in the package is
# copied through byte-for-byte.
_TEXT_PART_PATTERNS = (
    re.compile(r"^word/document\d*\.xml$"),
    re.compile(r"^word/header\d*\.xml$"),
    re.compile(r"^word/footer\d*\.xml$"),
    re.compile(r"^word/footnotes\.xml$"),
    re.compile(r"^word/endnotes\.xml$"),
    re.compile(r"^word/comments\.xml$"),
)


def is_text_part(name: str) -> bool:
    """Whether a package entry is one whose text should be processed."""
    return any(pattern.match(name) for pattern in _TEXT_PART_PATTERNS)


class OOXMLEditError(RuntimeError):
    """The part could not be parsed, so it must be copied through untouched."""


def escape_text(text: str) -> str:
    """XML-escape character data.

    Only the three characters that must be escaped in content are escaped, which
    is what Word itself writes; quotes are left alone so the output looks like a
    Word file rather than a generic serialiser's.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class TextNode:
    """One ``w:t`` element, located in the original bytes.

    ``text`` is the decoded character data.  Assigning :attr:`replacement` marks
    the node for splicing; leaving it ``None`` guarantees the node's bytes are
    emitted unchanged.
    """

    __slots__ = (
        "text",
        "tag_start",
        "content_start",
        "content_end",
        "self_closing",
        "has_space_attr",
        "run_index",
        "deleted",
        "replacement",
    )

    def __init__(self) -> None:
        self.text: str = ""
        self.tag_start: int = 0
        self.content_start: int = 0
        self.content_end: int = 0
        self.self_closing: bool = False
        self.has_space_attr: bool = False
        self.run_index: int = -1
        self.deleted: bool = False
        self.replacement: Optional[str] = None

    @property
    def changed(self) -> bool:
        return self.replacement is not None and self.replacement != self.text


class Paragraph:
    """A ``w:p`` and the ``w:t`` nodes that belong to it directly.

    "Directly" matters: a text box nests a whole ``w:p`` inside a run of an outer
    paragraph, and Word duplicates that content across the Choice and Fallback
    branches of ``mc:AlternateContent``.  Attributing each ``w:t`` to its
    innermost paragraph keeps the inner text from being spliced into the outer
    paragraph's string, where offsets would be meaningless.
    """

    __slots__ = ("nodes", "in_table", "in_text_box")

    def __init__(self, in_table: bool = False, in_text_box: bool = False) -> None:
        self.nodes: List[TextNode] = []
        self.in_table = in_table
        self.in_text_box = in_text_box

    @property
    def live_nodes(self) -> List[TextNode]:
        """Nodes that are actually rendered — a ``w:t`` under ``w:del`` is not."""
        return [node for node in self.nodes if not node.deleted]

    def text(self) -> str:
        """The paragraph's visible text, reassembled across its runs."""
        return "".join(node.text for node in self.live_nodes)


class Part:
    """A parsed text part: the original bytes plus the paragraphs found in them."""

    __slots__ = (
        "data",
        "paragraphs",
        "_nodes",
        "counts",
        "name",
        "blocks",
        "sections",
        "bookmarks",
        "fields",
    )

    def __init__(self, data: bytes, name: str = "") -> None:
        self.data = data
        self.paragraphs: List[Paragraph] = []
        self._nodes: List[TextNode] = []
        # Structural tallies used by the validation report.
        self.counts: Dict[str, int] = {}
        # Package-relative name of the part, e.g. "word/document.xml".  Anchors
        # carry it so a block knows which part its bytes live in.
        self.name = name
        # The Phase 1 block model.  Empty unless ``parse_part(..., blocks=True)``
        # asked for it, which is what keeps the Document Generator's cost and
        # behaviour exactly as they were.
        self.blocks: List[object] = []
        self.sections: List[object] = []
        self.bookmarks: List[object] = []
        self.fields: List[object] = []

    def serialize(self) -> bytes:
        """The part's bytes with only the changed text nodes spliced in.

        Returns the *original object* when nothing changed, so an untouched part
        is provably identical rather than merely equal.
        """
        edits = [node for node in self._nodes if node.changed]
        if not edits:
            return self.data

        out = bytearray()
        cursor = 0
        for node in sorted(edits, key=lambda n: n.tag_start):
            assert node.replacement is not None
            body = _render_text(node.replacement)
            if node.self_closing:
                # `<w:t/>` cannot hold text; grow it into a real element, reusing
                # its own attribute bytes so nothing else about it changes.
                tag = self.data[node.tag_start : node.content_end].decode("utf-8")
                open_tag = tag[:-2].rstrip() + ">"  # drop the trailing "/>"
                open_tag = _with_space_preserve(open_tag, node.replacement)
                out += self.data[cursor : node.tag_start]
                out += open_tag.encode("utf-8")
                out += body.encode("utf-8")
                out += b"</w:t>"
                cursor = node.content_end
                continue

            if _needs_space_preserve(node.replacement) and not node.has_space_attr:
                tag = self.data[node.tag_start : node.content_start].decode("utf-8")
                out += self.data[cursor : node.tag_start]
                out += _with_space_preserve(tag, node.replacement).encode("utf-8")
            else:
                out += self.data[cursor : node.content_start]
            out += body.encode("utf-8")
            cursor = node.content_end

        out += self.data[cursor:]
        return bytes(out)


def _needs_space_preserve(text: str) -> bool:
    """Whether Word would otherwise eat this text's leading/trailing spaces."""
    first = text.split("\n")[0]
    last = text.split("\n")[-1]
    return first != first.lstrip() or last != last.rstrip()


def _with_space_preserve(open_tag: str, text: str) -> str:
    """Add ``xml:space="preserve"`` to a start tag if the text needs it."""
    if not _needs_space_preserve(text) or 'xml:space' in open_tag:
        return open_tag
    return open_tag[:-1].rstrip() + ' xml:space="preserve">'


def _render_text(text: str) -> str:
    """Character data for a ``w:t``, with newlines becoming real Word breaks.

    A ``w:t`` cannot contain a newline.  Emitting ``</w:t><w:br/><w:t …>`` closes
    and reopens the text element *inside the same run*, so a three-line author
    block or a wrapped title keeps the run's font, size, colour and spacing —
    which is what makes the value behave as one logical field rather than a set
    of fragments.
    """
    lines = text.split("\n")
    rendered = escape_text(lines[0])
    for line in lines[1:]:
        space = ' xml:space="preserve"' if line != line.strip() else ""
        rendered += f'</w:t><w:br/><w:t{space}>{escape_text(line)}'
    return rendered


def _local(name: str) -> str:
    """Local name of an expat-reported qualified name (namespace URI + space)."""
    return name.rsplit(" ", 1)[-1] if " " in name else name.split(":")[-1]


def _in_w(name: str, local: str) -> bool:
    return name == f"{W_NS} {local}"


def parse_part(data: bytes, blocks: bool = False, name: str = "") -> Part:
    """Locate every paragraph and ``w:t`` in a part, recording byte offsets.

    With ``blocks=True`` the same single traversal also builds the Phase 1 block
    model -- paragraphs with resolved-later formatting, runs, tables, drawings,
    bookmarks, fields and section breaks -- and leaves it on :attr:`Part.blocks`.
    The default is off, so every existing caller gets byte-for-byte the same
    behaviour, at the same cost, as it did before the block model existed.
    """
    part = Part(data, name)
    builder = BlockBuilder(data, name) if blocks else None
    parser = expat.ParserCreate(namespace_separator=" ")

    # Stacks tracking where we are; paragraphs nest inside text boxes.
    paragraph_stack: List[Paragraph] = []
    run_depth: List[int] = []
    del_depth = [0]
    table_depth = [0]
    box_depth = [0]
    current: List[Optional[TextNode]] = [None]
    run_counter = [0]
    counts: Dict[str, int] = {
        "paragraphs": 0,
        "tables": 0,
        "table_rows": 0,
        "table_cells": 0,
        "text_boxes": 0,
        "runs": 0,
        "breaks": 0,
        "drawings": 0,
        "hyperlinks": 0,
        "bookmarks": 0,
    }

    def start_tag_end(offset: int) -> int:
        """Byte index just past the ``>`` that closes the start tag at ``offset``."""
        try:
            return scan_tag_end(data, offset)
        except ValueError as exc:
            raise OOXMLEditError("unterminated start tag") from exc

    def on_start(name: str, attrs: Dict[str, str]) -> None:
        offset = parser.CurrentByteIndex
        if builder is not None:
            builder.start(name, attrs, offset)
        if _in_w(name, "p"):
            paragraph = Paragraph(
                in_table=table_depth[0] > 0, in_text_box=box_depth[0] > 0
            )
            paragraph_stack.append(paragraph)
            part.paragraphs.append(paragraph)
            counts["paragraphs"] += 1
        elif _in_w(name, "tbl"):
            table_depth[0] += 1
            counts["tables"] += 1
        elif _in_w(name, "tr"):
            counts["table_rows"] += 1
        elif _in_w(name, "tc"):
            counts["table_cells"] += 1
        elif _in_w(name, "txbxContent"):
            box_depth[0] += 1
            counts["text_boxes"] += 1
        elif _in_w(name, "br"):
            counts["breaks"] += 1
        elif _in_w(name, "drawing") or _in_w(name, "pict"):
            counts["drawings"] += 1
        elif _in_w(name, "hyperlink"):
            counts["hyperlinks"] += 1
        elif _in_w(name, "bookmarkStart"):
            counts["bookmarks"] += 1
        elif _in_w(name, "del"):
            del_depth[0] += 1
        elif _in_w(name, "r"):
            run_counter[0] += 1
            run_depth.append(run_counter[0])
            counts["runs"] += 1
        elif _in_w(name, "t"):
            node = TextNode()
            node.tag_start = offset
            node.content_start = start_tag_end(offset)
            node.has_space_attr = (
                b"xml:space" in data[offset : node.content_start]
            )
            node.run_index = run_depth[-1] if run_depth else -1
            node.deleted = del_depth[0] > 0
            current[0] = node
            part._nodes.append(node)
            if paragraph_stack:
                paragraph_stack[-1].nodes.append(node)

    def on_end(name: str) -> None:
        offset = parser.CurrentByteIndex
        if builder is not None:
            builder.end(name, offset)
        if _in_w(name, "p"):
            if paragraph_stack:
                paragraph_stack.pop()
        elif _in_w(name, "del"):
            del_depth[0] = max(0, del_depth[0] - 1)
        elif _in_w(name, "tbl"):
            table_depth[0] = max(0, table_depth[0] - 1)
        elif _in_w(name, "txbxContent"):
            box_depth[0] = max(0, box_depth[0] - 1)
        elif _in_w(name, "r"):
            if run_depth:
                run_depth.pop()
        elif _in_w(name, "t"):
            node = current[0]
            current[0] = None
            if node is None:
                return
            if offset < node.content_start:
                # Expat reports an empty-element tag's end at its start: `<w:t/>`.
                node.self_closing = True
                node.content_end = node.content_start
            else:
                node.content_end = offset

    def on_chardata(text: str) -> None:
        if builder is not None:
            builder.chardata(text)
        node = current[0]
        if node is not None:
            node.text += text

    parser.StartElementHandler = on_start
    parser.EndElementHandler = on_end
    parser.CharacterDataHandler = on_chardata
    # Word writes no entities of its own; expanding none of them keeps offsets
    # honest and stops a malicious template from expanding into the output.
    parser.buffer_text = False

    try:
        parser.Parse(data, True)
    except expat.ExpatError as exc:  # pragma: no cover - malformed template
        raise OOXMLEditError(f"part is not well-formed XML: {exc}") from exc

    if builder is not None:
        builder.finish()
        part.blocks = builder.blocks
        part.sections = builder.sections
        part.bookmarks = builder.bookmarks
        part.fields = builder.fields

    part.counts = counts
    return part


def rewrite_spans(paragraph: Paragraph, spans: Sequence[Span]) -> int:
    """Replace character spans of a paragraph's text. Returns how many applied.

    ``spans`` index the string returned by :meth:`Paragraph.text` and must not
    overlap.  They are applied right to left so the offsets of spans still to be
    processed stay valid.

    The whole replacement lands in the **first** node the span touches and the
    rest of the covered nodes are emptied.  That is what makes a mapped value one
    logical field: an author list scattered over nine runs comes back as a single
    contiguous string in the first run's formatting, instead of being dribbled
    back across the fragments it happened to be split into.
    """
    nodes = paragraph.live_nodes
    if not nodes or not spans:
        return 0

    texts = [node.text for node in nodes]
    offsets: List[int] = []
    running = 0
    for text in texts:
        offsets.append(running)
        running += len(text)
    total = running

    def locate(position: int) -> Tuple[int, int]:
        for idx in range(len(texts) - 1, -1, -1):
            if position >= offsets[idx]:
                return idx, position - offsets[idx]
        return 0, 0

    applied = 0
    for start, end, replacement in sorted(spans, key=lambda s: s[0], reverse=True):
        if start >= end or start < 0 or end > total:
            continue
        start_idx, start_off = locate(start)
        end_idx, end_off = locate(end - 1)
        end_off += 1  # exclusive

        head = texts[start_idx][:start_off]
        tail = texts[end_idx][end_off:]
        if start_idx == end_idx:
            texts[start_idx] = head + replacement + tail
        else:
            texts[start_idx] = head + replacement
            for middle in range(start_idx + 1, end_idx):
                texts[middle] = ""
            texts[end_idx] = tail
        applied += 1

        running = 0
        for idx, text in enumerate(texts):
            offsets[idx] = running
            running += len(text)
        total = running

    if applied:
        for node, text in zip(nodes, texts):
            if text != node.text:
                node.replacement = text
    return applied
