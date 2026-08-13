"""Validation before delivery: one report, run before the project is returned.

Every engine in this package answers a narrow question well.  This module asks
the only question the person downloading the project actually has -- *is this
finished?* -- by running all of them against the built artefacts and merging
their findings into a single report with a single verdict.

The design rule here is that validation **observes and never repairs**.  A
validator that fixes what it finds cannot be trusted to report accurately, and
a pipeline whose last stage silently rewrites the document is one whose output
nobody can reason about.  Everything below reads; nothing writes to the
project.

The verdict is deliberately three-valued.  ``pass`` means nothing was found.
``warn`` means the document is deliverable but imperfect -- an uncited
reference, an overfull line, a large image.  ``fail`` means the PDF a reader
opens contains something visibly wrong: a ``??`` where a figure number should
be, a missing image, a reference to nothing.  Collapsing the last two into one
would make the report either alarmist or useless.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.engines.citation_engine import CitationEngine, CitationAnalysis
from app.engines.crossref_engine import CrossReferenceEngine, CrossRefAnalysis
from app.engines.journal_rules import JournalRules, JournalRulesResolver
from app.engines.latex_log import LogReport, parse_log


#: Image files bigger than this are worth reporting: they bloat the project
#: archive and, in a converted manuscript, almost always mean a screenshot was
#: pasted at full resolution rather than a figure exported at print size.
_LARGE_IMAGE_BYTES = 4 * 1024 * 1024

#: Extensions pdflatex can include directly.  A file with any other extension
#: in the media folder will not compile if it is referenced.
_PDFLATEX_IMAGE_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".eps", ".ps"}

#: Magic numbers, so a file's *actual* type can be compared against the
#: extension it was given.  Word documents routinely carry an image saved as
#: ``.jpg`` that is really a PNG, or an EMF renamed to ``.png``; LaTeX believes
#: the extension and fails on the content.
_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"%PDF-", ".pdf"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"BM", ".bmp"),
    (b"II*\x00", ".tif"),
    (b"MM\x00*", ".tif"),
    (b"%!PS", ".eps"),
)


@dataclass
class Finding:
    """One thing worth telling the user before they download the project."""

    area: str          # citations | references | figures | tables | equations
                       # | labels | assets | compilation | files | archive
    kind: str
    severity: str      # error | warning | info
    message: str
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        out = {"area": self.area, "kind": self.kind,
               "severity": self.severity, "message": self.message}
        if self.detail:
            out["detail"] = self.detail
        return out


@dataclass
class ValidationReport:
    findings: List[Finding] = field(default_factory=list)
    checks: Dict[str, str] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    rules: Optional[Dict[str, Any]] = None

    @property
    def verdict(self) -> str:
        if any(f.severity == "error" for f in self.findings):
            return "fail"
        if any(f.severity == "warning" for f in self.findings):
            return "warn"
        return "pass"

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)
        # A check is only as good as its worst finding, and severity only ever
        # escalates: a later passing sub-check must not clear an earlier
        # failure in the same area.
        rank = {"pass": 0, "warn": 1, "fail": 2}
        current = self.checks.get(finding.area, "pass")
        new = {"error": "fail", "warning": "warn"}.get(finding.severity, "pass")
        if rank[new] > rank[current]:
            self.checks[finding.area] = new

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "checks": dict(self.checks),
            "counts": {
                "total": len(self.findings),
                "errors": sum(1 for f in self.findings if f.severity == "error"),
                "warnings": sum(1 for f in self.findings
                                if f.severity == "warning"),
            },
            "stats": self.stats,
            "journal_rules": self.rules,
            "findings": [f.to_dict() for f in self.findings],
        }


class DeliveryValidator:
    """Runs every check and produces the report returned with the project."""

    #: Areas reported on, always present in ``checks`` so the report has a
    #: fixed shape whether or not a given area had anything to say.
    AREAS = ("citations", "references", "figures", "tables", "equations",
             "labels", "assets", "compilation", "files", "archive")

    def __init__(self,
                 citation_engine: Optional[CitationEngine] = None,
                 crossref_engine: Optional[CrossReferenceEngine] = None,
                 rules_resolver: Optional[JournalRulesResolver] = None) -> None:
        self.citations = citation_engine or CitationEngine()
        self.crossrefs = crossref_engine or CrossReferenceEngine()
        self.rules_resolver = rules_resolver or JournalRulesResolver()

    # -- entry point --------------------------------------------------------- #

    def validate(self, rendered_dir: Path,
                 doc_model: Any = None,
                 log_path: Optional[Path] = None,
                 pdf_path: Optional[Path] = None,
                 zip_path: Optional[Path] = None,
                 rules: Optional[JournalRules] = None,
                 entry_file: str = "main.tex") -> ValidationReport:
        """Validate a built project.

        Every argument beyond ``rendered_dir`` is optional, and each missing
        one narrows what can be checked rather than preventing the check from
        running.  A validator that refuses to run without a complete set of
        inputs is one that never runs at the moment it is most needed -- after
        a partial failure.
        """
        report = ValidationReport()
        report.checks = {area: "pass" for area in self.AREAS}
        rendered_dir = Path(rendered_dir)

        if rules is None:
            rules = self.rules_resolver.for_workspace(rendered_dir)
        report.rules = rules.to_dict()

        tex_path = rendered_dir / entry_file
        if not tex_path.is_file():
            # Fall back to the conventional name before giving up: a project
            # whose template.json disagrees with what was actually written is
            # a configuration fault, worth reporting, not a reason to abandon
            # every other check.
            fallback = rendered_dir / "main.tex"
            if fallback.is_file() and fallback != tex_path:
                report.add(Finding(
                    area="files", kind="entry_file_mismatch", severity="warning",
                    message=(f"the template names '{entry_file}' as its entry "
                             "file but the project was written as 'main.tex'"),
                ))
                tex_path = fallback

        log = parse_log(log_path) if log_path else LogReport(
            parsed=False, parse_note="no compilation log was provided")

        self._check_files(report, rendered_dir, tex_path, pdf_path)
        self._check_compilation(report, log)
        crossref = self._check_crossrefs(report, tex_path, rules, log, doc_model)
        citation = self._check_citations(report, doc_model, tex_path, rules)
        self._check_assets(report, rendered_dir, tex_path)
        self._check_objects(report, doc_model, crossref)
        if zip_path:
            self._check_archive(report, zip_path, rendered_dir, tex_path.stem)

        report.stats.update({
            "log": log.summary(),
            "crossref": crossref.to_dict()["counts"] if crossref else {},
            "citations": (citation.to_dict()["counts"] if citation else {}),
        })
        return report

    # -- files --------------------------------------------------------------- #

    def _check_files(self, report: ValidationReport, rendered_dir: Path,
                     tex_path: Path, pdf_path: Optional[Path]) -> None:
        if not rendered_dir.is_dir():
            report.add(Finding(
                area="files", kind="missing_project", severity="error",
                message="the rendered LaTeX project directory does not exist"))
            return
        if not tex_path.is_file():
            report.add(Finding(
                area="files", kind="missing_entry_file", severity="error",
                message="the project has no LaTeX entry file, so it cannot be "
                        "compiled by whoever downloads it"))
        if pdf_path is not None and not Path(pdf_path).is_file():
            report.add(Finding(
                area="files", kind="missing_pdf", severity="error",
                message="compilation produced no PDF"))

        # A reference to a file that is not in the project is the single most
        # common reason a downloaded archive fails to build on someone else's
        # machine, and it is invisible here because the file exists in the
        # TeX installation used to compile it.
        if tex_path.is_file():
            try:
                text = tex_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return
            import re
            for m in re.finditer(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}",
                                 text):
                target = m.group(1).strip()
                if not target or target.startswith("\\"):
                    continue
                if not self._image_exists(rendered_dir, target):
                    report.add(Finding(
                        area="assets", kind="missing_image", severity="error",
                        message=(f"the document includes '{target}', which is "
                                 "not present in the project"),
                        detail={"path": target}))

    @staticmethod
    def _image_exists(rendered_dir: Path, target: str) -> bool:
        """Whether an ``\\includegraphics`` target resolves inside the project.

        LaTeX resolves an extensionless target against a list of known
        extensions, so the check has to do the same or it reports every
        correctly written inclusion as missing.
        """
        candidate = rendered_dir / target
        if candidate.is_file():
            return True
        if candidate.suffix:
            return False
        return any((rendered_dir / (target + suffix)).is_file()
                   for suffix in _PDFLATEX_IMAGE_SUFFIXES)

    # -- compilation --------------------------------------------------------- #

    def _check_compilation(self, report: ValidationReport,
                           log: LogReport) -> None:
        if not log.parsed:
            report.add(Finding(
                area="compilation", kind="log_unavailable", severity="warning",
                message=(f"the compilation log could not be read "
                         f"({log.parse_note}), so warnings could not be checked")))
            return
        for diagnostic in log.errors:
            if diagnostic.category in ("undefined_reference",
                                       "undefined_citation",
                                       "multiply_defined_label"):
                continue  # reported in their own areas, with more context
            report.add(Finding(
                area="compilation", kind=diagnostic.category, severity="error",
                message=diagnostic.message,
                detail={k: v for k, v in diagnostic.to_dict().items()
                        if k not in ("message", "severity")}))

        overfull = log.overfull
        if overfull:
            worst = log.worst_overflow_pt()
            # A hairline overflow is invisible in print; a wide one is ink in
            # the margin.  Reporting them identically trains the reader to
            # ignore the whole category, so the threshold is stated rather
            # than hidden: one printer's point is about a third of a
            # millimetre, and 5pt is where protrusion becomes visible.
            report.add(Finding(
                area="compilation", kind="overfull_boxes",
                severity="warning" if worst >= 5.0 else "info",
                message=(f"{len(overfull)} overfull box"
                         f"{'es' if len(overfull) > 1 else ''}, the worst "
                         f"protruding {worst:.1f}pt beyond the text block"),
                detail={"worst_pt": round(worst, 2), "count": len(overfull),
                        "lines": [d.source_line for d in overfull[:20]
                                  if d.source_line]}))
        if log.underfull:
            report.add(Finding(
                area="compilation", kind="underfull_boxes", severity="info",
                message=(f"{len(log.underfull)} underfull box"
                         f"{'es' if len(log.underfull) > 1 else ''} "
                         "(stretched spacing, no ink outside the text block)"),
                detail={"count": len(log.underfull)}))
        if log.float_problems:
            report.add(Finding(
                area="figures", kind="float_problem", severity="warning",
                message=(f"{len(log.float_problems)} float placement problem"
                         f"{'s' if len(log.float_problems) > 1 else ''} "
                         "reported by LaTeX"),
                detail={"messages": [d.message for d in log.float_problems[:10]]}))
        missing_chars = log.of("missing_character")
        if missing_chars:
            report.add(Finding(
                area="compilation", kind="missing_characters", severity="warning",
                message=(f"{len(missing_chars)} character"
                         f"{'s are' if len(missing_chars) > 1 else ' is'} not "
                         "available in the document's fonts and will not appear "
                         "in the PDF"),
                detail={"characters": [d.target for d in missing_chars[:20]]}))

    # -- cross references ----------------------------------------------------- #

    def _check_crossrefs(self, report: ValidationReport, tex_path: Path,
                         rules: JournalRules, log: LogReport,
                         doc_model: Any) -> Optional[CrossRefAnalysis]:
        if not tex_path.is_file():
            return None
        expected = self._expected_counts(doc_model)
        analysis = self.crossrefs.analyse(tex_path, rules, log, expected)
        for issue in analysis.issues:
            area = {"undefined_citation": "citations",
                    "unlabelled_object": "labels",
                    "unreferenced_object": "references"}.get(issue.kind, "labels")
            report.add(Finding(area=area, kind=issue.kind,
                               severity=issue.severity, message=issue.message,
                               detail=issue.detail))
        return analysis

    def _check_citations(self, report: ValidationReport, doc_model: Any,
                         tex_path: Path,
                         rules: JournalRules) -> Optional[CitationAnalysis]:
        references = list(getattr(doc_model, "references", []) or [])
        if not references:
            if doc_model is not None:
                report.add(Finding(
                    area="citations", kind="no_bibliography", severity="warning",
                    message="no reference list was extracted from the manuscript"))
            return None
        try:
            body = tex_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        analysis = self.citations.analyse(references, body, rules)
        for issue in analysis.issues:
            # Citation issues found against the rendered LaTeX are reported at
            # one level below their standalone severity when the LaTeX already
            # carries resolved \cite commands: at that point an unmatched
            # bracket in the text is a leftover, not a broken link, and the
            # compiler's own undefined-citation check is authoritative.
            report.add(Finding(area="citations", kind=issue.kind,
                               severity=issue.severity, message=issue.message,
                               detail=issue.detail))
        return analysis

    @staticmethod
    def _expected_counts(doc_model: Any) -> Dict[str, int]:
        """How many labellable objects the parsed document contains."""
        counts = {"figure": 0, "table": 0, "equation": 0}
        for section in getattr(doc_model, "sections", []) or []:
            for block in getattr(section, "blocks", []) or []:
                kind = getattr(getattr(block, "type", None), "value", "")
                if kind in counts:
                    # An equation image is a picture of an equation, not a
                    # figure, and numbering it as one would produce a figure
                    # list full of formulae.
                    if kind == "figure" and (block.content or {}).get("is_equation"):
                        continue
                    counts[kind] += 1
        return {k: v for k, v in counts.items() if v}

    def _check_objects(self, report: ValidationReport, doc_model: Any,
                       crossref: Optional[CrossRefAnalysis]) -> None:
        counts = self._expected_counts(doc_model)
        report.stats["objects"] = counts
        for kind, area in (("figure", "figures"), ("table", "tables"),
                           ("equation", "equations")):
            if counts.get(kind):
                report.checks.setdefault(area, "pass")

    # -- assets ---------------------------------------------------------------#

    def _check_assets(self, report: ValidationReport, rendered_dir: Path,
                      tex_path: Path) -> None:
        media_dir = rendered_dir / "media"
        if not media_dir.is_dir():
            return
        files = sorted(p for p in media_dir.rglob("*") if p.is_file())
        report.stats["media_files"] = len(files)
        if not files:
            return

        try:
            body = tex_path.read_text(encoding="utf-8", errors="replace") \
                if tex_path.is_file() else ""
        except OSError:
            body = ""

        digests: Dict[str, List[str]] = {}
        for path in files:
            rel = path.relative_to(rendered_dir).as_posix()
            try:
                data = path.read_bytes()
            except OSError:
                report.add(Finding(
                    area="assets", kind="unreadable_media", severity="error",
                    message=f"'{rel}' could not be read", detail={"path": rel}))
                continue

            if not data:
                report.add(Finding(
                    area="assets", kind="empty_media", severity="error",
                    message=f"'{rel}' is empty and will not typeset",
                    detail={"path": rel}))
                continue

            digests.setdefault(hashlib.sha256(data).hexdigest(), []).append(rel)

            if len(data) > _LARGE_IMAGE_BYTES:
                report.add(Finding(
                    area="assets", kind="large_media", severity="warning",
                    message=(f"'{rel}' is {len(data) / 1048576:.1f} MB, which "
                             "will slow compilation and bloat the archive"),
                    detail={"path": rel, "bytes": len(data)}))

            actual = next((suffix for magic, suffix in _MAGIC
                           if data.startswith(magic)), None)
            declared = path.suffix.lower()
            if actual and declared not in (actual, ".jpeg" if actual == ".jpg" else actual):
                report.add(Finding(
                    area="assets", kind="wrong_extension", severity="warning",
                    message=(f"'{rel}' is named '{declared}' but its content is "
                             f"{actual[1:].upper()}; LaTeX trusts the extension "
                             "and will fail to include it"),
                    detail={"path": rel, "declared": declared, "actual": actual}))
            elif not actual and declared not in _PDFLATEX_IMAGE_SUFFIXES:
                report.add(Finding(
                    area="assets", kind="unsupported_media", severity="warning",
                    message=(f"'{rel}' has an extension pdflatex cannot include "
                             "directly"),
                    detail={"path": rel, "suffix": declared}))

            if body and rel not in body and path.name not in body:
                report.add(Finding(
                    area="assets", kind="unused_media", severity="info",
                    message=f"'{rel}' is in the project but never included",
                    detail={"path": rel}))

        for digest, paths in digests.items():
            if len(paths) > 1:
                report.add(Finding(
                    area="assets", kind="duplicate_media", severity="info",
                    message=(f"{len(paths)} media files are byte-identical: "
                             + ", ".join(paths[:5])),
                    detail={"paths": paths[:20]}))

    # -- archive ---------------------------------------------------------------#

    def _check_archive(self, report: ValidationReport, zip_path: Path,
                       rendered_dir: Path, tex_stem: str = "main") -> None:
        """The archive must be readable, safe and complete.

        Complete is the part a naive check misses: an archive that opens
        cleanly but is missing the class file the document needs will fail on
        the machine of whoever downloads it, and will do so with an error that
        points at LaTeX rather than at us.
        """
        path = Path(zip_path)
        if not path.is_file():
            report.add(Finding(
                area="archive", kind="missing_archive", severity="error",
                message="the project archive was not produced"))
            return
        try:
            with zipfile.ZipFile(path) as zf:
                bad = zf.testzip()
                if bad is not None:
                    report.add(Finding(
                        area="archive", kind="corrupt_archive", severity="error",
                        message=f"the archive is corrupt at '{bad}'"))
                    return
                names = zf.namelist()
        except (zipfile.BadZipFile, OSError) as exc:
            report.add(Finding(
                area="archive", kind="unreadable_archive", severity="error",
                message=f"the project archive could not be read ({exc})"))
            return

        report.stats["archive_entries"] = len(names)
        escaping = [n for n in names
                    if n.startswith("/") or ".." in Path(n).parts]
        if escaping:
            report.add(Finding(
                area="archive", kind="unsafe_paths", severity="error",
                message=(f"{len(escaping)} archive entries would extract "
                         "outside the project directory"),
                detail={"entries": escaping[:20]}))

        if not any(n.endswith(".tex") for n in names):
            report.add(Finding(
                area="archive", kind="no_source_in_archive", severity="error",
                message="the archive contains no LaTeX source"))

        # Everything the project directory holds that the archive does not.
        if rendered_dir.is_dir():
            packed = {Path(n).as_posix().lstrip("./") for n in names}
            missing = []
            for item in rendered_dir.rglob("*"):
                if not item.is_file():
                    continue
                rel = item.relative_to(rendered_dir).as_posix()
                if item.suffix.lower() in (".aux", ".log", ".out", ".toc",
                                           ".synctex", ".gz", ".fls",
                                           ".fdb_latexmk", ".bbl", ".blg"):
                    continue
                # The compiled PDF of the entry file is a build product, not a
                # source file; a project archive that omits it is correct.
                # Other PDFs are figures and must be present.
                if item.suffix.lower() == ".pdf" and item.stem == tex_stem:
                    continue
                if rel not in packed:
                    missing.append(rel)
            if missing:
                report.add(Finding(
                    area="archive", kind="incomplete_archive", severity="warning",
                    message=(f"{len(missing)} project file"
                             f"{'s are' if len(missing) > 1 else ' is'} absent "
                             "from the archive"),
                    detail={"files": sorted(missing)[:30]}))


def write_report(report: ValidationReport, destination: Path) -> Path:
    """Write the report beside the project's other reports."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report.to_dict(), indent=2),
                           encoding="utf-8")
    return destination
