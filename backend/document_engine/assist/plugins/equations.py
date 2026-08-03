"""Equations: numbering and the punctuation around them.

Almost everything this plugin finds is a note, and that is not a limitation --
it is the correct answer.  An equation's content is OMML, not text; the engine's
editing layer refuses to rewrite it precisely because "replace the text of an
equation" has no safe meaning.  So the plugin reports what it can see about the
*document's* handling of its equations and proposes nothing it cannot apply.

The one exception is the paragraph a display equation sits in when the equation
is numbered inconsistently in text form -- ``(1)`` versus ``(Eq. 1)`` -- which
is ordinary text in an ordinary paragraph and can be normalised like any other.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from document_engine.assist.plugin import Context, SuggestionPlugin

EQUATION_NUMBER = re.compile(r"\(\s*(?:Eq\.?|Equation)?\s*(\d+(?:\.\d+)?)\s*\)\s*$", re.IGNORECASE)
INLINE_REFERENCE = re.compile(r"\b(?:Eq\.?|Equation)\s*\(?\s*(\d+(?:\.\d+)?)\s*\)?", re.IGNORECASE)


class EquationPlugin(SuggestionPlugin):
    name = "equations"
    title = "Equation suggestions"
    description = (
        "Reports gaps, duplicates and unreferenced equation numbers.  Equation "
        "content itself is never rewritten."
    )
    enabled_by_default = True

    def run(self, context: Context) -> None:
        equations = context.document.equations
        if not equations:
            return

        numbered = [eq for eq in equations if eq.number]
        display = [eq for eq in equations if eq.display]

        if display and not numbered:
            context.note(
                f"none of this document's {len(display)} display equations are "
                "numbered; most journals require numbering for any equation "
                "referred to in the text",
            )

        self._check_sequence(context, numbered)
        self._check_references(context, numbered)

    @staticmethod
    def _check_sequence(context: Context, numbered) -> None:
        seen: Dict[str, int] = {}
        previous: Optional[int] = None
        for equation in numbered:
            raw = str(equation.number).strip()
            seen[raw] = seen.get(raw, 0) + 1
            if seen[raw] == 2:
                context.note(
                    f"equation number ({raw}) is used more than once",
                    node=equation,
                    severity="warning",
                )
            if "." in raw or not raw.isdigit():
                continue
            value = int(raw)
            if previous is not None and value not in (previous, previous + 1):
                context.note(
                    f"equation numbering jumps from ({previous}) to ({value})",
                    node=equation,
                    severity="warning",
                )
            previous = value

    @staticmethod
    def _check_references(context: Context, numbered) -> None:
        if not numbered:
            return
        referenced = set()
        for _, text in context.prose_nodes():
            for match in INLINE_REFERENCE.finditer(text):
                referenced.add(match.group(1))
        unreferenced = [
            str(eq.number).strip()
            for eq in numbered
            if str(eq.number).strip() not in referenced
        ]
        if unreferenced and len(unreferenced) < len(numbered):
            # All of them unreferenced usually means the document refers to
            # equations in a way this plugin cannot see, not that every equation
            # is orphaned.  Reporting that would be reporting the plugin's own
            # blind spot as the author's mistake.
            context.note(
                "these numbered equations are never referred to in the text: "
                + ", ".join(f"({n})" for n in unreferenced[:12]),
            )


__all__ = ["EquationPlugin"]
