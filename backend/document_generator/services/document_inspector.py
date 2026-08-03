"""Reads a stored Word document into the pieces the mapping wizard shows.

The operator uploads an ordinary letter or invoice -- a real one, with a real
title, a real reference number, real dates -- and then points at the parts of it
that change from paper to paper.  This module turns the document into that
list of selectable pieces, and offers a first guess for each field so the common
case is a confirmation rather than a hunt.

Two properties matter for the result to be usable:

* **Segments are what Word renders, not what the XML stores.** A paragraph's
  text is reassembled across its runs, so the operator sees "Ref. JSAP055726A"
  as one string even though Word split it into five runs.
* **Duplicates are collapsed.** Word duplicates text-box content across the
  ``mc:AlternateContent`` Choice and Fallback branches, and a header repeats on
  every section.  Showing the same line five times would make the wizard
  unreadable, so identical text is listed once with an occurrence count -- and
  because mapping replaces *every* occurrence of a literal, the copies are all
  still handled.

The suggestions are generic heuristics -- label prefixes, date shapes, reference
shapes -- deliberately not tied to any particular journal's wording, so they keep
working when the operator replaces these templates with different ones.
"""

from __future__ import annotations

import logging
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from document_generator.models.schemas import (
    DocumentSegment,
    FieldSuggestion,
    TemplateInspection,
)
from document_generator.services import document_types, template_fields
from document_generator.services.ooxml_bytes import (
    OOXMLEditError,
    is_text_part,
    parse_part,
)

logger = logging.getLogger("document_generator.document_inspector")

# Shortest text worth offering: single characters and stray punctuation are
# noise in a picker, and mapping them would replace text all over the document.
_MIN_SEGMENT_LENGTH = 2


class DocumentInspectorError(Exception):
    """Raised when a document cannot be inspected."""


def _location(part_name: str) -> str:
    if part_name.startswith("word/header"):
        return "header"
    if part_name.startswith("word/footer"):
        return "footer"
    return "body"


def read_segments(path: Path) -> List[DocumentSegment]:
    """Every distinct line of visible text in a document, in reading order."""
    if not path.is_file():
        raise DocumentInspectorError(f"Document not found: {path}")

    # Body first, then headers and footers, so the wizard reads top to bottom.
    def part_order(name: str) -> Tuple[int, str]:
        return ({"body": 0, "header": 1, "footer": 2}[_location(name)], name)

    segments: List[DocumentSegment] = []
    by_text: Dict[str, DocumentSegment] = {}

    try:
        with zipfile.ZipFile(path) as zf:
            names = sorted((n for n in zf.namelist() if is_text_part(n)), key=part_order)
            for part in names:
                try:
                    parsed = parse_part(zf.read(part))
                except OOXMLEditError as exc:
                    logger.warning("Skipping unreadable part %s: %s", part, exc)
                    continue

                for index, paragraph in enumerate(parsed.paragraphs):
                    text = paragraph.text().strip()
                    if len(text) < _MIN_SEGMENT_LENGTH:
                        continue
                    existing = by_text.get(text)
                    if existing is not None:
                        existing.occurrences += 1
                        continue
                    segment = DocumentSegment(
                        id=f"s{len(segments) + 1}",
                        part=part,
                        location=_location(part),
                        index=index,
                        text=text,
                        in_table=paragraph.in_table,
                    )
                    segments.append(segment)
                    by_text[text] = segment
    except zipfile.BadZipFile as exc:
        raise DocumentInspectorError(
            f"{path.name} is not a readable .docx document."
        ) from exc

    return segments


# --------------------------------------------------------------------------- #
# Suggestions
# --------------------------------------------------------------------------- #

# "Title:", "Paper title -", "Authors :" ... a labelled value is by far the most
# common shape in the letters and invoices these templates are made from.
_LABELS: Tuple[Tuple[str, str], ...] = (
    (r"(?:paper\s+)?title", "TITLE"),
    (r"author(?:s|\(s\))?", "AUTHORS"),
    (r"ref(?:erence)?(?:\s*(?:no|number|#))?", "REFERENCE_NUMBER"),
    (r"manuscript\s*(?:id|no|number)", "REFERENCE_NUMBER"),
    (r"(?:date\s+of\s+)?accept(?:ed|ance)(?:\s+date)?", "ACCEPTANCE_DATE"),
    (r"deadline|due\s+date|payable\s+by|payment\s+deadline", "DEADLINE"),
    (r"(?:name\s+of\s+)?journal", "JOURNAL"),
    (r"editor(?:[-\s]in[-\s]chief)?", "EDITOR"),
)

# A label only counts when it is followed by ":" or "." -- without that rule the
# word "Journal" inside the journal's own name, or "Accepted" in the phrase
# "Accepted Paper", would be read as a label and the suggestion would be
# nonsense.  A second rule, applied at match time, is that the label must be
# capitalised: "Ref." labels a value, "journal." merely ends a sentence.
_LABEL_RES: Tuple[Tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(rf"(?i)(?:^|[\s(\[.,;]|(?<=[a-z]))(?:{pattern})\s*[:.]\s*"), field)
    for pattern, field in _LABELS
)


def _is_label(matched: str) -> bool:
    """Whether a label match reads like a real label rather than prose."""
    for character in matched:
        if character.isalpha():
            return character.isupper()
    return False

# Generic value shapes, used when there is no label to lean on.
_DATE_RE = re.compile(
    r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\s+\d{4}"
    r"|[A-Za-z]{3,9}\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}"
    r"|\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\b"
)
# A reference token: letters then digits, optionally a trailing letter.
_REFERENCE_RE = re.compile(r"\b[A-Z]{2,10}[-_ ]?\d{4,12}[A-Z]?\b")

# Where a labelled value ends: the next label on the same line starts a new
# field, which is what makes "Title: ... Ref. X Email: y" separable.
_NEXT_LABEL_RE = re.compile(
    r"(?i)\s*(?:"
    r"ref(?:erence)?(?:\s*(?:no|number|#))?|author(?:s|\(s\))?|e-?mail|"
    r"title|journal|deadline|due\s+date|accept(?:ed|ance)|editor|tel(?:ephone)?|"
    r"volume|issue|pages?"
    r")\s*[:.]\s*"
)


def _value_after_label(text: str, start: int) -> str:
    """The value that follows a label, stopping at the next label on the line."""
    rest = text[start:]
    following = _NEXT_LABEL_RE.search(rest)
    value = rest[: following.start()] if following else rest
    return value.strip().strip(".,;:")


def suggest_fields(segments: List[DocumentSegment]) -> List[FieldSuggestion]:
    """Best guess at the literal text behind each field.

    At most one suggestion per field -- the wizard is a confirmation step, and a
    list of competing guesses would make it slower than mapping by hand.  A
    labelled value always beats a shape-based guess.
    """
    labelled: Dict[str, FieldSuggestion] = {}
    shaped: Dict[str, FieldSuggestion] = {}

    for segment in segments:
        text = segment.text

        for pattern, field in _LABEL_RES:
            if field in labelled:
                continue
            match = pattern.search(text)
            if not match or not _is_label(match.group(0)):
                continue
            value = _value_after_label(text, match.end())
            if len(value) < _MIN_SEGMENT_LENGTH:
                continue
            labelled[field] = FieldSuggestion(
                field=field,
                text=value,
                segment_id=segment.id,
                occurrences=segment.occurrences,
                reason=f"Follows the label “{match.group(0).strip()}” in the document.",
            )

        if "REFERENCE_NUMBER" not in shaped:
            found = _REFERENCE_RE.search(text)
            if found:
                shaped["REFERENCE_NUMBER"] = FieldSuggestion(
                    field="REFERENCE_NUMBER",
                    text=found.group(0),
                    segment_id=segment.id,
                    occurrences=segment.occurrences,
                    reason="Looks like a manuscript reference number.",
                )
        if "ACCEPTANCE_DATE" not in shaped:
            found = _DATE_RE.search(text)
            if found:
                shaped["ACCEPTANCE_DATE"] = FieldSuggestion(
                    field="ACCEPTANCE_DATE",
                    text=found.group(0),
                    segment_id=segment.id,
                    occurrences=segment.occurrences,
                    reason="Looks like a date.",
                )

    suggestions: List[FieldSuggestion] = []
    for field in (f.key for f in template_fields.list_fields()):
        chosen = labelled.get(field) or shaped.get(field)
        if chosen is None:
            continue
        # A labelled value may still contain the label's own value shape; trim a
        # reference suggestion down to the token itself.
        if field == "REFERENCE_NUMBER":
            token = _REFERENCE_RE.search(chosen.text)
            if token:
                chosen.text = token.group(0)
        if field in {"ACCEPTANCE_DATE", "DEADLINE"}:
            token = _DATE_RE.search(chosen.text)
            if token:
                chosen.text = token.group(0)
        if len(chosen.text) >= _MIN_SEGMENT_LENGTH:
            suggestions.append(chosen)
    return suggestions


def count_occurrences(path: Path, literal: str) -> int:
    """How many paragraphs in the document contain ``literal``."""
    if not literal:
        return 0
    total = 0
    try:
        with zipfile.ZipFile(path) as zf:
            for part in zf.namelist():
                if not is_text_part(part):
                    continue
                try:
                    parsed = parse_part(zf.read(part))
                except OOXMLEditError:
                    continue
                for paragraph in parsed.paragraphs:
                    total += paragraph.text().count(literal)
    except zipfile.BadZipFile:
        return 0
    return total


def inspect(
    path: Path, document_type: str, mapping: Optional[object] = None
) -> TemplateInspection:
    """Everything the wizard needs for one stored template."""
    info = document_types.get_document_type(document_type)
    segments = read_segments(path)
    return TemplateInspection(
        document_type=document_type,
        label=info.label,
        fields=template_fields.list_fields(),
        segments=segments,
        suggestions=suggest_fields(segments),
        mapping=mapping,  # type: ignore[arg-type]
    )
