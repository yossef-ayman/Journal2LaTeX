"""The abstract, judged only on the things that are true of every venue.

Word limits differ by journal, so the bounds here are wide enough that hitting
one means something regardless of venue: an abstract of forty words is short
anywhere, and one of four hundred is long anywhere.  Both are notes rather than
suggestions -- lengthening an abstract requires knowing what the paper found.

What the plugin *does* propose is the same class of mechanical fix the grammar
plugin makes, applied where it matters most: the abstract is the part of the
manuscript an editor reads first.  Undefined acronyms and citations inside the
abstract are reported, because most venues ask for an abstract that stands
alone, and neither has an automatic fix.
"""

from __future__ import annotations

import re
from typing import List, Optional

from document_engine.assist.plugin import Context, SuggestionPlugin, words

SHORT = 60
LONG = 350

CITATION = re.compile(r"\[\s*\d+[^\]]*\]|\(\s*[A-Z][A-Za-z'’\-]+[^)]{0,30}\d{4}[a-z]?\s*\)")
ACRONYM = re.compile(r"\b([A-Z]{3,})\b")
DEFINED_HERE = re.compile(r"\(\s*([A-Z]{2,}s?)\s*\)")
LABEL = re.compile(r"^\s*abstract\s*[:.\-–—]?\s*", re.IGNORECASE)


class AbstractPlugin(SuggestionPlugin):
    name = "abstract"
    title = "Abstract improvements"
    description = (
        "Checks the abstract's length, and reports citations and undefined "
        "acronyms in it."
    )
    enabled_by_default = True

    def run(self, context: Context) -> None:
        abstract = context.document.metadata.abstract
        if abstract is None:
            context.note(
                "no abstract was found in this document",
                severity="warning",
            )
            return

        nodes = [
            (block.item, block.item.text)
            for block in abstract.content
            if block.kind in ("paragraph", "list_item")
            and getattr(block.item, "text", "").strip()
        ]
        if not nodes:
            return

        text = " ".join(value for _, value in nodes)
        self._length(context, text)
        self._citations(context, nodes)
        self._acronyms(context, text)
        self._leading_label(context, nodes)

    # -- notes -------------------------------------------------------------

    @staticmethod
    def _length(context: Context, text: str) -> None:
        count = len(words(text))
        if count < SHORT:
            context.note(
                f"the abstract is {count} words, which is short for most "
                f"venues (typically {SHORT}-250)",
            )
        elif count > LONG:
            context.note(
                f"the abstract is {count} words, which exceeds the limit of "
                f"most venues (typically 250-300)",
                severity="warning",
            )

    @staticmethod
    def _citations(context: Context, nodes) -> None:
        for node, value in nodes:
            found = CITATION.findall(value)
            if found:
                context.note(
                    f"the abstract contains {len(found)} citation(s); most "
                    "venues ask for an abstract that stands alone",
                    node=node,
                )
                return

    @staticmethod
    def _acronyms(context: Context, text: str) -> None:
        defined = {match.group(1).upper() for match in DEFINED_HERE.finditer(text)}
        undefined = sorted(
            {
                match.group(1)
                for match in ACRONYM.finditer(text)
                if match.group(1).upper() not in defined
            }
        )
        if undefined:
            context.note(
                "these acronyms are used in the abstract without being "
                "expanded there: " + ", ".join(undefined[:10]),
            )

    # -- one thing there is text to fix ------------------------------------

    @staticmethod
    def _leading_label(context: Context, nodes) -> None:
        """"Abstract: We show that..." -- the word is the heading, not the text.

        Only proposed when the abstract already has its own heading paragraph,
        so removing the inline label does not lose it.
        """
        if context.document.metadata.abstract.heading_block is None:
            return
        node, value = nodes[0]
        stripped = LABEL.sub("", value)
        if stripped == value or not stripped.strip():
            return
        context.propose(
            node,
            stripped,
            "the abstract already has a heading, so the repeated label can go",
            confidence=0.7,
        )


__all__ = ["AbstractPlugin"]
