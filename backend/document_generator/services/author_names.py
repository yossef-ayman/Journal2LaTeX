"""Telling author names apart from everything that sits next to them.

A paper's front matter is a dense block: names, superscript markers, departments,
universities, ministries, postal addresses, countries and email addresses, often
on adjacent lines and sometimes on the *same* line.  A Word analyzer working from
layout alone cannot always tell which line is which, so the raw author list it
produces frequently carries affiliations along with the names.  In a letter
addressed to the authors, that is not a cosmetic problem — it is the wrong text
in the most visible field on the page.

This module decides the question on the *shape* of the text, not on a list of
the values in any particular paper.  Two independent tests are applied:

* **Line level.** A line that contains an email address, a URL, a long digit run
  (a postal or box number), or any word from a generic institutional vocabulary
  is an affiliation *as a whole* and is discarded entirely.  Doing this before
  splitting is what stops ``"1 An educator Ministry of Education, Jordan"`` from
  contributing the perfectly name-shaped fragment ``"Jordan"``.
* **Name level.** What survives is split on the usual separators, and each
  candidate must look like a person's name: a small number of tokens, all
  alphabetic apart from initials, hyphens and apostrophes, with no digits and no
  English function words.

Both tests are deliberately generic.  Nothing here is derived from a particular
journal, paper or author, so a future submission from a different field, country
or template is judged by the same rules.  Name particles (``van``, ``de``,
``bin``, ``al``) are explicitly *not* treated as function words, and ALL-CAPS
names are as acceptable as title case, because both are ordinary in practice.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List, Tuple

# Separators between authors within one line.
_SPLIT_RE = re.compile(r"\s*(?:[,;،]|\band\b|&|/|\||•)\s*", re.IGNORECASE)

# Superscript affiliation markers, in either the digit or the Unicode form, plus
# the symbols journals use for corresponding-author and equal-contribution notes.
_MARKER_CHARS = "0123456789*†‡§¶#¹²³⁰⁴⁵⁶⁷⁸⁹"
_LEADING_MARKER_RE = re.compile(rf"^[{re.escape(_MARKER_CHARS)}\s.,;:()\[\]-]+")
_TRAILING_MARKER_RE = re.compile(rf"[{re.escape(_MARKER_CHARS)}\s.,;:()\[\]]+$")

# Academic and courtesy titles, stripped rather than rejected: "Dr. Aisha Karim"
# is a real author whose name is "Aisha Karim".
_TITLES = {
    "dr", "dr.", "prof", "prof.", "professor", "mr", "mr.", "mrs", "mrs.",
    "ms", "ms.", "miss", "eng", "eng.", "engineer", "assoc", "assoc.",
    "assist", "assist.", "asst", "asst.", "phd", "ph.d", "ph.d.", "md",
    "m.d.", "msc", "m.sc.", "bsc", "b.sc.",
}

# Words that never occur inside a person's name but are the substance of an
# affiliation, an address, a job description or a contact line.  This vocabulary
# is institutional, not journal-specific.
_AFFILIATION_WORDS = frozenset(
    """
    university universities univ college institute institut institution
    department dept departement faculty school academy academic ministry
    hospital clinic laboratory laboratories lab centre center research
    foundation society association corporation company corp ltd inc llc gmbh
    plc campus box street st road avenue ave boulevard blvd lane building
    floor suite city province district region county municipality village town
    postal zip code email mail e-mail phone telephone tel fax website www http
    https orcid corresponding correspondence author authors affiliation
    affiliations address addresses chair head division unit branch office
    bureau council commission
    agency authority program programme kingdom republic sultanate emirate
    state states national international federal public private group team
    center's college's science sciences engineering medicine education
    technology technologies management business arts humanities
    """.split()
)

# Occupations and roles.  These are held apart from the institutional words on
# purpose: a line describing what someone does ("An educator, Ministry of
# Education") is an affiliation, but the same words are ordinary surnames --
# Researcher, Teacher, Baker, Chandler -- so they may never on their own reject
# a candidate that otherwise has the shape of a person's name.
_OCCUPATION_WORDS = frozenset(
    """
    educator teacher lecturer researcher student scholar instructor
    professor practitioner consultant specialist coordinator supervisor
    """.split()
)

# English function words.  Their presence marks a phrase rather than a name;
# name particles such as van, de, der, bin, ibn, al and da are excluded on
# purpose, because they are part of the name.
_FUNCTION_WORDS = frozenset(
    {"of", "the", "for", "in", "at", "on", "with", "from", "a", "an", "to", "by"}
)

_EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+")
_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
_LONG_NUMBER_RE = re.compile(r"\d{3,}")

# Placeholders the analyzer records when a document declares no usable author.
_PLACEHOLDERS = frozenset(
    {"", "author name unspecified", "unknown", "n/a", "na", "anonymous", "-"}
)

_MAX_NAME_TOKENS = 6
_MAX_NAME_LENGTH = 60


def _normalise(text: str) -> str:
    """Collapse whitespace and unify the quote characters names are written with."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("’", "'").replace("ʼ", "'")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _words(text: str) -> List[str]:
    """Lowercased alphabetic words, with punctuation stripped."""
    return [w.strip(".,;:()[]'-").lower() for w in text.split() if w.strip(".,;:()[]'-")]


def is_affiliation_line(text: str) -> bool:
    """Whether a whole line is an affiliation, address or contact line.

    Judged before the line is split, because splitting an affiliation produces
    fragments that are individually indistinguishable from names -- a country, a
    city, a person's surname used as an institute's name.
    """
    line = _normalise(text)
    if not line:
        return True
    if _EMAIL_RE.search(line) or _URL_RE.search(line):
        return True
    if _LONG_NUMBER_RE.search(line):
        return True
    words = set(_words(line))
    if words & _AFFILIATION_WORDS:
        return True
    # "An educator ...", "The Department ..." -- a line opening with an article
    # is a description of something, never a person.
    first = _words(line)[:1]
    if first and first[0] in {"a", "an", "the"}:
        return True
    # A role word marks a line as a job description only when the line is not
    # itself shaped like a name: "Researcher, Faculty of Science" is one, and
    # "Ali Researcher" is a person whose surname happens to be that word.
    if words & _OCCUPATION_WORDS and not any(
        is_person_name(part) for part in _SPLIT_RE.split(line) if part.strip()
    ):
        return True
    return False


def strip_markers(text: str) -> str:
    """Remove superscript affiliation markers and courtesy titles from a name."""
    name = _normalise(text)
    name = _LEADING_MARKER_RE.sub("", name)
    name = _TRAILING_MARKER_RE.sub("", name)
    # Markers also appear glued between the given and family name in some
    # layouts ("J.1 Smith"); drop digits that follow a letter.
    name = re.sub(rf"(?<=[^\W\d_])[{re.escape(_MARKER_CHARS[9:])}\d]+", "", name)
    tokens = name.split()
    while tokens and tokens[0].lower().strip(".,") in _TITLES:
        tokens.pop(0)
    return " ".join(tokens).strip(" ,.;-")


def _is_name_token(token: str) -> bool:
    """Whether one token could be part of a person's name."""
    core = token.strip(".,;:()[]")
    if not core:
        return False
    if core.lower() in _FUNCTION_WORDS or core.lower() in _AFFILIATION_WORDS:
        return False
    # Letters, plus the punctuation names legitimately contain: initials'
    # full stops, hyphenated surnames, elided particles.
    return all(char.isalpha() or char in "'-." for char in core)


def is_person_name(text: str) -> bool:
    """Whether a cleaned candidate has the shape of a person's name."""
    name = strip_markers(text)
    if not name or name.lower() in _PLACEHOLDERS:
        return False
    if len(name) > _MAX_NAME_LENGTH:
        return False
    if any(char.isdigit() for char in name):
        return False
    tokens = name.split()
    if not 1 <= len(tokens) <= _MAX_NAME_TOKENS:
        return False
    if not all(_is_name_token(token) for token in tokens):
        return False
    # A single token has to be substantial: "A." or "Jr" is a fragment, not a name.
    letters = [char for char in name if char.isalpha()]
    if len(letters) < 2:
        return False
    if len(tokens) == 1 and len(letters) < 3:
        return False
    return True


def clean_authors(raw_names: Iterable[str]) -> Tuple[List[str], List[str]]:
    """Turn a raw extracted author list into names, and report what was dropped.

    Returns ``(names, discarded)``.  The discarded list is not cosmetic: it is
    what lets a batch warn an operator that a paper's front matter confused the
    parser, instead of quietly shortening the author list.
    """
    names: List[str] = []
    discarded: List[str] = []
    seen: set[str] = set()

    for raw in raw_names:
        for line in (_normalise(raw) or "").split("\n"):
            line = line.strip()
            if not line:
                continue
            if is_affiliation_line(line):
                discarded.append(line)
                continue
            for candidate in _SPLIT_RE.split(line):
                candidate = candidate.strip()
                if not candidate:
                    continue
                if not is_person_name(candidate):
                    if candidate.lower() not in _PLACEHOLDERS:
                        discarded.append(candidate)
                    continue
                name = strip_markers(candidate)
                key = name.casefold()
                if key in seen:
                    continue
                seen.add(key)
                names.append(name)

    return names, discarded


__all__ = [
    "clean_authors",
    "is_affiliation_line",
    "is_person_name",
    "strip_markers",
]
