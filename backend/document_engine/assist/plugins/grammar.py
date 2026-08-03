"""Mechanical text defects: the ones with exactly one right answer.

This plugin only proposes fixes where the correction is not a matter of taste.
A double space between words is not a style choice; a repeated "the the" is not
an authorial decision.  Anything that requires judgement about the author's
meaning belongs in :mod:`document_engine.assist.plugins.academic`, which is off
by default for that reason, or in a future model-backed plugin.

Two deliberate omissions are worth recording, because both look like bugs.

**A period followed immediately by a letter is not touched.**  "e.g.Smith" is a
missing space, but so is every abbreviation, initial, decimal, filename, URL and
species name in a research paper, and the rule cannot tell them apart from text
alone.  Only ``,`` and ``;`` are corrected, where the ambiguity does not exist.

**Repeated words have an exception list.**  "had had", "that that" and "is is"
are grammatical English, and a plugin that flags them teaches the user to stop
reading its output.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from document_engine.assist.plugin import Context, SuggestionPlugin

# A word may legitimately follow itself.  Small on purpose: an exception list
# long enough to be safe is one long enough to hide real duplicates.
LEGITIMATE_REPEATS = {"had", "that", "is", "is,", "the", "very", "no"}

DOUBLE_SPACE = re.compile(r"[ \t]{2,}")
SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,;:.!?])")
MISSING_SPACE = re.compile(r"([,;])(?=[A-Za-z])")
REPEATED_WORD = re.compile(r"\b([A-Za-z]+)(\s+)(\1)\b", re.IGNORECASE)
SPACE_INSIDE_BRACKET = re.compile(r"\(\s+|\s+\)")


def _repeated(text: str) -> str:
    def replace(match: "re.Match[str]") -> str:
        word = match.group(1)
        if word.lower() in LEGITIMATE_REPEATS:
            return match.group(0)
        # "The the" at the start of a sentence still leaves the capital behind.
        return word
    return REPEATED_WORD.sub(replace, text)


def _brackets(text: str) -> str:
    text = re.sub(r"\(\s+", "(", text)
    return re.sub(r"\s+\)", ")", text)


# Ordered, because fixing a missing space can create a double space and the
# reverse is not true.
RULES: List[Tuple[str, object, str]] = [
    ("repeated word", _repeated, "a word is repeated"),
    ("missing space", lambda t: MISSING_SPACE.sub(r"\1 ", t), "a space is missing after punctuation"),
    ("space before punctuation", lambda t: SPACE_BEFORE_PUNCTUATION.sub(r"\1", t), "there is a space before punctuation"),
    ("bracket spacing", _brackets, "there is a space just inside a bracket"),
    ("double space", lambda t: DOUBLE_SPACE.sub(" ", t), "there is more than one space between words"),
]


class GrammarPlugin(SuggestionPlugin):
    name = "grammar"
    title = "Grammar and spacing"
    description = (
        "Mechanical defects with one correct answer: doubled spaces, spacing "
        "around punctuation, and repeated words."
    )
    enabled_by_default = True

    def run(self, context: Context) -> None:
        for node, text in context.prose_nodes():
            fixed = text
            reasons: List[str] = []
            for _, rule, reason in RULES:
                after = rule(fixed)
                if after != fixed:
                    reasons.append(reason)
                    fixed = after
            if fixed == text:
                continue
            context.propose(
                node,
                fixed,
                "; ".join(reasons),
                # Mechanical, checkable, and reversible: high but never 1.0,
                # because the user is the one accepting it.
                confidence=0.95,
            )


__all__ = ["GrammarPlugin"]
