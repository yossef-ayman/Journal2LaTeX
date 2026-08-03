"""What changed, at word granularity, deterministically.

Two jobs, and they are the same computation used twice.

**For the user.**  The UI shows Original / Suggested / Accept / Reject, and a
whole-paragraph before-and-after is unreadable when one comma moved.  So the
diff is reported as a list of hunks -- equal, deleted, inserted -- that a UI can
render inline with strikethrough and underline.

**For the writer.**  Replacing a paragraph's entire text would work and would be
wrong: every run boundary inside it would collapse into the first run's
formatting, so correcting a typo in a sentence would flatten the italics three
words later.  :func:`changed_span` narrows an edit to the smallest character
range that actually differs, so the splice touches that range and leaves every
other run in the paragraph byte-for-byte alone.

``difflib.SequenceMatcher`` is used with autojunk disabled.  The heuristic it
disables discards elements that appear in more than 1% of a long sequence, which
on a paragraph of ordinary English means common words stop matching and the diff
silently degrades into "replace everything".  Off, the result is deterministic
and depends only on the two strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

# Words, runs of whitespace, and single punctuation marks are each one token, so
# a hunk lands on a word boundary rather than mid-word.
_TOKEN = re.compile(r"\w+|\s+|[^\w\s]", re.UNICODE)


@dataclass
class Hunk:
    """One stretch of the comparison."""

    kind: str   # "equal" | "delete" | "insert"
    text: str

    def as_dict(self) -> dict:
        return {"kind": self.kind, "text": self.text}


def tokenize(text: str) -> List[str]:
    return _TOKEN.findall(text or "")


def diff_words(original: str, suggested: str) -> List[Hunk]:
    """Word-level hunks turning ``original`` into ``suggested``."""
    left, right = tokenize(original), tokenize(suggested)
    matcher = SequenceMatcher(a=left, b=right, autojunk=False)
    hunks: List[Hunk] = []

    def push(kind: str, text: str) -> None:
        if not text:
            return
        if hunks and hunks[-1].kind == kind:
            hunks[-1].text += text
            return
        hunks.append(Hunk(kind, text))

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("equal",):
            push("equal", "".join(left[i1:i2]))
        else:
            if tag in ("delete", "replace"):
                push("delete", "".join(left[i1:i2]))
            if tag in ("insert", "replace"):
                push("insert", "".join(right[j1:j2]))
    return hunks


def changed_span(original: str, suggested: str) -> Optional[Tuple[int, int, str]]:
    """The smallest ``(start, end, replacement)`` that turns one into the other.

    Character offsets into ``original``.  ``None`` when the two are identical.

    Computed by trimming the common prefix and suffix rather than by walking the
    opcodes: the result is the same, and a single contiguous span is what
    :func:`document_engine.ooxml.bytes.rewrite_spans` can apply while leaving the
    runs on either side of it untouched.  Trimming is done on whole characters
    but clipped back to a token boundary where one is nearby, so an edit does not
    split a word across two runs.
    """
    if original == suggested:
        return None

    limit = min(len(original), len(suggested))
    prefix = 0
    while prefix < limit and original[prefix] == suggested[prefix]:
        prefix += 1

    suffix = 0
    while (
        suffix < limit - prefix
        and original[len(original) - 1 - suffix] == suggested[len(suggested) - 1 - suffix]
    ):
        suffix += 1

    start = prefix
    end = len(original) - suffix
    replacement = suggested[prefix : len(suggested) - suffix]
    return start, end, replacement


def summarize(original: str, suggested: str) -> dict:
    """A compact description of one edit, for the preview payload."""
    hunks = diff_words(original, suggested)
    return {
        "hunks": [hunk.as_dict() for hunk in hunks],
        "words_removed": sum(
            len(tokenize(h.text)) for h in hunks if h.kind == "delete"
        ),
        "words_added": sum(
            len(tokenize(h.text)) for h in hunks if h.kind == "insert"
        ),
        "characters_changed": abs(len(suggested) - len(original)) or sum(
            len(h.text) for h in hunks if h.kind != "equal"
        ),
    }


__all__ = ["Hunk", "changed_span", "diff_words", "summarize", "tokenize"]
