"""Low-level OOXML text editing primitives.

Both substitution engines in this module -- the placeholder engine (``{{NAME}}``)
and the mapping engine (replace the literal text an operator pointed at) -- need
exactly the same delicate machinery:

* read a paragraph's visible text as one string, even though Word has scattered
  it across arbitrarily many runs;
* replace character *spans* of that string, writing the result back across the
  runs the span actually covered;
* do it without disturbing a single byte of formatting.

That machinery lives here once, so the two engines cannot drift apart and a fix
to run-splitting or whitespace handling benefits both.

The editing is done on the XML directly rather than through a document-object
library.  That is a deliberate choice about fidelity: the only bytes that change
are the text nodes holding a replaced span, so styles, numbering, section
properties, headers, footers, tables, images, fonts and page setup all survive
exactly as the operator designed them in Word.  Rebuilding a document through a
library, by contrast, silently normalises parts of it.
"""

from __future__ import annotations

import re
from io import BytesIO
from typing import List, Sequence, Tuple
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

# Parts of a .docx that carry visible text.  Anything else in the package is
# copied through untouched.
_TEXT_PART_PATTERNS = (
    re.compile(r"^word/document\.xml$"),
    re.compile(r"^word/header\d*\.xml$"),
    re.compile(r"^word/footer\d*\.xml$"),
    re.compile(r"^word/footnotes\.xml$"),
    re.compile(r"^word/endnotes\.xml$"),
    re.compile(r"^word/comments\.xml$"),
)

# A span replacement: (start, end, replacement text) over a paragraph's
# concatenated visible text.
Span = Tuple[int, int, str]

# Parked in the text while rewriting so a replacement that itself looks like a
# match ("{{" from a placeholder value, or a literal that contains another
# mapped literal) can never be re-matched in the same pass.
_SENTINEL = "\x00REPL\x00"


def is_text_part(name: str) -> bool:
    """Whether a package entry is one whose text should be processed."""
    return any(pattern.match(name) for pattern in _TEXT_PART_PATTERNS)


def register_namespaces(xml_bytes: bytes) -> None:
    """Preserve the document's namespace prefixes when re-serialising.

    ElementTree invents ``ns0:``-style prefixes unless the real ones are
    registered.  Word tolerates that, but it makes every generated file diff
    wildly against its template and is a common source of "why does this look
    different" reports, so the original prefixes are kept.
    """
    for _event, (prefix, uri) in ET.iterparse(  # type: ignore[misc]
        BytesIO(xml_bytes), events=["start-ns"]
    ):
        ET.register_namespace(prefix, uri)


def paragraph_text_nodes(paragraph: ET.Element) -> List[ET.Element]:
    """The ``w:t`` nodes of a paragraph, in reading order.

    Nodes inside a deleted revision are skipped: a ``w:t`` under ``w:del`` is not
    rendered, so text that only exists in tracked-change history must never be
    matched or replaced.
    """
    deleted_runs: List[ET.Element] = []
    for deletion in paragraph.iter(f"{W}del"):
        deleted_runs.extend(deletion.iter(f"{W}r"))

    nodes: List[ET.Element] = []
    for run in paragraph.iter(f"{W}r"):
        if any(run is dead for dead in deleted_runs):
            continue
        nodes.extend(run.findall(f"{W}t"))
    return nodes


def paragraph_text(paragraph: ET.Element) -> str:
    """A paragraph's visible text, reassembled across its runs."""
    return "".join(node.text or "" for node in paragraph_text_nodes(paragraph))


def set_node_text(node: ET.Element, text: str) -> None:
    """Write ``text`` into a ``w:t``, honouring leading/trailing spaces.

    Without ``xml:space="preserve"`` Word discards edge whitespace, which turns
    "Dear <editor> ," into "Dear Editor," and silently eats the spacing the
    template author chose.
    """
    node.text = text
    if text != text.strip():
        node.set(XML_SPACE, "preserve")


def _apply_line_breaks(run: ET.Element | None, node: ET.Element, text: str) -> None:
    """Write possibly multi-line ``text`` into a single ``w:t``.

    A ``w:t`` cannot contain a newline, so additional lines become ``w:br`` +
    ``w:t`` siblings appended to the *same* run.  Staying inside the run is what
    keeps the template's formatting: an author list broken over three lines is
    still typeset in the run's font, size and colour.
    """
    lines = text.split("\n")
    set_node_text(node, lines[0])
    if len(lines) == 1:
        return
    if run is None:
        # Cannot split safely -- fall back to spaces rather than corrupt the XML.
        set_node_text(node, " ".join(lines))
        return

    insert_at = list(run).index(node) + 1
    for line in lines[1:]:
        run.insert(insert_at, ET.Element(f"{W}br"))
        insert_at += 1
        text_node = ET.Element(f"{W}t")
        set_node_text(text_node, line)
        run.insert(insert_at, text_node)
        insert_at += 1


def rewrite_spans(paragraph: ET.Element, spans: Sequence[Span]) -> int:
    """Replace character spans of a paragraph's text. Returns how many applied.

    ``spans`` are offsets into the string returned by :func:`paragraph_text` and
    must not overlap; they are applied right to left so the offsets of the spans
    still to be processed stay valid as earlier text is rewritten.
    """
    if not spans:
        return 0
    nodes = paragraph_text_nodes(paragraph)
    if not nodes:
        return 0

    texts = [node.text or "" for node in nodes]
    # Owning run per text node, needed to append line-break siblings.
    owner: List[ET.Element | None] = [None] * len(nodes)
    for run in paragraph.iter(f"{W}r"):
        children = list(run)
        for idx, node in enumerate(nodes):
            if any(child is node for child in children):
                owner[idx] = run

    offsets: List[int] = []
    running = 0
    for text in texts:
        offsets.append(running)
        running += len(text)

    def locate(position: int) -> Tuple[int, int]:
        """(node index, offset within node) for an absolute character position."""
        for idx in range(len(texts) - 1, -1, -1):
            if position >= offsets[idx]:
                return idx, position - offsets[idx]
        return 0, 0

    applied = 0
    for start, end, replacement in sorted(spans, key=lambda s: s[0], reverse=True):
        if start >= end:
            continue
        start_idx, start_off = locate(start)
        end_idx, end_off = locate(end - 1)
        end_off += 1  # exclusive

        if start_idx == end_idx:
            text = texts[start_idx]
            texts[start_idx] = text[:start_off] + _SENTINEL + text[end_off:]
        else:
            texts[start_idx] = texts[start_idx][:start_off] + _SENTINEL
            for middle in range(start_idx + 1, end_idx):
                texts[middle] = ""
            texts[end_idx] = texts[end_idx][end_off:]
        texts[start_idx] = texts[start_idx].replace(_SENTINEL, replacement, 1)
        applied += 1

        # Offsets shift for everything after this span; recompute.
        running = 0
        for idx, text in enumerate(texts):
            offsets[idx] = running
            running += len(text)

    for idx, (node, text) in enumerate(zip(nodes, texts)):
        if "\n" in text:
            _apply_line_breaks(owner[idx], node, text)
        else:
            set_node_text(node, text)

    return applied
