"""Reading what LaTeX actually said.

Every fact needed to judge whether a document typeset well is written to the
``.log`` file, and until now nothing in this pipeline opened it.  Compilation
was judged solely by whether a PDF appeared, which is a very low bar: LaTeX
emits a PDF for a document with a two-inch overfull line, a figure that pushed
past the bottom margin, a citation that resolved to ``[?]`` and a cross
reference that resolved to ``??``.  All four are visible to a reader and none
of them is an error.

This module turns the log into structured diagnostics so the layout, biography
and validation engines can act on them.  It parses; it does not judge.  Which
diagnostics matter, and what to do about them, belongs to the engines that ask.

Two properties matter more than completeness here.  The first is that parsing
must never raise: a log is the artefact you consult *because* something went
wrong, and a parser that dies on a malformed one is useless exactly when it is
needed.  The second is that line wrapping must be undone before matching.  TeX
hard-wraps its log at (usually) 79 columns, mid-word and mid-number, so a
regex applied to raw lines silently misses a large fraction of real warnings --
which is the classic reason a log parser reports a suspiciously clean document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# --------------------------------------------------------------------------- #
# Diagnostic model
# --------------------------------------------------------------------------- #

#: Severity ordering, worst first.  Used for sorting and for deciding whether a
#: category should block delivery.
SEVERITIES = ("error", "warning", "info")


@dataclass(frozen=True)
class Diagnostic:
    """One thing LaTeX reported."""

    #: Stable machine-readable category: "overfull_hbox", "underfull_vbox",
    #: "float_too_large", "float_stuck", "undefined_reference",
    #: "undefined_citation", "multiply_defined_label", "missing_character",
    #: "missing_file", "package_error", "latex_error", "package_warning".
    category: str
    severity: str
    message: str
    #: Source line in the .tex the message was attributed to, when TeX said.
    source_line: Optional[int] = None
    #: Page the message was attributed to, when TeX said.
    page: Optional[int] = None
    #: Magnitude in points for box warnings; the number that says whether an
    #: overfull box is a hairline or a visible protrusion into the margin.
    overflow_pt: Optional[float] = None
    #: Badness for underfull boxes, on TeX's 0-10000 scale.
    badness: Optional[int] = None
    #: The name a reference, citation or label diagnostic is about.
    target: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {"category": self.category, "severity": self.severity,
               "message": self.message}
        for key in ("source_line", "page", "overflow_pt", "badness", "target"):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        return out


@dataclass
class LogReport:
    """Everything the log said, grouped for the engines that consume it."""

    diagnostics: List[Diagnostic] = field(default_factory=list)
    #: Total pages, when the log states it.  A count that jumps between
    #: recompiles is itself a signal that a layout change was not neutral.
    pages: Optional[int] = None
    parsed: bool = True
    parse_note: str = ""

    # -- queries used by the engines ---------------------------------------- #

    def of(self, *categories: str) -> List[Diagnostic]:
        wanted = set(categories)
        return [d for d in self.diagnostics if d.category in wanted]

    @property
    def errors(self) -> List[Diagnostic]:
        return [d for d in self.diagnostics if d.severity == "error"]

    @property
    def overfull(self) -> List[Diagnostic]:
        return self.of("overfull_hbox", "overfull_vbox")

    @property
    def underfull(self) -> List[Diagnostic]:
        return self.of("underfull_hbox", "underfull_vbox")

    @property
    def float_problems(self) -> List[Diagnostic]:
        return self.of("float_too_large", "float_stuck")

    @property
    def broken_links(self) -> List[Diagnostic]:
        """References and citations that will typeset as ``??`` or ``[?]``."""
        return self.of("undefined_reference", "undefined_citation",
                       "multiply_defined_label")

    def worst_overflow_pt(self) -> float:
        """Largest overfull magnitude, or 0.0.

        The single most useful number for deciding whether a layout retry
        helped: a run whose worst overflow fell from 34pt to 2pt improved, even
        if the *count* of warnings went up.
        """
        return max((d.overflow_pt or 0.0 for d in self.overfull), default=0.0)

    def summary(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for d in self.diagnostics:
            counts[d.category] = counts.get(d.category, 0) + 1
        return {
            "parsed": self.parsed,
            "parse_note": self.parse_note,
            "pages": self.pages,
            "counts": counts,
            "total": len(self.diagnostics),
            "errors": len(self.errors),
            "worst_overflow_pt": round(self.worst_overflow_pt(), 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {**self.summary(),
                "diagnostics": [d.to_dict() for d in self.diagnostics]}


# --------------------------------------------------------------------------- #
# Patterns
# --------------------------------------------------------------------------- #
#
# Applied to *unwrapped* text.  Each is anchored on the fixed part of the
# message TeX emits, and every variable part is captured rather than skipped,
# because the magnitude is what makes a box warning actionable.

_OVERFULL_RE = re.compile(
    r"^(Overfull|Underfull)\s+\\(hbox|vbox)\s+\((?:(\d+(?:\.\d+)?)pt too (?:wide|high)"
    r"|badness (\d+))\)"
    r"(?:[^\n]*?\blines?\s+(\d+)(?:--(\d+))?|[^\n]*?\bat line\s+(\d+))?",
    re.MULTILINE,
)

# "Float too large" is the only float message that carries a magnitude, and it
# is a distinct fault from a float that merely could not be placed where it was
# asked for: this one cannot fit on a page at all at its current size, so the
# remedy is to shrink it rather than to move it.  Specifier changes and
# deferred floats are matched separately, below, so the two never double-count.
_FLOAT_TOO_LARGE_RE = re.compile(
    r"^LaTeX Warning: Float too large for page by (\d+(?:\.\d+)?)pt"
    r"[^\n]*?(?:on input line (\d+))?",
    re.MULTILINE,
)

_UNDEFINED_REF_RE = re.compile(
    r"^LaTeX Warning: Reference `([^']*)' on page (\d+) undefined on input line (\d+)",
    re.MULTILINE,
)

_UNDEFINED_CITE_RE = re.compile(
    r"^LaTeX Warning: Citation `([^']*)' on page (\d+) undefined on input line (\d+)",
    re.MULTILINE,
)

_MULTIPLY_DEFINED_RE = re.compile(
    r"^LaTeX Warning: Label `([^']*)' multiply defined",
    re.MULTILINE,
)

_MISSING_CHAR_RE = re.compile(
    r"^Missing character: There is no (.+?) in font ([^!]*)!",
    re.MULTILINE,
)

_LATEX_ERROR_RE = re.compile(
    r"^! (LaTeX Error: )?(.+)$",
    re.MULTILINE,
)

_PACKAGE_WARNING_RE = re.compile(
    r"^(?:Package|Class) (\w+) Warning: (.+?)(?:\s+on input line (\d+))?\.?$",
    re.MULTILINE,
)

_PACKAGE_ERROR_RE = re.compile(
    r"^(?:Package|Class) (\w+) Error: (.+?)\.?$",
    re.MULTILINE,
)

_MISSING_FILE_RE = re.compile(
    r"^(?:! LaTeX Error: File `([^']*)' not found|"
    r"! Unable to find (?:file|epsfile) `?([^'\s]*)'?)",
    re.MULTILINE,
)

#: Openings of the messages parsed below.  A line matching this is the start of
#: a new message and so can never be the continuation of a wrapped one.
_MESSAGE_START_RE = re.compile(
    r"^(?:!|Overfull |Underfull |LaTeX Warning:|LaTeX Font Warning:|"
    r"Package \w+ (?:Warning|Error):|Class \w+ (?:Warning|Error):|"
    r"Missing character:|Output written on |Runaway argument)"
)

_PAGES_RE = re.compile(r"Output written on [^(]*\((\d+) pages?", re.MULTILINE)

#: Float-placement trouble that TeX reports without the words "too large":
#: a float held back so far that it is deferred to the end of the document, and
#: the ``[]`` overfull that a wrapped figure produces when text does not fit
#: beside it.  Both are the concrete failure modes a biography photo layout
#: hits, so both must be visible to the retry logic.
_FLOAT_STUCK_RE = re.compile(
    r"^LaTeX Warning: (?:.*?\bh\b.*? float specifier|"
    r"Text page \d+ contains only floats|"
    r"Some float\(?s?\)? (?:were|was) not (?:placed|processed))[^\n]*",
    re.MULTILINE | re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #

class LatexLogParser:
    """Turns a ``.log`` (or raw compiler output) into a :class:`LogReport`."""

    #: TeX wraps its log at max_print_line columns, breaking messages mid-token.
    #: A continuation line is one that follows a wrap; joining them back is a
    #: prerequisite for matching anything reliably, not an optimisation.
    _WRAP_WIDTH = 79

    def parse_file(self, log_path: Optional[Path]) -> LogReport:
        """Parse a log file, degrading to an empty report rather than raising.

        A missing or unreadable log is not an error condition here: it means
        the caller has no information, which the report says explicitly through
        ``parsed=False`` so a consumer never mistakes "nothing was reported"
        for "nothing was wrong".
        """
        if not log_path:
            return LogReport(parsed=False, parse_note="no log path was provided")
        path = Path(log_path)
        if not path.is_file():
            return LogReport(parsed=False,
                             parse_note=f"log file not found: {path.name}")
        try:
            # LaTeX logs are not reliably UTF-8: fonts and packages write bytes
            # from whatever encoding they were authored in.
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return LogReport(parsed=False,
                             parse_note=f"log file could not be read ({exc})")
        return self.parse_text(text)

    def parse_text(self, text: str) -> LogReport:
        report = LogReport()
        if not text:
            report.parsed = False
            report.parse_note = "the log was empty"
            return report
        try:
            unwrapped = self._unwrap(text)
            self._collect(unwrapped, report)
        except Exception as exc:  # noqa: BLE001 - a log parser must not raise
            report.parse_note = (f"the log was parsed partially "
                                 f"({type(exc).__name__}: {exc})")
        return report

    # -- unwrapping ---------------------------------------------------------- #

    def _unwrap(self, text: str) -> str:
        """Undo TeX's hard wrapping.

        A line of *exactly* the wrap width was cut mid-message, so the line
        after it continues it.  Two details make the difference between this
        working and quietly destroying the log.

        The test is on the length of the last *segment* appended, not on the
        length of the line built so far: once two segments have been joined the
        result is longer than the wrap width by construction, and testing the
        whole accumulated line would make every subsequent line of the log
        continue the same one -- collapsing the file into a single line and
        with it every ``^``-anchored pattern below.

        And a line that opens a message of its own is never treated as a
        continuation, however long its predecessor was.  TeX writes plenty of
        naturally full-width lines (font paths, package banners); joining a
        real warning onto one of those hides the warning just as effectively.
        """
        out: List[str] = []
        last_segment = 0
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            if (out and last_segment == self._WRAP_WIDTH
                    and not _MESSAGE_START_RE.match(line)):
                out[-1] += line
            else:
                out.append(line)
            last_segment = len(line)
        return "\n".join(out)

    # -- collection ---------------------------------------------------------- #

    def _collect(self, text: str, report: LogReport) -> None:
        _collect_diagnostics(self, text, report)

    def _add(self, report: LogReport, diagnostic: Diagnostic) -> None:
        report.diagnostics.append(diagnostic)


def _collect_diagnostics(self: LatexLogParser, text: str,
                         report: LogReport) -> None:
    """Populate ``report`` from unwrapped log text."""

    for m in _OVERFULL_RE.finditer(text):
        kind, box, overflow, badness, first_line, _last, at_line = m.groups()
        first_line = first_line or at_line
        prefix = kind.lower()
        category = f"{prefix}_{box}"
        self._add(report, Diagnostic(
            category=category,
            # An overfull box puts ink outside the type block, which a reader
            # sees; an underfull one only stretches white space, which is
            # ugly at worst.  Ranking them the same would drown the real
            # problems in a long document.
            severity="warning" if prefix == "overfull" else "info",
            message=m.group(0).strip()[:400],
            overflow_pt=float(overflow) if overflow else None,
            badness=int(badness) if badness else None,
            source_line=int(first_line) if first_line else None,
        ))

    for m in _FLOAT_TOO_LARGE_RE.finditer(text):
        overflow, line_no = m.group(1), m.group(2)
        self._add(report, Diagnostic(
            category="float_too_large",
            severity="warning",
            message=m.group(0).strip()[:400],
            overflow_pt=float(overflow) if overflow else None,
            source_line=int(line_no) if line_no else None,
        ))

    for m in _FLOAT_STUCK_RE.finditer(text):
        self._add(report, Diagnostic(
            category="float_stuck", severity="warning",
            message=m.group(0).strip()[:400],
        ))

    for m in _UNDEFINED_REF_RE.finditer(text):
        target, page, line_no = m.groups()
        self._add(report, Diagnostic(
            category="undefined_reference",
            # A dangling reference typesets as "??" in the delivered PDF.  It
            # is not an error to TeX and it is unambiguously a defect to a
            # reader, which is exactly the class of problem this engine exists
            # to catch, so it is recorded at error severity.
            severity="error",
            message=m.group(0).strip()[:400],
            target=target, page=int(page), source_line=int(line_no),
        ))

    for m in _UNDEFINED_CITE_RE.finditer(text):
        target, page, line_no = m.groups()
        self._add(report, Diagnostic(
            category="undefined_citation", severity="error",
            message=m.group(0).strip()[:400],
            target=target, page=int(page), source_line=int(line_no),
        ))

    for m in _MULTIPLY_DEFINED_RE.finditer(text):
        self._add(report, Diagnostic(
            category="multiply_defined_label", severity="error",
            message=m.group(0).strip()[:400], target=m.group(1),
        ))

    seen_chars = set()
    for m in _MISSING_CHAR_RE.finditer(text):
        # One missing glyph is usually thousands of identical messages; the
        # useful report is which glyph, not how many times.
        key = m.group(1)
        if key in seen_chars:
            continue
        seen_chars.add(key)
        self._add(report, Diagnostic(
            category="missing_character", severity="warning",
            message=m.group(0).strip()[:400], target=key,
        ))

    for m in _MISSING_FILE_RE.finditer(text):
        self._add(report, Diagnostic(
            category="missing_file", severity="error",
            message=m.group(0).strip()[:400],
            target=(m.group(1) or m.group(2) or "").strip(),
        ))

    for m in _PACKAGE_ERROR_RE.finditer(text):
        self._add(report, Diagnostic(
            category="package_error", severity="error",
            message=m.group(0).strip()[:400], target=m.group(1),
        ))

    for m in _PACKAGE_WARNING_RE.finditer(text):
        line_no = m.group(3)
        self._add(report, Diagnostic(
            category="package_warning", severity="warning",
            message=m.group(0).strip()[:400], target=m.group(1),
            source_line=int(line_no) if line_no else None,
        ))

    for m in _LATEX_ERROR_RE.finditer(text):
        body = (m.group(2) or "").strip()
        # "! " also introduces TeX's interactive prompts and the "Emergency
        # stop" epilogue, neither of which is a distinct fault.
        if not body or body.startswith("==>") or body.startswith("Emergency stop"):
            continue
        self._add(report, Diagnostic(
            category="latex_error", severity="error", message=body[:400],
        ))

    pages = _PAGES_RE.search(text)
    if pages:
        report.pages = int(pages.group(1))

    # Deterministic order: worst first, then by category, so two reports of the
    # same document are comparable and a diff between retries is meaningful.
    order = {s: i for i, s in enumerate(SEVERITIES)}
    report.diagnostics.sort(
        key=lambda d: (order.get(d.severity, 99), d.category,
                       -(d.overflow_pt or 0.0), d.source_line or 0)
    )


def parse_log(log_path: Optional[Path]) -> LogReport:
    """Convenience entry point."""
    return LatexLogParser().parse_file(log_path)
