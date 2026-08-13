"""The Cross Reference Engine: every pointer in the document, checked.

A LaTeX document is a graph.  ``\\label`` declares a node, ``\\ref`` and
``\\cite`` declare edges, and the compiler resolves the edges on a later pass.
When an edge points nowhere the compiler does not stop -- it typesets ``??`` or
``[?]``, notes the fact in the log, and produces a PDF that looks finished.
That is the failure this engine exists to prevent: not a crash, but a document
that is quietly wrong in a way only a reader notices.

The engine works on the rendered LaTeX, which is the only place where the
graph is complete.  Working on the document model instead would miss every
label the template itself contributes and every reference a journal class
generates, and those are exactly the ones a converted manuscript gets wrong.

Two sources of truth are combined.  Reading the ``.tex`` tells us what the
document *claims*; reading the compilation log tells us what LaTeX *found*.
Either alone is insufficient -- static analysis cannot see a label a class file
defines at run time, and the log cannot see a label that is declared but never
used -- so both are consulted and their findings merged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from app.engines.journal_rules import JournalRules
from app.engines.latex_log import LogReport


#: The kinds of thing a document labels.  Used to classify a label by its
#: prefix so a report can say "two figures are referenced but never labelled"
#: rather than listing opaque strings.
REFERENCE_KINDS = ("figure", "table", "equation", "section", "appendix",
                   "algorithm", "listing", "theorem", "other")


@dataclass
class LabelUse:
    """One ``\\label`` declaration or one reference to a label."""

    name: str
    kind: str
    line: int

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "line": self.line}


@dataclass
class CrossRefIssue:
    kind: str
    severity: str
    message: str
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "severity": self.severity,
                "message": self.message,
                **({"detail": self.detail} if self.detail else {})}


@dataclass
class CrossRefAnalysis:
    labels: List[LabelUse] = field(default_factory=list)
    references: List[LabelUse] = field(default_factory=list)
    citations: List[LabelUse] = field(default_factory=list)
    bib_keys: Set[str] = field(default_factory=set)
    issues: List[CrossRefIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    def to_dict(self) -> Dict[str, Any]:
        by_kind: Dict[str, int] = {}
        for label in self.labels:
            by_kind[label.kind] = by_kind.get(label.kind, 0) + 1
        return {
            "counts": {
                "labels": len(self.labels),
                "references": len(self.references),
                "citations": len(self.citations),
                "bibliography_keys": len(self.bib_keys),
                "issues": len(self.issues),
                "errors": sum(1 for i in self.issues if i.severity == "error"),
            },
            "labels_by_kind": by_kind,
            "issues": [i.to_dict() for i in self.issues],
        }


# --------------------------------------------------------------------------- #
# Patterns
# --------------------------------------------------------------------------- #

# Commands are matched with their braces balanced only to one level, which is
# all a label or a key list ever needs, and the leading (?<!\\) rejects a
# command that has itself been escaped for display in the text.
_LABEL_RE = re.compile(r"(?<!\\)\\label\s*\{([^}]*)\}")
# \ref, \pageref, \eqref, \autoref, \cref, \Cref, \nameref, \vref and the
# cleveref plurals.  Matching the family rather than \ref alone matters: a
# document that uses \cref throughout would otherwise appear to have no
# references at all and every label would be reported as unused.
_REF_RE = re.compile(
    r"(?<!\\)\\(?:page|eq|auto|name|v|c|C)?ref(?:s|\*)?\s*\{([^}]*)\}"
)
_CITE_RE = re.compile(
    r"(?<!\\)\\[Cc]ite[a-zA-Z]*\s*(?:\[[^\]]*\])*\s*\{([^}]*)\}"
)
_BIBITEM_RE = re.compile(r"(?<!\\)\\bibitem\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")
# \input and \include pull in more of the document; a project split across
# files would otherwise look like it had almost no labels.
_INPUT_RE = re.compile(r"(?<!\\)\\(?:input|include)\s*\{([^}]*)\}")
# Environments that are conventionally labelled.  Used to attribute a label to
# a kind when its name carries no prefix, which is the common case in a
# template's own boilerplate.
_ENV_RE = re.compile(r"\\begin\s*\{(figure|table|equation|align|algorithm|"
                     r"lstlisting|theorem|lemma|proof)\*?\}")


class CrossReferenceEngine:
    """Builds and validates the document's internal link graph."""

    def analyse(self, tex_path: Path,
                rules: Optional[JournalRules] = None,
                log: Optional[LogReport] = None,
                expected: Optional[Dict[str, int]] = None) -> CrossRefAnalysis:
        """Check every label, reference and citation in a rendered project.

        ``expected`` optionally carries the counts the document model says the
        paper has -- how many figures, tables and equations were parsed out of
        the DOCX.  Comparing those against the labels actually emitted catches
        the case no amount of LaTeX analysis can: a figure that was rendered
        but never labelled is perfectly valid LaTeX and simply cannot be
        referred to.
        """
        analysis = CrossRefAnalysis()
        sources = self._collect_sources(tex_path)
        if not sources:
            analysis.issues.append(CrossRefIssue(
                kind="unreadable_project", severity="error",
                message=f"the LaTeX source could not be read at {tex_path}",
            ))
            return analysis

        for path, text in sources:
            self._scan(text, analysis, rules)
            analysis.bib_keys.update(m.group(1).strip()
                                     for m in _BIBITEM_RE.finditer(text))

        self._validate(analysis, log, expected, rules)
        return analysis

    # -- reading ------------------------------------------------------------- #

    def _collect_sources(self, tex_path: Path,
                         _seen: Optional[Set[Path]] = None
                         ) -> List[Tuple[Path, str]]:
        """The entry file and everything it pulls in, once each.

        Following ``\\input`` is what makes the analysis correct for templates
        that split their preamble or their back matter into separate files, and
        the visited set is what stops a circular include from hanging the job.
        """
        seen = _seen if _seen is not None else set()
        path = Path(tex_path)
        try:
            resolved = path.resolve()
        except OSError:
            return []
        if resolved in seen or not path.is_file():
            return []
        seen.add(resolved)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        out = [(path, text)]
        for m in _INPUT_RE.finditer(text):
            target = m.group(1).strip()
            if not target:
                continue
            candidate = (path.parent / target)
            if candidate.suffix.lower() != ".tex":
                candidate = candidate.with_suffix(".tex")
            out.extend(self._collect_sources(candidate, seen))
        return out

    def _scan(self, text: str, analysis: CrossRefAnalysis,
              rules: Optional[JournalRules]) -> None:
        stripped = self._strip_comments(text)
        line_of = self._line_index(stripped)
        for m in _LABEL_RE.finditer(stripped):
            name = m.group(1).strip()
            if name:
                analysis.labels.append(LabelUse(
                    name, self._kind_of(name, stripped, m.start(), rules),
                    line_of(m.start())))
        for m in _REF_RE.finditer(stripped):
            for name in self._split_keys(m.group(1)):
                analysis.references.append(LabelUse(
                    name, self._kind_of(name, stripped, m.start(), rules),
                    line_of(m.start())))
        for m in _CITE_RE.finditer(stripped):
            for name in self._split_keys(m.group(1)):
                analysis.citations.append(
                    LabelUse(name, "citation", line_of(m.start())))

    @staticmethod
    def _strip_comments(text: str) -> str:
        """Blank out LaTeX comments, preserving offsets.

        A commented-out ``\\ref`` is not a reference, and reporting it as a
        broken one sends the reader to a line that contains nothing.  Offsets
        are preserved rather than the text shortened so that reported line
        numbers still match the file on disk.
        """
        out = []
        for line in text.split("\n"):
            idx = 0
            while True:
                idx = line.find("%", idx)
                if idx == -1:
                    out.append(line)
                    break
                if idx > 0 and line[idx - 1] == "\\":
                    idx += 1
                    continue
                out.append(line[:idx] + " " * (len(line) - idx))
                break
            else:  # pragma: no cover - defensive
                out.append(line)
        return "\n".join(out)

    @staticmethod
    def _line_index(text: str):
        starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                starts.append(i + 1)

        def line_of(pos: int) -> int:
            lo, hi = 0, len(starts) - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if starts[mid] <= pos:
                    lo = mid
                else:
                    hi = mid - 1
            return lo + 1
        return line_of

    @staticmethod
    def _split_keys(body: str) -> List[str]:
        return [k.strip() for k in (body or "").split(",") if k.strip()]

    @staticmethod
    def _kind_of(name: str, text: str, pos: int,
                 rules: Optional[JournalRules]) -> str:
        """What kind of object a label names.

        The prefix is the reliable signal and is tried first, using the
        journal's own prefixes so a template that labels figures ``f:`` is read
        correctly.  When a label carries no prefix -- common in a template's
        boilerplate -- the enclosing environment is used instead, which is why
        the surrounding text is passed in.
        """
        lowered = name.lower()
        prefixes = {
            "figure": ("fig:", "fig-", "f:"), "table": ("tab:", "tbl:", "t:"),
            "equation": ("eq:", "eqn:", "e:"), "section": ("sec:", "sub:", "s:"),
            "appendix": ("app:", "apx:"), "algorithm": ("alg:", "algo:"),
            "listing": ("lst:", "lis:"), "theorem": ("thm:", "lem:", "prop:"),
        }
        if rules is not None:
            for kind in ("figure", "table", "equation", "section",
                         "appendix", "algorithm"):
                declared = rules.labels.prefix_for(kind).lower()
                if declared and lowered.startswith(declared):
                    return kind
        for kind, options in prefixes.items():
            if any(lowered.startswith(p) for p in options):
                return kind
        window = text[max(0, pos - 600):pos]
        matches = _ENV_RE.findall(window)
        if matches:
            env = matches[-1]
            return {"align": "equation", "lstlisting": "listing",
                    "lemma": "theorem", "proof": "theorem"}.get(env, env)
        return "other"

    # -- validation ---------------------------------------------------------- #

    def _validate(self, analysis: CrossRefAnalysis, log: Optional[LogReport],
                  expected: Optional[Dict[str, int]],
                  rules: Optional[JournalRules]) -> None:
        add = analysis.issues.append
        declared = {l.name for l in analysis.labels}
        referenced = {r.name for r in analysis.references}

        # Duplicate labels: LaTeX keeps the last and every reference to the
        # earlier one silently points at the wrong object.  Nothing in the
        # output distinguishes this from a correct document.
        counts: Dict[str, int] = {}
        for label in analysis.labels:
            counts[label.name] = counts.get(label.name, 0) + 1
        duplicates = sorted(n for n, c in counts.items() if c > 1)
        if duplicates:
            add(CrossRefIssue(
                kind="duplicate_label", severity="error",
                message=(f"{len(duplicates)} label"
                         f"{'s are' if len(duplicates) > 1 else ' is'} declared "
                         "more than once; references to the earlier one will "
                         "point at the wrong object"),
                detail={"labels": duplicates[:50]},
            ))

        dangling = sorted(referenced - declared)
        if dangling:
            add(CrossRefIssue(
                kind="undefined_reference", severity="error",
                message=(f"{len(dangling)} reference"
                         f"{'s point' if len(dangling) > 1 else ' points'} at a "
                         "label that is never declared; "
                         f"{'they' if len(dangling) > 1 else 'it'} will typeset "
                         "as '??'"),
                detail={"labels": dangling[:50]},
            ))

        # An unused label is not a defect -- templates declare labels nobody
        # references, and an author may label ahead of writing -- but an
        # unreferenced *figure or table* usually means a cross reference was
        # lost in conversion, which is worth surfacing.
        unused = sorted(l.name for l in analysis.labels
                        if l.name not in referenced
                        and l.kind in ("figure", "table", "equation"))
        if unused:
            add(CrossRefIssue(
                kind="unreferenced_object", severity="warning",
                message=(f"{len(unused)} figure, table or equation label"
                         f"{'s are' if len(unused) > 1 else ' is'} never "
                         "referenced from the text"),
                detail={"labels": unused[:50]},
            ))

        cited = {c.name for c in analysis.citations}
        if analysis.bib_keys:
            dangling_cites = sorted(cited - analysis.bib_keys)
            if dangling_cites:
                add(CrossRefIssue(
                    kind="undefined_citation", severity="error",
                    message=(f"{len(dangling_cites)} citation"
                             f"{'s name' if len(dangling_cites) > 1 else ' names'} "
                             "a bibliography key that does not exist"),
                    detail={"keys": dangling_cites[:50]},
                ))

        # Objects the document model says exist but that carry no label cannot
        # be referred to at all.  This is the one check that needs the model:
        # unlabelled figures are valid LaTeX and invisible to the compiler.
        if expected:
            by_kind: Dict[str, int] = {}
            for label in analysis.labels:
                by_kind[label.kind] = by_kind.get(label.kind, 0) + 1
            for kind, count in expected.items():
                have = by_kind.get(kind, 0)
                if count > have:
                    add(CrossRefIssue(
                        kind="unlabelled_object", severity="warning",
                        message=(f"the document has {count} {kind}"
                                 f"{'s' if count > 1 else ''} but only {have} "
                                 f"{kind} label{'s' if have != 1 else ''}; the "
                                 f"unlabelled {kind}"
                                 f"{'s' if count - have > 1 else ''} cannot be "
                                 "cross referenced"),
                        detail={"kind": kind, "objects": count, "labels": have},
                    ))

        # What LaTeX itself found.  A label a class file creates at run time is
        # invisible to the scan above, so the log can clear a reference the
        # static analysis flagged -- and it can also flag one the static
        # analysis cleared, when a label is declared inside a conditional that
        # did not fire.
        if log is not None and log.parsed:
            log_undefined = {d.target for d in log.of("undefined_reference")
                             if d.target}
            log_uncited = {d.target for d in log.of("undefined_citation")
                           if d.target}
            confirmed = sorted(log_undefined - set(dangling))
            if confirmed:
                add(CrossRefIssue(
                    kind="undefined_reference", severity="error",
                    message=(f"LaTeX reported {len(confirmed)} undefined "
                             "reference(s) that static analysis did not find; "
                             "the label is probably declared inside a "
                             "conditional that did not run"),
                    detail={"labels": sorted(confirmed)[:50]},
                ))
            confirmed_cites = sorted(log_uncited - set(cited - analysis.bib_keys))
            if confirmed_cites:
                add(CrossRefIssue(
                    kind="undefined_citation", severity="error",
                    message=(f"LaTeX reported {len(confirmed_cites)} undefined "
                             "citation(s)"),
                    detail={"keys": confirmed_cites[:50]},
                ))
            if log.of("multiply_defined_label") and not duplicates:
                add(CrossRefIssue(
                    kind="duplicate_label", severity="error",
                    message=("LaTeX reported multiply-defined labels that "
                             "static analysis did not find"),
                    detail={"labels": sorted(
                        {d.target for d in log.of("multiply_defined_label")
                         if d.target})[:50]},
                ))
