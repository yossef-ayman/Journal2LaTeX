"""Rendering a document from a saved field mapping.

The operator never edits Word.  They upload the real acceptance letter and the
real invoice, point at the title, the authors, the reference number and the
dates once, and the module remembers those literals.  Generation is then simply:
wherever that literal appears, put this paper's value instead.

Three consequences shaped this implementation:

* **Every occurrence is replaced, not the first.** A reference number appears in
  the body and again next to the bank details; a journal name repeats in the
  header of every section; Word stores text-box content twice, once in the
  ``mc:AlternateContent`` Choice branch and once in the Fallback.  Replacing a
  single occurrence would leave the old value visible somewhere in the output.
* **Longer literals are replaced first.** If one mapped literal contains
  another -- an author list that happens to include the corresponding author --
  applying the longer one first stops the shorter from cutting it in half.
* **A replaced value is never re-scanned.** The rewrite happens through
  :func:`ooxml_bytes.rewrite_spans` on offsets computed once per paragraph, so a
  value that happens to contain another mapped literal cannot cascade.
* **A mapped value is one logical field.** The whole replacement lands in the
  first run the match touched, so an author list Word had scattered over nine
  runs comes back as a single contiguous block in that run's formatting rather
  than being dribbled back across the fragments.

Substitution is done by splicing bytes into the original part, never by
re-serialising the XML -- see :mod:`document_generator.services.ooxml_bytes` for
why that distinction is the difference between a file Word exports and a file
Word calls corrupted.

Placeholders are handled in the same pass.  A template may therefore be mapped,
or use ``{{NAME}}`` markers, or both -- which is what lets the mapping feature
arrive without invalidating any template already in use.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from document_generator.models.schemas import FieldMapping
from document_generator.services.ooxml_bytes import (
    OOXMLEditError,
    Paragraph,
    Span,
    is_text_part,
    parse_part,
    rewrite_spans,
)
from document_generator.services.placeholder_engine import (
    PLACEHOLDER_RE,
    PlaceholderEngineError,
    resolve_value,
)

logger = logging.getLogger("document_generator.mapping_engine")


class MappingEngineError(Exception):
    """Raised when a mapped template cannot be rendered."""


def _prepared(
    mappings: Sequence[FieldMapping], values: Mapping[str, str]
) -> List[Tuple[str, str]]:
    """(literal, replacement) pairs, longest literal first.

    A mapping whose field the value set does not know is dropped rather than
    replaced with a blank: the operator's own text is a better thing to leave in
    the document than an empty gap.
    """
    prepared: List[Tuple[str, str]] = []
    folded = {key.upper(): value for key, value in values.items()}
    for mapping in mappings:
        literal = mapping.text or ""
        if not literal.strip():
            continue
        field = (mapping.field or "").strip().upper()
        if field not in folded:
            logger.warning("Mapped field '%s' has no value; leaving the template text.", field)
            continue
        val = folded[field] or ""
        if "#" in literal:
            import re
            replacement = re.sub(r"#+", val, literal)
        else:
            replacement = val
        prepared.append((literal, replacement))
    prepared.sort(key=lambda pair: len(pair[0]), reverse=True)
    return prepared


def _literal_spans(text: str, prepared: Sequence[Tuple[str, str]]) -> List[Span]:
    """Non-overlapping spans for every occurrence of every mapped literal."""
    spans: List[Span] = []
    claimed: List[Tuple[int, int]] = []

    def free(start: int, end: int) -> bool:
        return all(end <= s or start >= e for s, e in claimed)

    for literal, replacement in prepared:
        start = text.find(literal)
        while start != -1:
            end = start + len(literal)
            if free(start, end):
                spans.append((start, end, replacement))
                claimed.append((start, end))
            start = text.find(literal, end)
    return spans


def _substitute_paragraph(
    paragraph: Paragraph,
    prepared: Sequence[Tuple[str, str]],
    values: Mapping[str, str],
    missing: List[str],
    prev_text: str = "",
) -> int:
    """Apply mapped literals and placeholders to one paragraph."""
    text = paragraph.text()
    if not text:
        return 0

    spans: List[Span] = []
    # Placeholders first: an explicit marker always wins over a literal that
    # happens to overlap it.
    placeholder_ranges: List[Tuple[int, int]] = []
    for match in PLACEHOLDER_RE.finditer(text):
        spans.append((match.start(), match.end(), resolve_value(match.group(1), values, missing)))
        placeholder_ranges.append((match.start(), match.end()))

    for start, end, replacement in _literal_spans(text, prepared):
        if all(end <= s or start >= e for s, e in placeholder_ranges):
            spans.append((start, end, replacement))

    if "##" in text and not spans:
        combined = f"{prev_text} {text}".lower()
        target_val = None
        if "total charge in us dollars" in combined or "total charge in dollars" in combined:
            target_val = values.get("TOTAL_CHARGE_USD") or values.get("FEE") or values.get("TOTAL_CHARGE")
        elif "total charge" in combined or "fees" in combined or "total amount" in combined:
            target_val = values.get("TOTAL_CHARGE") or values.get("TOTAL") or values.get("FEE")
        elif "discount" in combined:
            target_val = values.get("DISCOUNT") or "$0"
        elif "ref" in combined:
            target_val = values.get("REFERENCE_NUMBER") or values.get("REF_NUMBER")
        elif "invoice no" in combined or "invoice number" in combined:
            target_val = values.get("INVOICE_NUMBER") or values.get("REFERENCE_NUMBER")

        if target_val:
            import re
            replacement_text = re.sub(r"#+", target_val, text)
            spans.append((0, len(text), replacement_text))

    if not spans:
        return 0
    return rewrite_spans(paragraph, spans)


def _substitute_part(
    xml_bytes: bytes,
    prepared: Sequence[Tuple[str, str]],
    values: Mapping[str, str],
    missing: List[str],
) -> Tuple[bytes, int]:
    part = parse_part(xml_bytes)
    count = 0
    for idx, paragraph in enumerate(part.paragraphs):
        prev_p = part.paragraphs[idx - 1] if idx > 0 else None
        prev_text = prev_p.text() if prev_p else ""
        count += _substitute_paragraph(paragraph, prepared, values, missing, prev_text=prev_text)
    # `serialize` returns the original bytes when nothing changed, and otherwise
    # splices only the byte ranges of the replaced text: the XML declaration,
    # namespace declarations, attribute order and every unrelated element keep
    # their exact original bytes.
    return part.serialize(), count


def render(
    template_path: Path,
    output_path: Path,
    values: Mapping[str, str],
    mappings: Sequence[FieldMapping] = (),
) -> Dict[str, object]:
    """Write ``template_path`` to ``output_path`` with the mapping applied.

    With an empty mapping this is exactly placeholder substitution, so it is safe
    as the single rendering path for both mapped and placeholder templates.

    Returns a report: how many substitutions were made, which placeholder names
    the template used but nobody supplied, and which mapped literals were not
    found at all -- the last of these is how an operator learns that a replaced
    template no longer matches its saved mapping.
    """
    if not template_path.is_file():
        raise MappingEngineError(f"Template not found: {template_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prepared = _prepared(list(mappings), values)
    missing: List[str] = []
    substitutions = 0
    seen_literals: Dict[str, int] = {literal: 0 for literal, _ in prepared}
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    try:
        with zipfile.ZipFile(template_path) as source:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as target:
                for item in source.infolist():
                    data = source.read(item.filename)
                    if is_text_part(item.filename):
                        # Count before substituting: afterwards the literal is
                        # gone, and the count is what tells the operator a saved
                        # mapping has stopped matching its template.
                        if seen_literals:
                            _count_in_part(data, seen_literals)
                        try:
                            data, count = _substitute_part(data, prepared, values, missing)
                            substitutions += count
                        except OOXMLEditError as exc:
                            raise MappingEngineError(
                                f"Template part {item.filename} is not valid XML: {exc}"
                            ) from exc
                    target.writestr(item, data)
        tmp_path.replace(output_path)
    except zipfile.BadZipFile as exc:
        tmp_path.unlink(missing_ok=True)
        raise MappingEngineError(
            f"Template {template_path.name} is not a readable .docx file."
        ) from exc
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    unmatched = sorted(
        {
            field_of(literal, mappings)
            for literal, count in seen_literals.items()
            if count == 0
        }
    )
    unresolved = sorted(set(missing))
    if unresolved or unmatched:
        logger.info(
            "Rendered %s with %d substitution(s); unsupplied placeholders: %s; "
            "mapped fields not found: %s",
            output_path.name,
            substitutions,
            ", ".join(unresolved) or "none",
            ", ".join(unmatched) or "none",
        )
    return {
        "substitutions": substitutions,
        "unresolved": unresolved,
        "unmatched_fields": unmatched,
    }


def field_of(literal: str, mappings: Iterable[FieldMapping]) -> str:
    """The field a literal belongs to, for reporting."""
    for mapping in mappings:
        if mapping.text == literal:
            return mapping.field
    return literal


def _count_in_part(xml_bytes: bytes, tallies: Dict[str, int]) -> None:
    """Add each literal's occurrences in one XML part to ``tallies``."""
    try:
        part = parse_part(xml_bytes)
    except OOXMLEditError:
        return
    for paragraph in part.paragraphs:
        text = paragraph.text()
        if not text:
            continue
        for literal in tallies:
            if literal in text:
                tallies[literal] += text.count(literal)


__all__ = ["MappingEngineError", "PlaceholderEngineError", "render", "field_of"]
