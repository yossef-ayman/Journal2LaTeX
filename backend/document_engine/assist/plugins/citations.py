"""Citation consistency: how citations are punctuated, and whether they resolve.

Two different kinds of finding live here, and they are deliberately reported
differently.

**Spacing and separators are suggestions**, because there is text to replace:
``result[3]`` wants a space, ``[1],[2]`` wants ``[1, 2]``, ``[ 4 ]`` wants
``[4]``.  These are mechanical and reversible.

**An uncited or duplicated reference is a note**, because there is nothing to
replace.  The fix for "reference 12 is never cited" is a sentence only the
author can write, and a plugin that invented one would be inventing a claim
about the literature.  Notes are the honest shape for a finding whose remedy is
not an edit.

The citation style is not assumed.  Numeric brackets and author-year parentheses
are both recognised, and the *document's own* majority decides which one is
treated as its style, so an Elsevier numeric paper and an APA thesis both get
sensible answers without the plugin knowing which it holds.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

from document_engine.assist.plugin import Context, SuggestionPlugin

NUMERIC_CITATION = re.compile(r"\[\s*(\d+(?:\s*[-–,]\s*\d+)*)\s*\]")
AUTHOR_YEAR = re.compile(r"\(\s*[A-Z][A-Za-z'’\-]+(?:\s+(?:et\s+al\.?|and|&)\s*[A-Za-z'’\-]*)?,?\s*\d{4}[a-z]?\s*\)")

GLUED_BRACKET = re.compile(r"(?<=[A-Za-z0-9])(\[\d)")
PADDED_BRACKET = re.compile(r"\[\s+(\d[^\]]*?)\s*\]|\[\s*(\d[^\]]*?)\s+\]")
ADJACENT_BRACKETS = re.compile(r"\]\s*,?\s*\[")
SPACE_BEFORE_BRACKET_PUNCTUATION = re.compile(r"\]\s+([,.;:])")


def _numbers(text: str) -> Set[int]:
    """Every reference number a numeric citation names, ranges expanded."""
    found: Set[int] = set()
    for match in NUMERIC_CITATION.finditer(text):
        body = match.group(1)
        for part in re.split(r"\s*,\s*", body):
            span = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", part)
            if span:
                first, last = int(span.group(1)), int(span.group(2))
                if 0 < first <= last <= first + 200:
                    found.update(range(first, last + 1))
            elif part.strip().isdigit():
                found.add(int(part))
    return found


def _normalize(text: str) -> str:
    fixed = PADDED_BRACKET.sub(lambda m: "[" + (m.group(1) or m.group(2)) + "]", text)
    fixed = GLUED_BRACKET.sub(r" \1", fixed)
    fixed = ADJACENT_BRACKETS.sub(", ", fixed)
    fixed = SPACE_BEFORE_BRACKET_PUNCTUATION.sub(r"]\1", fixed)
    return fixed


class CitationPlugin(SuggestionPlugin):
    name = "citations"
    title = "Citation consistency"
    description = (
        "Normalises citation spacing and separators, and reports references "
        "that are never cited or cited but missing."
    )
    enabled_by_default = True

    def run(self, context: Context) -> None:
        nodes = list(context.prose_nodes())

        numeric = sum(len(NUMERIC_CITATION.findall(text)) for _, text in nodes)
        author_year = sum(len(AUTHOR_YEAR.findall(text)) for _, text in nodes)

        if numeric:
            self._normalise_brackets(context, nodes)
        if numeric and author_year and min(numeric, author_year) > 1:
            context.note(
                f"this document mixes two citation styles: {numeric} numeric "
                f"citations and {author_year} author-year citations",
                severity="warning",
            )

        self._check_coverage(context, nodes, numeric)

    # -- the part with text to replace ------------------------------------

    @staticmethod
    def _normalise_brackets(context: Context, nodes) -> None:
        for node, text in nodes:
            fixed = _normalize(text)
            if fixed != text:
                context.propose(
                    node,
                    fixed,
                    "citation brackets are spaced or separated inconsistently",
                    confidence=0.85,
                )

    # -- the part with nothing to replace ---------------------------------

    @staticmethod
    def _check_coverage(context: Context, nodes, numeric: int) -> None:
        references = context.document.references
        if not references:
            if numeric:
                context.note(
                    "this document cites sources but no reference list was "
                    "found",
                    severity="warning",
                )
            return

        cited: Set[int] = set()
        for _, text in nodes:
            cited |= _numbers(text)
        if not cited:
            # Author-year, or citations this plugin cannot see.  Saying nothing
            # is better than reporting every reference as uncited.
            return

        total = len(references)
        uncited = [n for n in range(1, total + 1) if n not in cited]
        missing = sorted(n for n in cited if n > total)

        if uncited:
            listed = ", ".join(str(n) for n in uncited[:12])
            more = "" if len(uncited) <= 12 else f" (and {len(uncited) - 12} more)"
            context.note(
                f"{len(uncited)} of {total} references are never cited in the "
                f"text: {listed}{more}",
                severity="warning",
            )
        if missing:
            context.note(
                "the text cites "
                + ", ".join(f"[{n}]" for n in missing)
                + f", but the reference list has only {total} entries",
                severity="warning",
            )

        seen: Dict[str, int] = {}
        duplicates: List[str] = []
        for reference in references:
            key = re.sub(r"\W+", " ", reference.text.lower()).strip()
            if not key:
                continue
            if key in seen:
                duplicates.append(reference.text[:60])
            seen[key] = seen.get(key, 0) + 1
        for text in duplicates:
            context.note(
                f"this reference appears more than once: {text}...",
                severity="warning",
            )


__all__ = ["CitationPlugin"]
