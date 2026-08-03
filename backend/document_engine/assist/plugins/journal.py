"""Journal style, inferred from the manuscript instead of from a journal.

The engine must work on Springer, IEEE, Elsevier, MDPI, Nature, Wiley, theses
and plain Word files, so it cannot hold a rule table for any of them.  What it
can do is notice that a document has *almost* settled on a convention and points
at the exceptions: eleven headings in title case and one in sentence case is a
finding; six and five is a choice.

The conventions checked are the ones a document either has or does not have,
independent of publisher: the capitalisation of headings, a trailing period on a
heading, whitespace at the ends of a heading, and gaps or repeats in its own
section numbering.  Numbering problems are notes -- renumbering a section means
renumbering every cross-reference to it, and this plugin does not touch
cross-references.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterator, List, Optional, Tuple

from document_engine.assist.plugin import Context, SuggestionPlugin
from document_engine.model.nodes import Section

# Words a title-case heading leaves lowercase unless they start it.
MINOR = {
    "a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "nor",
    "of", "on", "or", "per", "the", "to", "via", "vs", "with",
}

NUMBER_PREFIX = re.compile(r"^\s*(\d+(?:\.\d+)*)\.?\s+")
WORD = re.compile(r"[A-Za-z][A-Za-z'’\-]*")

# Below this many headings, a "majority" is noise.
MINIMUM_HEADINGS = 4


def _style_of(title: str) -> Optional[str]:
    """``"title"``, ``"sentence"``, ``"upper"`` -- or ``None`` if unreadable."""
    body = NUMBER_PREFIX.sub("", title).strip()
    found = WORD.findall(body)
    if len(found) < 2:
        return None
    letters = [c for c in body if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return "upper"
    significant = [w for w in found[1:] if w.lower() not in MINOR]
    if not significant:
        return None
    capitalised = sum(1 for w in significant if w[:1].isupper())
    if capitalised == len(significant):
        return "title"
    if capitalised == 0:
        return "sentence"
    return None


def _to_title(title: str) -> str:
    def convert(match: "re.Match[str]") -> str:
        word = match.group(0)
        if word.isupper() and len(word) > 1:
            return word          # an acronym stays an acronym
        return word[:1].upper() + word[1:]

    prefix = NUMBER_PREFIX.match(title)
    head = prefix.group(0) if prefix else ""
    body = title[len(head):]
    parts = list(WORD.finditer(body))
    result = body
    for match in reversed(parts):
        word = match.group(0)
        first = match is parts[0]
        last = match is parts[-1]
        if not first and not last and word.lower() in MINOR and not word.isupper():
            replacement = word.lower()
        else:
            replacement = convert(match)
        result = result[: match.start()] + replacement + result[match.end():]
    return head + result


def _to_sentence(title: str) -> str:
    prefix = NUMBER_PREFIX.match(title)
    head = prefix.group(0) if prefix else ""
    body = title[len(head):]
    parts = list(WORD.finditer(body))
    result = body
    for match in reversed(parts[1:]):
        word = match.group(0)
        if word.isupper() and len(word) > 1:
            continue             # an acronym stays an acronym
        result = result[: match.start()] + word.lower() + result[match.end():]
    return head + result


class JournalStylePlugin(SuggestionPlugin):
    name = "journal"
    title = "Journal style"
    description = (
        "Aligns headings with the capitalisation and punctuation this document "
        "already uses, and reports gaps in its section numbering."
    )
    enabled_by_default = True

    def run(self, context: Context) -> None:
        sections = [
            section
            for section in context.body_sections()
            if section.heading_block is not None and section.title.strip()
        ]
        if not sections:
            return

        self._trailing_punctuation(context, sections)
        self._capitalisation(context, sections)
        self._numbering(context, sections)

    # -- one right answer -------------------------------------------------

    @staticmethod
    def _trailing_punctuation(context: Context, sections: List[Section]) -> None:
        headings = [s.heading_block.text() for s in sections]
        with_period = sum(1 for h in headings if h.rstrip().endswith("."))
        # Only when the document clearly does not do this.
        if with_period == 0 or with_period > len(headings) / 2:
            return
        for section in sections:
            text = section.heading_block.text()
            stripped = text.rstrip()
            if not stripped.endswith(".") or NUMBER_PREFIX.fullmatch(stripped):
                continue
            context.propose(
                section,
                stripped[:-1].rstrip(),
                "this heading ends with a period and the document's other "
                "headings do not",
                confidence=0.8,
            )

    # -- majority rules ---------------------------------------------------

    @staticmethod
    def _capitalisation(context: Context, sections: List[Section]) -> None:
        if len(sections) < MINIMUM_HEADINGS:
            return
        styles = {}
        for section in sections:
            style = _style_of(section.title)
            if style:
                styles[id(section)] = style
        counts = Counter(styles.values())
        if not counts:
            return
        ordered = counts.most_common()
        if ordered[0][0] == "upper":
            return          # an all-caps house style is a house style
        if len(ordered) > 1 and ordered[0][1] == ordered[1][1]:
            return          # a tie is not a convention
        if ordered[0][1] < 3 or ordered[0][1] <= sum(counts.values()) / 2:
            return

        winner = ordered[0][0]
        convert = _to_title if winner == "title" else _to_sentence
        label = "title case" if winner == "title" else "sentence case"
        for section in sections:
            style = styles.get(id(section))
            if style is None or style == winner:
                continue
            heading = section.heading_block.text()
            fixed = convert(heading)
            if fixed == heading:
                continue
            context.propose(
                section,
                fixed,
                f"most headings in this document use {label}",
                # Capitalisation of a heading is conventional, not correct, so
                # this stays well below the mechanical rules.
                confidence=0.65,
            )

    # -- nothing to replace -----------------------------------------------

    @staticmethod
    def _numbering(context: Context, sections: List[Section]) -> None:
        numbered: List[Tuple[str, Section]] = []
        for section in sections:
            match = NUMBER_PREFIX.match(section.heading_block.text())
            if match:
                numbered.append((match.group(1), section))
        if len(numbered) < 3:
            return

        top: List[int] = []
        for number, _ in numbered:
            if "." not in number:
                top.append(int(number))
        seen = set()
        for index, value in enumerate(top):
            if value in seen:
                context.note(
                    f"section number {value} is used more than once",
                    severity="warning",
                )
            seen.add(value)
            if index and value not in (top[index - 1], top[index - 1] + 1):
                context.note(
                    f"section numbering jumps from {top[index - 1]} to {value}",
                    severity="warning",
                )


__all__ = ["JournalStylePlugin"]
