"""Internal consistency, decided by the document rather than by this file.

No dictionary of correct spellings appears here, and that is the design.  A
paper that writes "organisation" throughout is not wrong; a paper that writes it
both ways is inconsistent, and inconsistency is the only thing this plugin
claims to detect.  The majority form *in this document* wins, which is what
makes the rule work identically on a British thesis and an American journal
submission without knowing which it is holding.

Three families are covered, all detected by normalising a word to a key and
seeing whether one key attracted more than one spelling:

* ``-ise``/``-ize`` and ``-isation``/``-ization``;
* ``-our``/``-or`` (behaviour / behavior);
* hyphenation of the same compound ("multi-agent" / "multiagent").

A tie proposes nothing.  With no majority there is no evidence for a direction,
and picking one anyway would be the plugin imposing a house style it was never
told.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from document_engine.assist.plugin import Context, SuggestionPlugin, words

WORD_IN_TEXT = re.compile(r"[A-Za-z][A-Za-z'’-]*")

# Minimum occurrences before a majority means anything.  Two against one is a
# pattern; one against one is a coin toss.
MINIMUM_TOTAL = 2


def _spelling_key(word: str) -> Optional[str]:
    """A key shared by the variants of one word, or ``None`` if it has none."""
    lower = word.lower()
    key = lower
    if lower.endswith(("ise", "ize", "ised", "ized", "ises", "izes", "ising", "izing")):
        key = re.sub(r"i([sz])(e|ed|es|ing)$", r"iZ\2", lower)
    elif lower.endswith(("isation", "ization", "isations", "izations")):
        key = re.sub(r"i([sz])ation", "iZation", lower)
    elif lower.endswith(("our", "ours", "oural")):
        key = re.sub(r"our", "oR", lower)
    elif lower.endswith(("or", "ors", "oral")) and len(lower) > 4:
        key = re.sub(r"or", "oR", lower)
    else:
        return None
    return key


def _majority(counts: Dict[str, int]) -> Optional[str]:
    """The single most common form, or ``None`` if there is a tie."""
    if len(counts) < 2 or sum(counts.values()) < MINIMUM_TOTAL:
        return None
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    if ordered[0][1] == ordered[1][1]:
        return None
    return ordered[0][0]


def _match_case(source: str, target: str) -> str:
    if source[:1].isupper():
        return target[:1].upper() + target[1:]
    return target


class ConsistencyPlugin(SuggestionPlugin):
    name = "consistency"
    title = "Consistency checking"
    description = (
        "Finds words this document spells or hyphenates more than one way, and "
        "proposes the form the document itself uses most."
    )
    enabled_by_default = True

    def run(self, context: Context) -> None:
        nodes = list(context.prose_nodes())

        counted: Dict[str, int] = defaultdict(int)
        for _, text in nodes:
            for word in words(text):
                counted[word.lower()] += 1

        spellings: Dict[str, Dict[str, int]] = defaultdict(dict)
        hyphens: Dict[str, Dict[str, int]] = defaultdict(dict)
        for word, count in counted.items():
            key = _spelling_key(word)
            if key:
                spellings[key][word] = count
            # A hyphenated compound and its unhyphenated form share a key, so a
            # document using both puts two entries under one key and the
            # majority rule below decides between them.  A compound written only
            # one way lands alone under its key and is never proposed against.
            hyphens[word.replace("-", "")][word] = count

        winners: Dict[str, str] = {}
        for table in (spellings, hyphens):
            for key, counts in table.items():
                winner = _majority(counts)
                if winner is None:
                    continue
                for variant in counts:
                    if variant != winner:
                        winners[variant] = winner

        if not winners:
            return

        for node, text in nodes:
            fixed = text
            changed: List[Tuple[str, str]] = []

            def replace(match: "re.Match[str]") -> str:
                found = match.group(0)
                target = winners.get(found.lower())
                if target is None:
                    return found
                changed.append((found, target))
                return _match_case(found, target)

            fixed = WORD_IN_TEXT.sub(replace, fixed)
            if fixed == text or not changed:
                continue
            detail = ", ".join(
                sorted({f"{found} -> {target}" for found, target in changed})
            )
            context.propose(
                node,
                fixed,
                f"this document mostly writes it the other way ({detail})",
                # Evidence-based but not certain: two spellings can both be
                # intentional when one of them is a quoted title.
                confidence=0.7,
            )


__all__ = ["ConsistencyPlugin"]
