"""The title: the four defects that are defects in every venue.

A trailing period, an all-caps title, doubled internal spaces and a
line-broken title are wrong (or at least unwanted) whether the paper is going to
IEEE or into a thesis, so all four are proposed as edits.  Length is a note,
because shortening a title means knowing what the paper is about.

Title *case* is not touched.  Journals disagree about it -- IEEE wants title
case, many Elsevier titles are sentence case -- and there is exactly one title
in a document, so unlike headings there is no majority to learn from.  Guessing
would be this plugin imposing a house style on the one line the author cared
most about.
"""

from __future__ import annotations

import re
from typing import List

from document_engine.assist.plugin import Context, SuggestionPlugin, words

LONG = 25
SHORT = 3

MINOR = {
    "a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "nor",
    "of", "on", "or", "per", "the", "to", "via", "with",
}
WORD = re.compile(r"[A-Za-z][A-Za-z'’\-]*")


def _from_upper(title: str) -> str:
    """All caps -> title case.  Only reached when the title is entirely caps,
    so nothing that was deliberately an acronym can be told apart -- short
    all-caps words are left alone as the safer error."""
    parts = list(WORD.finditer(title))
    result = title
    for index, match in reversed(list(enumerate(parts))):
        word = match.group(0)
        if len(word) <= 4 and index not in (0, len(parts) - 1):
            # Might be an acronym; might be "FROM".  Leaving it caps is visible
            # and easy for the user to fix, which the reverse is not.
            continue
        lower = word.lower()
        if index not in (0, len(parts) - 1) and lower in MINOR:
            replacement = lower
        else:
            replacement = lower[:1].upper() + lower[1:]
        result = result[: match.start()] + replacement + result[match.end():]
    return result


class TitlePlugin(SuggestionPlugin):
    name = "title"
    title = "Title suggestions"
    description = (
        "Removes a trailing period, collapses stray whitespace, and offers to "
        "convert an all-caps title.  Never changes title case otherwise."
    )
    enabled_by_default = True

    def run(self, context: Context) -> None:
        node = context.document.metadata.title
        if node is None:
            context.note(
                "no title was found in this document",
                severity="warning",
            )
            return

        original = node.text
        fixed = original
        reasons: List[str] = []

        collapsed = re.sub(r"\s{2,}", " ", fixed).strip()
        if collapsed != fixed:
            reasons.append("stray whitespace")
            fixed = collapsed

        if fixed.endswith(".") and not fixed.endswith(".."):
            fixed = fixed[:-1].rstrip()
            reasons.append("a title does not end with a period")

        letters = [c for c in fixed if c.isalpha()]
        if letters and all(c.isupper() for c in letters) and len(letters) > 12:
            converted = _from_upper(fixed)
            if converted != fixed:
                fixed = converted
                reasons.append("the title is set entirely in capitals")

        if fixed != original and reasons:
            context.propose(
                node,
                fixed,
                "; ".join(reasons),
                # The all-caps conversion is a judgement; the rest is not.  The
                # single confidence reflects the weakest rule that fired.
                confidence=0.6 if len(reasons) > 1 else 0.85,
            )

        count = len(words(original))
        if count > LONG:
            context.note(
                f"the title is {count} words; many venues ask for under {LONG}",
            )
        elif count and count < SHORT:
            context.note(
                f"the title is only {count} word(s), which may be too short to "
                "describe the work",
            )


__all__ = ["TitlePlugin"]
