"""The Citation Engine: find every citation, understand it, then render it.

A Word manuscript records citations as text.  Whatever the author did -- typed
``[3]``, inserted a field that renders as ``(Roe, 2021)``, applied superscript
character formatting to a ``2``, or linked to a bookmark in the reference list
-- what survives conversion is characters in a paragraph.  So the engine's job
splits into three questions that must be kept apart, because conflating them is
what makes citation handling fragile:

* **What is here?**  Detection, over the text, producing spans.  No decision is
  taken at this stage; a span that turns out to resolve to nothing is still
  recorded, because "this looks like a citation and matches no reference" is
  precisely the defect worth reporting.
* **Is it sound?**  Validation, against the reference list: does every citation
  resolve, is any reference cited twice under different numbers, is any
  reference never cited, is the numbering a contiguous sequence introduced in
  order.  None of this depends on the target journal.
* **How should it look?**  Rendering, which is the *only* stage that consults
  :class:`JournalRules`.  The engine never writes ``\\cite`` because it decided
  to; it writes whatever command the rules name.

Keeping the three apart is what makes the engine reusable.  A new journal
changes the third stage only, by declaring different rules; a new Word citation
convention changes the first only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.engines.journal_rules import JournalRules


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #

#: The shapes a citation takes in a converted Word document.
#:
#: ``bracket_numeric``   [3], [1,3], [2-6], and mixtures of the three
#: ``paren_numeric``     (3), (1,3) -- the same thing in round brackets
#: ``superscript``       a raised number, which conversion leaves as
#:                       ``\textsuperscript{3}`` or ``$^{3}$``
#: ``paren_author_year`` (Roe, 2021), (Roe et al., 2021; Doe, 2019)
#: ``narrative``         Roe (2021) -- the author is part of the sentence
#: ``hyperlink``         a link whose visible text is one of the above, which is
#:                       what Word's cross-reference-to-bibliography produces
#: ``command``           an already-rendered ``\\cite{...}``, seen when the
#:                       engine runs over LaTeX rather than over converted text
CITATION_FORMS = ("bracket_numeric", "paren_numeric", "superscript",
                  "paren_author_year", "narrative", "hyperlink", "command")


@dataclass
class BibEntry:
    """One entry in the reference list."""

    index: int                    # position, 0-based
    raw: str                      # the reference line as the document has it
    key: str                      # generated citation key
    number: Optional[int] = None  # the number the document itself printed
    authors: Tuple[str, ...] = ()
    year: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"index": self.index, "key": self.key, "number": self.number,
                "authors": list(self.authors), "year": self.year,
                "text": self.raw[:200]}


@dataclass
class Citation:
    """One citation occurrence in the body text."""

    form: str
    raw: str
    start: int
    end: int
    #: Reference numbers this citation names, expanded from any ranges.
    numbers: Tuple[int, ...] = ()
    #: Author/year pairs this citation names.
    author_years: Tuple[Tuple[str, str], ...] = ()
    #: Keys it resolved to.  Empty means unresolved.
    keys: Tuple[str, ...] = ()
    #: Numbers or names that matched no reference.
    unresolved: Tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.keys) and not self.unresolved

    def to_dict(self) -> Dict[str, Any]:
        return {"form": self.form, "text": self.raw, "position": self.start,
                "numbers": list(self.numbers), "keys": list(self.keys),
                "unresolved": list(self.unresolved)}


@dataclass
class CitationIssue:
    """One defect found in the citation apparatus."""

    kind: str
    severity: str
    message: str
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "severity": self.severity,
                "message": self.message, **({"detail": self.detail}
                                            if self.detail else {})}


@dataclass
class CitationAnalysis:
    """Everything the engine learned about one document's citations."""

    entries: List[BibEntry] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    issues: List[CitationIssue] = field(default_factory=list)
    detected_style: str = "none"

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected_style": self.detected_style,
            "counts": {
                "bibliography_entries": len(self.entries),
                "citations": len(self.citations),
                "resolved": sum(1 for c in self.citations if c.resolved),
                "unresolved": sum(1 for c in self.citations if not c.resolved),
                "issues": len(self.issues),
                "errors": sum(1 for i in self.issues if i.severity == "error"),
            },
            "issues": [i.to_dict() for i in self.issues],
            "citations": [c.to_dict() for c in self.citations],
            "bibliography": [e.to_dict() for e in self.entries],
        }


# --------------------------------------------------------------------------- #
# Detection patterns
# --------------------------------------------------------------------------- #

# A bracketed or parenthesised run of numbers, separators and dashes.  The body
# is validated afterwards rather than in the pattern, because the pattern must
# also match the malformed cases worth reporting -- "[1,,3]", "[4-]" -- which a
# stricter pattern would silently skip.
# The lookbehind rejects a bracket that follows a backslash, which is how
# LaTeX writes an optional argument (``\\cite[p.~3]{x}``, ``\\begin{figure}[h]``)
# and never how a manuscript writes a citation.  It deliberately does *not*
# reject a bracket following a letter: Word manuscripts attach citations
# directly to the preceding word far more often than not ("the disorder[7]"),
# and a guard against array subscripts would silently drop every one of them.
_NUMERIC_GROUP_RE = re.compile(
    r"(?<!\\)(?<![0-9])([\[(])\s*([0-9][0-9\s,;]*(?:[-–—]\s*[0-9]+[0-9\s,;]*)*)\s*([\])])")

# A raised number, in either of the two forms conversion produces.
_SUPERSCRIPT_RE = re.compile(
    r"\\textsuperscript\s*\{([0-9][0-9\s,;–—-]*)\}"
    r"|\$\^\{?\s*([0-9][0-9\s,;–—-]*)\s*\}?\$"
)

# (Roe, 2021), (Roe et al., 2021; Doe & Poe, 2019).  The year anchors it: a
# parenthetical without one is an aside, not a citation.
_PAREN_AUTHOR_YEAR_RE = re.compile(
    r"\(([^()]*?\b(?:1[89]|20)\d{2}[a-z]?[^()]*?)\)"
)

# Roe (2021) / Roe et al. (2021) / Roe and Doe (2021).
_NARRATIVE_RE = re.compile(
    r"\b([A-Z][\w'’\-]+(?:\s+(?:et\s+al\.?|and|&|,)\s*[A-Z]?[\w'’\-]*)*)"
    r"\s*\(\s*((?:1[89]|20)\d{2}[a-z]?)\s*\)"
)

# \href{...}{[3]} and \url-style links whose visible text is the citation.
_HYPERLINK_RE = re.compile(r"\\href\s*\{[^}]*\}\s*\{([^}]*)\}")

# A citation that has already been rendered as a LaTeX command.  This is not a
# Word shape, but the engine also runs over rendered LaTeX during validation,
# and a document whose citations are all already correct would otherwise be
# reported as having no citations at all and every reference as uncited -- the
# most misleading report the engine could produce.
_COMMAND_RE = re.compile(
    r"(?<!\\)\\[Cc]ite[a-zA-Z]*\s*(?:\[[^\]]*\])*\s*\{([^}]*)\}"
)

# A leading number on a reference-list line: "1. ", "[1] ", "1) ".
_ENTRY_NUMBER_RE = re.compile(r"^\s*(?:\[\s*(\d+)\s*\]|(\d+)\s*[.)])\s*")

# A surname at the head of a reference, in either of the two orders reference
# lists use ("Roe, J." and "J. Roe").
_ENTRY_AUTHOR_RE = re.compile(
    r"^\s*(?:[A-Z]\.\s*)*([^\W\d_][\w'’\-]+)\s*,|^\s*([^\W\d_][\w'’\-]+)\s+[A-Z]\."
)
_ENTRY_YEAR_RE = re.compile(r"\b((?:1[89]|20)\d{2})[a-z]?\b")

# Separators inside a citation group.
_GROUP_SPLIT_RE = re.compile(r"[;,]")
_RANGE_RE = re.compile(r"^\s*(\d+)\s*[-–—]\s*(\d+)\s*$")

#: A number range wider than this is far more likely to be a page range, a
#: measurement or a year interval that happens to sit in brackets than a run of
#: citations.  Expanding it would invent dozens of citations that do not exist.
_MAX_RANGE_SPAN = 60


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #

class CitationEngine:
    """Detects, validates and renders citations."""

    # -- 1. the reference list ---------------------------------------------- #

    def build_bibliography(self, references: Sequence[str],
                           rules: Optional[JournalRules] = None
                           ) -> List[BibEntry]:
        """Turn the document's reference list into addressable entries.

        Keys are positional because a Word reference list has none of its own:
        it is formatted prose, and any key derived from its content would break
        the moment an author edited a surname.  What *is* read out of each
        entry is the number the document printed, the first surname and the
        year -- the three things a citation can name.

        The key itself is not computed here.  It comes from
        ``rules.bibliography.key_for``, which is also what the renderer calls
        when it writes ``\\bibitem``, so the two cannot disagree.
        """
        bibliography = (rules or JournalRules()).bibliography
        entries: List[BibEntry] = []
        for idx, raw in enumerate(references or []):
            text = (raw or "").strip()
            if not text:
                continue
            number = None
            m = _ENTRY_NUMBER_RE.match(text)
            body = text
            if m:
                number = int(m.group(1) or m.group(2))
                body = text[m.end():].strip()
            authors: Tuple[str, ...] = ()
            am = _ENTRY_AUTHOR_RE.match(body)
            if am:
                authors = ((am.group(1) or am.group(2) or "").strip(),)
            ym = _ENTRY_YEAR_RE.search(body)
            entries.append(BibEntry(
                index=len(entries), raw=text,
                key=bibliography.key_for(len(entries) + 1),
                # An unnumbered list is implicitly numbered by position, which
                # is how it will be typeset; treating it as unnumbered would
                # make every numeric citation unresolvable.
                number=number if number is not None else len(entries) + 1,
                authors=authors, year=ym.group(1) if ym else None,
            ))
        return entries

    # -- 2. detection -------------------------------------------------------- #

    def detect(self, text: str) -> List[Citation]:
        """Every citation-shaped span in the text, in reading order.

        Overlapping matches are resolved in favour of the first detector to
        claim a span, and the detectors are ordered so the more specific
        shape wins: a hyperlink whose text is ``[3]`` is a hyperlinked
        citation, not a bare bracket that happens to sit inside one.
        """
        found: List[Citation] = []
        claimed: List[Tuple[int, int]] = []

        def free(start: int, end: int) -> bool:
            return not any(start < c_end and end > c_start
                           for c_start, c_end in claimed)

        def claim(citation: Citation) -> None:
            found.append(citation)
            claimed.append((citation.start, citation.end))

        # Already-rendered commands are claimed first: their span covers text
        # that every other detector would also match, and their keys are
        # authoritative because a human or an earlier pass already resolved
        # them.
        for m in _COMMAND_RE.finditer(text):
            keys = tuple(k.strip() for k in m.group(1).split(",") if k.strip())
            if keys:
                citation = Citation(form="command", raw=m.group(0),
                                    start=m.start(), end=m.end())
                citation.keys = keys
                claim(citation)

        for m in _HYPERLINK_RE.finditer(text):
            # The visible text of the link is itself a citation in one of the
            # shapes below -- Word's cross-reference-to-bibliography produces
            # exactly "[3]" wrapped in a link -- so the label is re-examined
            # with the group pattern rather than read as a bare number list.
            label = m.group(1)
            group = _NUMERIC_GROUP_RE.search(label)
            numbers = self._numbers_in(group.group(2) if group else label)
            if numbers or _PAREN_AUTHOR_YEAR_RE.search(label):
                claim(Citation(form="hyperlink", raw=m.group(0),
                               start=m.start(), end=m.end(),
                               numbers=numbers,
                               author_years=self._author_years_in(label)))

        for m in _SUPERSCRIPT_RE.finditer(text):
            if not free(m.start(), m.end()):
                continue
            body = m.group(1) or m.group(2) or ""
            numbers = self._numbers_in(body)
            if numbers:
                claim(Citation(form="superscript", raw=m.group(0),
                               start=m.start(), end=m.end(), numbers=numbers))

        # Narrative citations are detected before numeric groups, because the
        # two overlap on the same characters: in "Doe (2020)" the parenthesis
        # is the year of a narrative citation, and a numeric detector reaching
        # it first would read it as a citation to reference number 2020.  The
        # more specific reading -- the one that also accounts for the name in
        # front of the bracket -- has to win.
        for m in _NARRATIVE_RE.finditer(text):
            if not free(m.start(), m.end()):
                continue
            claim(Citation(form="narrative", raw=m.group(0),
                           start=m.start(), end=m.end(),
                           author_years=((self._surname(m.group(1)),
                                          m.group(2)),)))

        for m in _NUMERIC_GROUP_RE.finditer(text):
            if not free(m.start(), m.end()):
                continue
            numbers = self._numbers_in(m.group(2))
            if not numbers or self._is_bare_year(numbers):
                continue
            form = "bracket_numeric" if m.group(1) == "[" else "paren_numeric"
            claim(Citation(form=form, raw=m.group(0),
                           start=m.start(), end=m.end(), numbers=numbers))

        for m in _PAREN_AUTHOR_YEAR_RE.finditer(text):
            if not free(m.start(), m.end()):
                continue
            pairs = self._author_years_in(m.group(1))
            if pairs:
                claim(Citation(form="paren_author_year", raw=m.group(0),
                               start=m.start(), end=m.end(),
                               author_years=pairs))

        found.sort(key=lambda c: c.start)
        return found

    def _numbers_in(self, body: str) -> Tuple[int, ...]:
        """Expand a citation group's body into the numbers it names.

        ``[2-6]`` names five references; ``[1,3]`` names two.  A range is only
        expanded when it is short and ascending, because a wide or descending
        one is not a citation range at all -- it is a page span or a year
        interval that happens to be bracketed, and expanding it would invent
        citations the document never made.
        """
        numbers: List[int] = []
        for part in _GROUP_SPLIT_RE.split(body or ""):
            part = part.strip()
            if not part:
                continue
            rng = _RANGE_RE.match(part)
            if rng:
                lo, hi = int(rng.group(1)), int(rng.group(2))
                if 0 < lo <= hi and (hi - lo) <= _MAX_RANGE_SPAN:
                    numbers.extend(range(lo, hi + 1))
                continue
            if part.isdigit():
                value = int(part)
                if value > 0:
                    numbers.append(value)
        # Order is preserved and duplicates within one group are collapsed:
        # "[3,3]" cites one reference, awkwardly.
        seen: Set[int] = set()
        return tuple(n for n in numbers if not (n in seen or seen.add(n)))

    @staticmethod
    def _is_bare_year(numbers: Sequence[int]) -> bool:
        """True when a bracketed group is a year rather than a citation number.

        "(2020)" and "[1998]" are years wherever they appear; no reference list
        in existence has two thousand entries.  Reading one as a citation
        manufactures a missing-reference error for text that is perfectly
        correct, which is worse than missing a citation: it puts noise in the
        report the reader is supposed to trust.
        """
        return len(numbers) == 1 and 1500 <= numbers[0] <= 2100

    def _author_years_in(self, body: str) -> Tuple[Tuple[str, str], ...]:
        pairs: List[Tuple[str, str]] = []
        for chunk in re.split(r";", body or ""):
            ym = _ENTRY_YEAR_RE.search(chunk)
            if not ym:
                continue
            name_part = chunk[:ym.start()]
            surname = self._surname(name_part)
            if surname:
                pairs.append((surname, ym.group(1)))
        return tuple(pairs)

    @staticmethod
    def _surname(text: str) -> str:
        """The surname a citation names, from whatever surrounds it.

        Only the first capitalised word matters: "Roe et al." and "Roe and Doe"
        both cite an entry whose first author is Roe, and matching on more than
        that would fail whenever the reference list abbreviates differently
        from the citation.
        """
        for token in re.split(r"[\s,&]+", (text or "").strip()):
            token = token.strip(".,;()[]")
            if not token or token.lower() in ("et", "al", "and", "the"):
                continue
            if token[:1].isupper():
                return token
        return ""

    # -- 3. resolution and validation ---------------------------------------- #

    def analyse(self, references: Sequence[str], text: str,
                rules: Optional[JournalRules] = None) -> CitationAnalysis:
        """Detect, resolve and validate, in one pass over one document."""
        analysis = CitationAnalysis()
        analysis.entries = self.build_bibliography(references, rules)
        analysis.citations = self.detect(text)
        analysis.detected_style = self._detect_style(analysis.citations)

        by_number: Dict[int, BibEntry] = {}
        duplicate_numbers: List[int] = []
        for entry in analysis.entries:
            if entry.number in by_number:
                duplicate_numbers.append(entry.number)
            else:
                by_number[entry.number] = entry
        by_author_year: Dict[Tuple[str, str], BibEntry] = {}
        for entry in analysis.entries:
            if entry.authors and entry.year:
                by_author_year.setdefault(
                    (entry.authors[0].lower(), entry.year), entry)

        known_keys = {e.key for e in analysis.entries}
        used: Set[str] = set()
        for citation in analysis.citations:
            if citation.form == "command":
                # The keys are already chosen; the only open question is
                # whether the bibliography still contains them.
                citation.unresolved = tuple(k for k in citation.keys
                                            if k not in known_keys)
                used.update(k for k in citation.keys if k in known_keys)
                continue
            keys: List[str] = []
            unresolved: List[str] = []
            for number in citation.numbers:
                entry = by_number.get(number)
                if entry:
                    keys.append(entry.key)
                    used.add(entry.key)
                else:
                    unresolved.append(str(number))
            for surname, year in citation.author_years:
                entry = by_author_year.get((surname.lower(), year))
                if entry:
                    keys.append(entry.key)
                    used.add(entry.key)
                else:
                    unresolved.append(f"{surname} {year}")
            citation.keys = tuple(dict.fromkeys(keys))
            citation.unresolved = tuple(unresolved)

        self._validate(analysis, by_number, duplicate_numbers, used)
        return analysis

    def _validate(self, analysis: CitationAnalysis,
                  by_number: Dict[int, BibEntry],
                  duplicate_numbers: Sequence[int],
                  used: Set[str]) -> None:
        add = analysis.issues.append

        # A citation with no matching reference typesets as a number pointing
        # at nothing.  It is the most serious defect in the apparatus, because
        # the reader cannot recover what was meant.
        for citation in analysis.citations:
            if citation.unresolved:
                add(CitationIssue(
                    kind="missing_reference", severity="error",
                    message=(f"citation {citation.raw.strip()} names "
                             f"{', '.join(citation.unresolved)}, which "
                             f"{'have' if len(citation.unresolved) > 1 else 'has'} "
                             "no entry in the reference list"),
                    detail={"citation": citation.raw.strip(),
                            "unresolved": list(citation.unresolved),
                            "position": citation.start},
                ))

        for number in sorted(set(duplicate_numbers)):
            add(CitationIssue(
                kind="duplicate_numbering", severity="error",
                message=(f"reference number {number} is used by more than one "
                         "entry in the reference list, so a citation to it is "
                         "ambiguous"),
                detail={"number": number},
            ))

        unused = [e for e in analysis.entries if e.key not in used]
        if unused:
            add(CitationIssue(
                kind="unused_reference", severity="warning",
                message=(f"{len(unused)} reference"
                         f"{'s are' if len(unused) > 1 else ' is'} never cited "
                         "in the text"),
                detail={"entries": [{"number": e.number, "text": e.raw[:120]}
                                    for e in unused[:50]]},
            ))

        # Numbered styles require the reference list to be numbered in order of
        # first citation, with no gaps.  Both failures are invisible in the
        # source and obvious in the PDF.
        if analysis.detected_style in ("numeric", "superscript"):
            cited = sorted({n for c in analysis.citations for n in c.numbers
                            if n in by_number})
            if cited:
                gaps = [n for n in range(cited[0], cited[-1] + 1)
                        if n not in set(cited)]
                if gaps:
                    add(CitationIssue(
                        kind="broken_sequence", severity="warning",
                        message=(f"the cited numbers skip "
                                 f"{len(gaps)} value"
                                 f"{'s' if len(gaps) > 1 else ''} "
                                 f"({', '.join(str(g) for g in gaps[:15])}"
                                 f"{'...' if len(gaps) > 15 else ''}), so the "
                                 "reference list is not a contiguous sequence"),
                        detail={"missing_numbers": gaps[:50]},
                    ))
                first_use: List[int] = []
                for citation in analysis.citations:
                    for number in citation.numbers:
                        if number in by_number and number not in first_use:
                            first_use.append(number)
                if first_use != sorted(first_use):
                    out_of_order = [n for i, n in enumerate(first_use)
                                    if i and n < first_use[i - 1]]
                    add(CitationIssue(
                        kind="out_of_order_numbering", severity="warning",
                        message=("references are not numbered in order of first "
                                 "citation; the first out-of-order citation is "
                                 f"[{out_of_order[0]}]"),
                        detail={"first_use_order": first_use[:60]},
                    ))

        if analysis.entries and not analysis.citations:
            add(CitationIssue(
                kind="no_citations", severity="warning",
                message=("the document has a reference list but no citation "
                         "was detected in the body text"),
            ))

    @staticmethod
    def _detect_style(citations: Sequence[Citation]) -> str:
        """The style the *source document* used, which is not the target style.

        Worth recording because a mismatch between the two is a real editorial
        decision -- converting an author-year manuscript into a numbered
        journal renumbers every citation -- and because a document that mixes
        both is usually one an author assembled from two sources.
        """
        numeric = sum(1 for c in citations
                      if c.form in ("bracket_numeric", "paren_numeric"))
        superscript = sum(1 for c in citations if c.form == "superscript")
        author_year = sum(1 for c in citations
                          if c.form in ("paren_author_year", "narrative"))
        if not citations:
            return "none"
        if all(c.form == "command" for c in citations):
            # Nothing can be said about the source document's style from LaTeX
            # that has already been rendered.
            return "rendered"
        if numeric and author_year:
            return "mixed"
        if superscript >= max(numeric, author_year):
            return "superscript"
        if author_year > numeric:
            return "author_year"
        return "numeric"

    # -- 4. rendering, the only stage that knows about the journal ----------- #

    def render(self, text: str, analysis: CitationAnalysis,
               rules: JournalRules) -> str:
        """Rewrite every resolved citation in the journal's own command.

        Replacement runs back to front so that each span's recorded offsets
        stay valid as earlier ones are rewritten.  An unresolved citation is
        left exactly as the author wrote it: turning it into a command would
        produce a ``[?]`` in the PDF and bury the defect in the compilation
        log, whereas leaving it visible keeps it where the validation report
        can point at it.
        """
        pieces = list(text)
        for citation in sorted(analysis.citations, key=lambda c: c.start,
                               reverse=True):
            # A citation already written as a command is left alone: it is
            # either the output of an earlier run of this engine or a command
            # a human wrote, and rewriting either would regroup keys the
            # author deliberately separated.
            if citation.form == "command" or not citation.resolved:
                continue
            rendered = self._render_one(citation, rules)
            if rendered is None:
                continue
            pieces[citation.start:citation.end] = list(rendered)
        return "".join(pieces)

    def _render_one(self, citation: Citation,
                    rules: JournalRules) -> Optional[str]:
        style = rules.citation.style
        keys = list(citation.keys)
        if not keys:
            return None

        if style == "author_year":
            # The two author-year shapes are not interchangeable: one is an
            # aside in brackets, the other is the subject of the sentence, and
            # swapping them makes the prose ungrammatical.
            command = (rules.citation.textual_command
                       if citation.form == "narrative"
                       else rules.citation.parenthetical_command)
        else:
            command = rules.citation.command

        if rules.citation.group_multiple:
            body = "\\" + command + "{" + ",".join(keys) + "}"
        else:
            body = "".join("\\" + command + "{" + key + "}" for key in keys)

        wrapper = rules.citation.wrapper
        if style == "superscript" and not wrapper:
            # A journal that wants superscript citations but names no wrapper
            # gets the LaTeX construct for one; raising text is a typesetting
            # primitive, not a house style anyone needs to declare.
            wrapper = "textsuperscript"
        if wrapper:
            body = "\\" + wrapper.lstrip("\\") + "{" + body + "}"
        return body
