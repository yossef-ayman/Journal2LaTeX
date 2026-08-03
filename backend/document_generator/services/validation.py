"""Proving a generated document is what the template was.

Two questions are answered here, and they are different questions.

**Is the file valid?**  Word is far stricter when exporting to PDF than when
opening a document: a package that opens without complaint can still fail export
with *"The file appears to be corrupted"*.  LibreOffice is more forgiving than
either, so a conversion succeeding on the server proves nothing about Word on the
operator's machine.  :func:`validate_docx` therefore checks the package the way
Word does — zip integrity, the required parts, every XML part well-formed, the
content types and relationships that name those parts — and a document that fails
is never handed to a PDF converter.

**Is it still the template?**  The promise this module makes is that only the
dynamic values change.  :func:`compare_to_template` checks that structurally:
paragraph, table, row, cell, text-box, header, footer, run and break counts must
match the template exactly, and every part other than the text parts must be
byte-identical.  A drift in any of those is the signature of a document that has
been rebuilt rather than edited — the reflowed spacing and shifted paragraphs an
operator sees — so it is reported rather than discovered by eye.

Nothing here knows anything about a particular journal or template: the template
is whatever the operator uploaded, and it is compared against itself.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from document_generator.services.ooxml_bytes import (
    OOXMLEditError,
    is_text_part,
    parse_part,
)

logger = logging.getLogger("document_generator.validation")

# Parts every .docx must carry for Word to consider the package complete.
_REQUIRED_PARTS = ("[Content_Types].xml", "_rels/.rels", "word/document.xml")

# Structural tallies compared between a template and its output, with the label
# each one carries in the operator-facing report.
_STRUCTURE_LABELS = {
    "paragraphs": "Paragraph count preserved",
    "tables": "Tables preserved",
    "table_rows": "Table rows preserved",
    "table_cells": "Table cells preserved",
    "text_boxes": "Text boxes preserved",
    "runs": "Run formatting preserved",
    "drawings": "Images and shapes preserved",
    "hyperlinks": "Hyperlinks preserved",
}


class ValidationResult:
    """The outcome of validating one generated document."""

    __slots__ = ("path", "valid", "errors", "checks", "fields_replaced", "fields_missing")

    def __init__(self, path: Path) -> None:
        self.path = path
        self.valid = True
        self.errors: List[str] = []
        # Human-readable check name -> passed.  This is the report the operator
        # sees; the order the checks are added is the order they are shown.
        self.checks: Dict[str, bool] = {}
        self.fields_replaced: List[str] = []
        self.fields_missing: List[str] = []

    def record(self, check: str, passed: bool, detail: str = "") -> None:
        self.checks[check] = passed and self.checks.get(check, True)
        if not passed:
            self.valid = False
            self.errors.append(detail or check)

    def as_dict(self) -> Dict[str, object]:
        return {
            "document": self.path.name,
            "valid": self.valid,
            "checks": dict(self.checks),
            "errors": list(self.errors),
            "fields_replaced": list(self.fields_replaced),
            "fields_missing": list(self.fields_missing),
        }

    def summary_lines(self) -> List[str]:
        """The report as ticked lines, which is how it reads in a log or the UI."""
        return [
            f"{'✓' if passed else '✗'} {check}" for check, passed in self.checks.items()
        ]


def _xml_parts(archive: zipfile.ZipFile) -> List[str]:
    return [n for n in archive.namelist() if n.lower().endswith((".xml", ".rels"))]


def validate_docx(path: Path, result: Optional[ValidationResult] = None) -> ValidationResult:
    """Check that a .docx is a package Word will open *and* export.

    Deliberately strict about XML well-formedness across *every* part, not just
    the document body: a header or a footnote part that fails to parse is exactly
    the kind of damage that opens fine and refuses to export.
    """
    result = result or ValidationResult(path)

    if not path.is_file():
        result.record("File written", False, f"{path.name} was not written.")
        return result
    result.record("File written", True)

    try:
        with zipfile.ZipFile(path) as archive:
            broken = archive.testzip()
            if broken is not None:
                result.record(
                    "Package integrity", False, f"The entry {broken} is corrupt."
                )
                return result
            result.record("Package integrity", True)

            names = set(archive.namelist())
            missing = [part for part in _REQUIRED_PARTS if part not in names]
            result.record(
                "Required parts present",
                not missing,
                f"Missing required part(s): {', '.join(missing)}." if missing else "",
            )

            bad: List[str] = []
            for name in _xml_parts(archive):
                try:
                    parse_part(archive.read(name))
                except OOXMLEditError as exc:
                    bad.append(f"{name} ({exc})")
            result.record(
                "XML consistency",
                not bad,
                f"Malformed XML in: {'; '.join(bad)}." if bad else "",
            )

            # Content types and relationships must still name the parts that are
            # actually in the package; a mismatch is what Word calls corruption.
            declared = archive.read("[Content_Types].xml").decode("utf-8", "replace")
            undeclared = [
                name
                for name in names
                if name.endswith(".xml")
                and not name.startswith("_rels/")
                and f'PartName="/{name}"' not in declared
                and f".{name.rsplit('.', 1)[-1]}" not in declared
            ]
            result.record(
                "Content types declared",
                not undeclared,
                f"Undeclared part(s): {', '.join(undeclared)}." if undeclared else "",
            )

            dangling: List[str] = []
            for rels_name in (n for n in names if n.endswith(".rels")):
                base = rels_name.rsplit("_rels/", 1)[0]
                text = archive.read(rels_name).decode("utf-8", "replace")
                for target in _internal_targets(text):
                    resolved = _resolve_target(base, target)
                    if resolved and resolved not in names:
                        dangling.append(f"{rels_name} -> {target}")
            result.record(
                "Relationships intact",
                not dangling,
                f"Broken relationship(s): {', '.join(dangling)}." if dangling else "",
            )
    except zipfile.BadZipFile as exc:
        result.record("Package integrity", False, f"{path.name} is not a .docx: {exc}")
    return result


def _internal_targets(rels_xml: str) -> List[str]:
    """Targets of relationships that point inside the package."""
    import re

    targets: List[str] = []
    for match in re.finditer(
        r'<Relationship\b[^>]*?Target="([^"]+)"([^>]*)>', rels_xml
    ):
        target, rest = match.group(1), match.group(2)
        if 'TargetMode="External"' in rest or "://" in target:
            continue
        targets.append(target)
    return targets


def _resolve_target(base: str, target: str) -> str:
    """Package-relative path a relationship target refers to."""
    if target.startswith("/"):
        return target.lstrip("/")
    path = (base + target).replace("\\", "/")
    parts: List[str] = []
    for piece in path.split("/"):
        if piece in ("", "."):
            continue
        if piece == "..":
            if parts:
                parts.pop()
            continue
        parts.append(piece)
    return "/".join(parts)


def compare_to_template(
    template: Path, generated: Path, result: Optional[ValidationResult] = None
) -> ValidationResult:
    """Check that only the dynamic values differ between template and output."""
    result = result or ValidationResult(generated)
    if not template.is_file() or not generated.is_file():
        result.record("Compared against the template", False, "A file was missing.")
        return result

    try:
        with zipfile.ZipFile(template) as left, zipfile.ZipFile(generated) as right:
            left_names, right_names = left.namelist(), right.namelist()
            result.record(
                "Package layout preserved",
                sorted(left_names) == sorted(right_names),
                "The generated package does not contain the same parts as the "
                "template.",
            )

            # Everything that is not a text part must be byte-identical: styles,
            # numbering, theme, fonts, settings, images, page setup.
            altered = [
                name
                for name in left_names
                if name in right_names
                and not is_text_part(name)
                and left.read(name) != right.read(name)
            ]
            result.record(
                "Formatting preserved",
                not altered,
                f"Non-text part(s) changed: {', '.join(altered)}." if altered else "",
            )

            totals_left: Dict[str, int] = {}
            totals_right: Dict[str, int] = {}
            headers = [0, 0]
            footers = [0, 0]
            for name in left_names:
                if not is_text_part(name) or name not in right_names:
                    continue
                if name.startswith("word/header"):
                    headers[0] += 1
                    headers[1] += 1
                if name.startswith("word/footer"):
                    footers[0] += 1
                    footers[1] += 1
                try:
                    a = parse_part(left.read(name))
                    b = parse_part(right.read(name))
                except OOXMLEditError as exc:
                    result.record("XML consistency", False, f"{name}: {exc}")
                    continue
                for key, value in a.counts.items():
                    totals_left[key] = totals_left.get(key, 0) + value
                for key, value in b.counts.items():
                    totals_right[key] = totals_right.get(key, 0) + value

            for key, label in _STRUCTURE_LABELS.items():
                before, after = totals_left.get(key, 0), totals_right.get(key, 0)
                result.record(
                    label,
                    before == after,
                    f"{label.lower()}: {before} in the template, {after} in the "
                    f"generated document.",
                )
            result.record("Headers preserved", headers[0] == headers[1])
            result.record("Footers preserved", footers[0] == footers[1])
    except zipfile.BadZipFile as exc:
        result.record("Compared against the template", False, str(exc))
    return result


def validate_generated(
    template: Path,
    generated: Path,
    expected_values: Optional[Dict[str, str]] = None,
    original_literals: Optional[Dict[str, str]] = None,
) -> ValidationResult:
    """The full check for one generated document.

    ``expected_values`` maps field name to the value that should now be in the
    document; ``original_literals`` maps the same field names to the template
    text that should have been replaced.  Together they turn "the substitution
    ran" into "the right text is in the file and the template's own text is gone",
    which is the only version of that claim worth reporting.
    """
    result = ValidationResult(generated)
    validate_docx(generated, result)
    if result.valid:
        compare_to_template(template, generated, result)

    if expected_values:
        text = _document_text(generated)
        replaced: List[str] = []
        missing: List[str] = []
        for field, value in expected_values.items():
            value = (value or "").strip()
            if not value:
                continue
            leftover = (original_literals or {}).get(field, "")
            present = _contains(text, value)
            stale = bool(leftover) and leftover != value and _contains(text, leftover)
            if present and not stale:
                replaced.append(field)
            else:
                missing.append(field)
        result.fields_replaced = sorted(replaced)
        result.fields_missing = sorted(missing)
        result.record(
            "Dynamic fields replaced correctly",
            not missing,
            f"Not filled in correctly: {', '.join(sorted(missing))}."
            if missing
            else "",
        )
    return result


def _contains(text: str, value: str) -> bool:
    """Whether a field's value is present in a document's text.

    Compared line by line rather than as one string, because a multi-line value
    is written into the document as a line *break* inside the run -- which is the
    right thing for the layout and carries no character of its own -- so the
    newline the caller passed in is not a character the document contains.  Each
    line is matched with its whitespace collapsed, since Word is free to split a
    line across runs with different spacing without changing what it says.
    """
    import re as _re

    haystack = _re.sub(r"\s+", " ", text)
    lines = [_re.sub(r"\s+", " ", line).strip() for line in value.split("\n")]
    return all(line in haystack for line in lines if line)


def _document_text(path: Path) -> str:
    """All visible text of a document, for the field-replacement check."""
    chunks: List[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if not is_text_part(name):
                    continue
                try:
                    part = parse_part(archive.read(name))
                except OOXMLEditError:
                    continue
                chunks.extend(paragraph.text() for paragraph in part.paragraphs)
    except zipfile.BadZipFile:
        return ""
    return "\n".join(chunks)


__all__ = [
    "ValidationResult",
    "compare_to_template",
    "validate_docx",
    "validate_generated",
]
