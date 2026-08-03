"""Keywords: separators, duplicates, count and trailing punctuation.

The keyword line is the one piece of front matter where the defects are almost
always mechanical -- a trailing semicolon, the same term twice, a mixture of
commas and semicolons in one list -- so most of what this plugin finds is
proposable rather than advisory.

The separator is not chosen by this file.  Whichever of ``,`` and ``;`` the line
uses more is treated as its separator and the other occurrences are converted,
so a Springer paper using semicolons is normalised to semicolons and an IEEE
paper using commas to commas.  A line whose separator is genuinely ambiguous --
equal counts -- is left alone.

Capitalisation is left alone entirely: sentence case, title case and all-lower
keyword lists are all common, and there is only one such line per document, so
there is nothing to infer a convention from.
"""

from __future__ import annotations

import re
from typing import List, Optional

from document_engine.assist.plugin import Context, SuggestionPlugin

FEW = 3
MANY = 8

LABEL = re.compile(r"^\s*(key\s*words?|index\s+terms?)\s*[:.\-–—]?\s*", re.IGNORECASE)
SEPARATORS = (",", ";")


def _separator(body: str) -> Optional[str]:
    counts = {sep: body.count(sep) for sep in SEPARATORS}
    if not any(counts.values()):
        return None
    ordered = sorted(counts.items(), key=lambda item: -item[1])
    if ordered[0][1] == ordered[1][1]:
        return None
    return ordered[0][0]


class KeywordPlugin(SuggestionPlugin):
    name = "keywords"
    title = "Keyword suggestions"
    description = (
        "Normalises the keyword list's separators and spacing, removes "
        "duplicates, and reports an unusual number of keywords."
    )
    enabled_by_default = True

    def run(self, context: Context) -> None:
        node = context.document.metadata.keywords_node
        keywords = context.document.metadata.keywords

        if node is None:
            if not keywords:
                context.note(
                    "no keywords were found in this document; most venues "
                    "require them",
                )
            return

        original = node.text
        label = LABEL.match(original)
        head = label.group(0) if label else ""
        body = original[len(head):]

        separator = _separator(body)
        if separator is None:
            self._counts(context, keywords or [body], node)
            return

        other = ";" if separator == "," else ","
        parts = [
            part.strip()
            for part in re.split(r"[,;]", body)
        ]
        parts = [part for part in parts if part]

        seen = set()
        unique: List[str] = []
        duplicates: List[str] = []
        for part in parts:
            key = part.lower()
            if key in seen:
                duplicates.append(part)
                continue
            seen.add(key)
            unique.append(part)

        rebuilt = head + f"{separator} ".join(unique)
        reasons: List[str] = []
        if duplicates:
            reasons.append("duplicate keyword(s): " + ", ".join(sorted(set(duplicates))))
        if other in body:
            reasons.append(f"the list mixes '{separator}' and '{other}'")
        if rebuilt != original and not reasons:
            reasons.append("the separators are spaced inconsistently")

        if rebuilt != original and rebuilt.strip():
            context.propose(
                node,
                rebuilt,
                "; ".join(reasons),
                confidence=0.8,
            )

        self._counts(context, unique, node)

    @staticmethod
    def _counts(context: Context, keywords, node) -> None:
        count = len([k for k in keywords if str(k).strip()])
        if count and count < FEW:
            context.note(
                f"only {count} keyword(s); most venues ask for {FEW}-{MANY}",
                node=node,
            )
        elif count > MANY:
            context.note(
                f"{count} keywords; most venues allow at most {MANY}",
                node=node,
            )


__all__ = ["KeywordPlugin"]
