"""Academic register: wordiness and informality, proposed but never assumed.

Every rule here changes an author's sentence, which is why the plugin is **off
by default**.  A tool that silently tightens somebody's prose the moment they
upload a manuscript is not an assistant.

The substitutions are the uncontroversial subset of the register advice every
style guide agrees on: expand contractions, drop empty intensifiers, replace a
multi-word connective with the single word it means.  Nothing here is specific
to a journal, a field or a document -- the table would apply equally to a thesis
or a report, which is the test a rule has to pass to be in it.

Case is preserved at a sentence start rather than lowercased, and word
boundaries are required on both sides, so "into" is not found inside
"pointing".
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from document_engine.assist.plugin import Context, SuggestionPlugin

# phrase -> replacement.  Longest first at match time so "in order to" wins over
# "in order".
WORDINESS: Dict[str, str] = {
    "in order to": "to",
    "in order for": "for",
    "due to the fact that": "because",
    "owing to the fact that": "because",
    "in spite of the fact that": "although",
    "despite the fact that": "although",
    "for the purpose of": "for",
    "in the event that": "if",
    "at this point in time": "now",
    "a large number of": "many",
    "a small number of": "a few",
    "the majority of": "most",
    "is able to": "can",
    "are able to": "can",
    "has the ability to": "can",
    "it is important to note that": "notably,",
    "in this paper we": "we",
    "as a matter of fact": "in fact",
    "in the near future": "soon",
    "with regard to": "regarding",
    "in terms of": "for",
    "utilize": "use",
    "utilizes": "uses",
    "utilized": "used",
    "utilizing": "using",
    "very important": "critical",
    "very large": "large",
    "very small": "small",
    "really": "",
    "basically": "",
    "actually": "",
}

CONTRACTIONS: Dict[str, str] = {
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "can't": "cannot",
    "won't": "will not",
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "hasn't": "has not",
    "haven't": "have not",
    "it's": "it is",
    "we've": "we have",
    "we'll": "we will",
    "we're": "we are",
    "that's": "that is",
    "there's": "there is",
}


def _compile(table: Dict[str, str]) -> List[Tuple["re.Pattern[str]", str, str]]:
    rules = []
    for phrase in sorted(table, key=len, reverse=True):
        pattern = re.compile(
            r"\b" + re.escape(phrase).replace(r"\ ", r"\s+").replace("'", "['’]") + r"\b",
            re.IGNORECASE,
        )
        rules.append((pattern, table[phrase], phrase))
    return rules


RULES = _compile(WORDINESS) + _compile(CONTRACTIONS)


def _match_case(source: str, replacement: str) -> str:
    """Keep a sentence-initial capital when the phrase had one."""
    if not replacement or not source:
        return replacement
    if source[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement


def _tidy(text: str) -> str:
    """Deleting a word ("really") leaves the spaces it sat between."""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return text


class AcademicPlugin(SuggestionPlugin):
    name = "academic"
    title = "Academic rewriting"
    description = (
        "Tightens wordy connectives and expands contractions.  Changes the "
        "author's words, so it is off unless asked for."
    )
    enabled_by_default = False

    def run(self, context: Context) -> None:
        for node, text in context.prose_nodes():
            fixed = text
            found: List[str] = []
            for pattern, replacement, phrase in RULES:
                def substitute(match: "re.Match[str]") -> str:
                    return _match_case(match.group(0), replacement)

                after = pattern.sub(substitute, fixed)
                if after != fixed:
                    found.append(phrase)
                    fixed = after
            fixed = _tidy(fixed)
            if fixed == text or not fixed.strip():
                continue
            context.propose(
                node,
                fixed,
                "wordy or informal phrasing: " + ", ".join(sorted(set(found))),
                # Lower than grammar: these are defensible as written, and a
                # confidence of 0.6 is the plugin saying "read this one".
                confidence=0.6,
            )


__all__ = ["AcademicPlugin"]
