"""Acronyms and terminology: defined once, used consistently.

The convention this plugin enforces is the one every venue shares: expand an
acronym at its first use, then use the acronym.  Everything it knows about which
acronyms exist, it learns from the document -- there is no list of terms here,
because a list would be a list of *some field's* terms and the engine has to
work on any field.

Two findings, again split by whether there is text to replace:

* a **redefinition** -- "Mobile Ad Hoc Network (MANET)" written out again three
  sections later -- is a suggestion, because the fix is to delete the repeated
  expansion and the remaining text is unambiguous;
* an **undefined acronym**, or one defined after its first use, is a note: the
  expansion is knowledge this plugin does not have.

Very short and very common capitalised strings are ignored.  "I", "A", "US" and
"DNA" would otherwise generate noise on every paper written.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from document_engine.assist.plugin import Context, SuggestionPlugin

# "Some Expanded Phrase (ACR)" -- the expansion immediately before the bracket.
DEFINITION = re.compile(
    r"((?:[A-Za-z][A-Za-z'’\-]*\s+){1,7}[A-Za-z][A-Za-z'’\-]*)\s*\(\s*([A-Z][A-Za-z]{1,9}s?)\s*\)"
)
ACRONYM = re.compile(r"\b([A-Z]{2,}(?:s|es)?)\b")

# Acronyms a reader is assumed to know, so flagging them is noise.
COMMON = {
    "I", "A", "AN", "THE", "AND", "OR", "IT", "IS", "US", "UK", "EU", "USA",
    "PDF", "HTML", "XML", "URL", "HTTP", "HTTPS", "API", "CPU", "GPU", "RAM",
    "PC", "TV", "DNA", "RNA", "PHD", "MSC", "BSC", "DOI", "ISBN", "ISSN",
    "AM", "PM", "AD", "BC", "OK", "ID", "IEEE", "ACM", "ISO", "IEC",
}


def _initials(phrase: str) -> str:
    return "".join(word[0].upper() for word in phrase.split() if word)


def _defines(phrase: str, acronym: str) -> bool:
    """Does this phrase plausibly expand this acronym?

    Requiring an exact initial match is too strict ("Mobile Ad-hoc NETwork"),
    and requiring nothing is too loose.  The rule used is: the acronym's letters
    appear as word initials, in order, within the phrase.
    """
    letters = [c for c in acronym.upper() if c.isalpha()]
    words = [w for w in phrase.split() if w]
    index = 0
    for word in words:
        if index < len(letters) and word[0].upper() == letters[index]:
            index += 1
    return index >= max(2, len(letters) - 1)


class TerminologyPlugin(SuggestionPlugin):
    name = "terminology"
    title = "Terminology consistency"
    description = (
        "Checks that acronyms are expanded once, at first use, and reports "
        "acronyms that are never defined."
    )
    enabled_by_default = True

    def run(self, context: Context) -> None:
        nodes = list(context.prose_nodes())

        # Pass one: where each acronym is defined, in document order.
        definitions: Dict[str, List[int]] = {}
        for order, (_, text) in enumerate(nodes):
            for match in DEFINITION.finditer(text):
                phrase, acronym = match.group(1), match.group(2)
                if not _defines(phrase, acronym):
                    continue
                definitions.setdefault(acronym.upper(), []).append(order)

        self._remove_redefinitions(context, nodes, definitions)
        self._report_undefined(context, nodes, definitions)

    # -- there is text to replace -----------------------------------------

    @staticmethod
    def _remove_redefinitions(context: Context, nodes, definitions) -> None:
        repeated = {a for a, where in definitions.items() if len(where) > 1}
        if not repeated:
            return
        for order, (node, text) in enumerate(nodes):
            fixed = text
            removed: List[str] = []

            def replace(match: "re.Match[str]") -> str:
                phrase, acronym = match.group(1), match.group(2)
                key = acronym.upper()
                if key not in repeated or not _defines(phrase, acronym):
                    return match.group(0)
                if definitions[key][0] == order:
                    return match.group(0)     # the first definition stays
                removed.append(acronym)
                # The expansion goes; the acronym stays and reads as a noun.
                return acronym

            fixed = DEFINITION.sub(replace, fixed)
            if fixed == text or not removed:
                continue
            fixed = re.sub(r"[ \t]{2,}", " ", fixed)
            context.propose(
                node,
                fixed,
                "already defined earlier: "
                + ", ".join(sorted(set(removed)))
                + " -- the expansion is repeated",
                confidence=0.75,
            )

    # -- there is not ------------------------------------------------------

    @staticmethod
    def _report_undefined(context: Context, nodes, definitions) -> None:
        first_use: Dict[str, int] = {}
        counts: Dict[str, int] = {}
        for order, (_, text) in enumerate(nodes):
            for match in ACRONYM.finditer(text):
                acronym = match.group(1).upper()
                if acronym in COMMON or len(acronym) < 3:
                    continue
                counts[acronym] = counts.get(acronym, 0) + 1
                first_use.setdefault(acronym, order)

        for acronym, order in sorted(first_use.items()):
            where = definitions.get(acronym)
            if where is None:
                if counts.get(acronym, 0) >= 2:
                    context.note(
                        f"{acronym} is used {counts[acronym]} times but never "
                        f"expanded",
                        severity="warning",
                    )
            elif where[0] > order:
                context.note(
                    f"{acronym} is used before it is defined",
                    severity="warning",
                )


__all__ = ["TerminologyPlugin"]
