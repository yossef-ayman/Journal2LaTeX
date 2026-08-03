"""The bibliography, kept whole.

Every entry is stored as the text the author wrote, with its marker separated
out if it has one.  Nothing is parsed into author, year and title.  That is a
deliberate limit: citation formats disagree in ways that are genuinely
ambiguous, a wrong split silently corrupts a citation, and nothing downstream
needs the parts yet.  When a Citation plugin arrives it can parse this text and
attach its own richer node without the core model having guessed first.

Finding the entries is the real work, and it is done by shape.  A bibliography
is a run of paragraphs at the end of a document that are alike -- all numbered,
or all hanging-indented, or all starting with a name-and-year -- and unlike the
prose above them.  Where the section heading says "References" that is a strong
confirmation, but it is not what the detection depends on.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence

from document_engine.model.nodes import Reference, Section
from document_engine.ooxml.blocks import Paragraph

# "[1]", "1.", "(1)" -- a leading entry marker.
_MARKER = re.compile(r"^\s*(?:\[\s*(\d+)\s*\]|\(\s*(\d+)\s*\)|(\d+)\s*[.)])\s+")
# "Doe, J. (2019)" and its many cousins: a year in parentheses near the front.
_YEAR = re.compile(r"\(\s*(?:19|20)\d{2}[a-z]?\s*\)")
# A year written bare, as most numeric citation styles do: ", 2010."
_BARE_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")


def _marker_of(text: str) -> Optional[str]:
    match = _MARKER.match(text)
    if not match:
        return None
    return next(g for g in match.groups() if g)


def extract_references(section: Section, blocks: Sequence[object]) -> List[Reference]:
    """Read the entries out of a section already identified as the bibliography."""
    paragraphs: List[Paragraph] = []
    for item in section.content:
        block = getattr(item.item, "block", None)
        if isinstance(block, Paragraph) and block.text().strip():
            paragraphs.append(block)
    return _entries(paragraphs)


def _entries(paragraphs: Sequence[Paragraph]) -> List[Reference]:
    if not paragraphs:
        return []

    marked = sum(1 for p in paragraphs if _marker_of(p.text().strip()))
    dated = sum(1 for p in paragraphs if _YEAR.search(p.text()[:120]))
    ordered = marked * 2 >= len(paragraphs)

    out: List[Reference] = []
    for index, paragraph in enumerate(paragraphs):
        text = paragraph.text().strip()
        marker = _marker_of(text)
        body = text
        if marker is not None:
            body = _MARKER.sub("", text, count=1).strip()
        confidence = 0.95 if marker else (0.85 if _YEAR.search(text[:120]) else 0.7)
        reference = Reference(
            id=f"reference:{paragraph.anchor.start}" if paragraph.anchor else f"ref:{index}",
            anchor=paragraph.anchor,
            text=body,
            block=paragraph,
            marker=marker,
            ordered=ordered,
            confidence=confidence,
            evidence=[
                "numbered entry" if marker else "unnumbered entry",
                f"{marked}/{len(paragraphs)} entries numbered, {dated} carry a year",
            ],
        )
        out.append(reference)
    return out


def looks_like_a_bibliography(paragraphs: Sequence[Paragraph]) -> float:
    """How much a run of paragraphs behaves like a reference list, in [0, 1].

    Used when no heading names the section, so that a bibliography at the end of
    a thesis with no "References" line is still found.
    """
    if len(paragraphs) < 3:
        return 0.0
    texts = [p.text().strip() for p in paragraphs if p.text().strip()]
    if not texts:
        return 0.0
    marked = sum(1 for t in texts if _marker_of(t))
    dated = sum(1 for t in texts if _YEAR.search(t[:120]))
    hanging = sum(
        1
        for p in paragraphs
        if (p.effective or p.props) and ((p.effective or p.props).indent_hanging_twips or 0) > 0
    )
    score = max(marked, dated, hanging) / len(texts)
    return min(score, 1.0)


def trailing_bibliography(paragraphs: Sequence[Paragraph]) -> List[Reference]:
    """Find an unheaded reference list at the end of a run of paragraphs.

    Plenty of documents end with a bibliography that no heading announces, or
    whose heading the signals did not call one.  The list is still visible: it
    is the longest *suffix* of the document that behaves like reference entries
    while the text above it does not.  Taking the longest qualifying suffix
    rather than the first is what stops a single numbered sentence in the
    conclusion from being read as a one-entry bibliography.
    """
    usable = [p for p in paragraphs if p.text().strip()]
    if len(usable) < 3:
        return []

    # Which signal this document's entries share is decided by the last few
    # paragraphs, which are certainly entries if there is a bibliography at all.
    tail = usable[-6:]
    # Ordered strongest first, and ties break that way: a numbered list is
    # better evidence than a paragraph that merely mentions a year, so when
    # both fit the tail equally the numbering is what the walk follows.
    tests = [
        ("numbered", lambda p: _marker_of(p.text().strip()) is not None),
        ("dated", lambda p: bool(_YEAR.search(p.text()[:120]))),
        ("hanging", _has_hanging_indent),
        # Weakest, and last for that reason.  It exists because a great many
        # bibliographies are unnumbered, unindented and write the year bare --
        # "..., Journal of Things, 2010." -- which none of the above catch.
        ("has a year", lambda p: bool(_BARE_YEAR.search(p.text()))),
    ]
    ranked = sorted(
        (
            (sum(1 for p in tail if test(p)), -rank, name, test)
            for rank, (name, test) in enumerate(tests)
        ),
        reverse=True,
    )
    hits, _, name, test = ranked[0]
    if hits < len(tail) - 1:
        return []

    # Walk upward while paragraphs keep passing that same test.  One miss is
    # tolerated -- an entry that wraps oddly -- but two in a row means the prose
    # above the bibliography has been reached.  A wider tolerance was tried and
    # swallowed the trailing headings of one real paper, which is the failure
    # this bound exists to prevent.
    start = len(usable)
    misses = 0
    for index in range(len(usable) - 1, -1, -1):
        if test(usable[index]):
            start = index
            misses = 0
        else:
            misses += 1
            if misses > 1:
                break
    entries = usable[start:]
    if len(entries) < 3:
        return []
    return _entries([p for p in entries if test(p)])


def _has_hanging_indent(paragraph: Paragraph) -> bool:
    props = paragraph.effective or paragraph.props
    return bool(props and (props.indent_hanging_twips or 0) > 0)


__all__ = [
    "extract_references",
    "looks_like_a_bibliography",
    "trailing_bibliography",
]
