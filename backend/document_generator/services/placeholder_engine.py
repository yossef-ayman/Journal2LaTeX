"""Placeholder substitution inside Word documents.

The engine edits the document's OOXML directly rather than going through a
document-object library.  That is a deliberate choice about fidelity: the only
bytes that change are the text nodes holding a placeholder, so styles, numbering,
section properties, headers, footers, tables, images, fonts and page setup all
survive exactly as the operator designed them in Word.  Rebuilding a document
through a library, by contrast, silently normalises parts of it.

Two Word behaviours the substitution has to cope with:

* **Split placeholders.** Word freely breaks a paragraph into runs at edit
  boundaries and spell-check marks, so ``{{TITLE}}`` is very often stored as
  ``{{TIT`` + ``LE}}`` across two runs, or with the braces in runs of their own.
  Matching therefore happens on the paragraph's concatenated text and the
  replacement is written back across the runs the match actually spanned.
* **Placeholders outside the body.** Reference numbers and dates commonly sit in
  a header or footer, and invoice notes in a footnote or a text box. Every text
  part of the package is processed, not just ``word/document.xml``.

The run-splitting machinery itself lives in
:mod:`document_generator.services.ooxml_bytes` and is shared with the mapping
engine, so a fix to whitespace or line-break handling benefits both engines
instead of drifting between them.  That module also explains why substitution
splices bytes rather than re-serialising the XML: a re-serialised part is what
made Word report a corrupt file on PDF export.
"""

from __future__ import annotations

import logging
import re
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Tuple

from .ooxml_bytes import (
    OOXMLEditError,
    Paragraph,
    Span,
    is_text_part as _is_text_part,
    parse_part as _parse_part,
    rewrite_spans as _rewrite_spans,
)

logger = logging.getLogger("document_generator.placeholder_engine")

# ``{{NAME}}`` with optional inner whitespace.  Names are restricted to word
# characters and dots so an ordinary brace in the template's prose (a LaTeX
# snippet, a code sample) is never mistaken for a placeholder.
PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")


class PlaceholderEngineError(Exception):
    """Raised when a template cannot be rendered."""


def _resolve(name: str, values: Mapping[str, str], missing: List[str]) -> str:
    """Value for one placeholder name.

    Lookup is case-insensitive because operators type ``{{Title}}`` as readily as
    ``{{TITLE}}``, and a template that silently failed on the wrong case would be
    a maddening thing to debug.  An unknown placeholder resolves to an empty
    string -- leaving ``{{FOO}}`` visible in a letter that goes to an author is
    worse than leaving a blank -- and is reported to the caller.
    """
    for key in (name, name.upper(), name.lower()):
        if key in values:
            return values[key] or ""
    folded = {k.upper(): v for k, v in values.items()}
    if name.upper() in folded:
        return folded[name.upper()] or ""
    missing.append(name)
    return ""


# Public alias: the mapping engine resolves placeholder names through exactly
# the same rules, and importing a private name across modules invites drift.
resolve_value = _resolve


def _substitute_paragraph(
    paragraph: Paragraph, values: Mapping[str, str], missing: List[str]
) -> int:
    """Substitute every placeholder in one paragraph. Returns the count."""
    full = paragraph.text()
    if "{{" not in full:
        return 0

    matches = list(PLACEHOLDER_RE.finditer(full))
    if not matches:
        return 0

    spans: List[Span] = [
        (m.start(), m.end(), _resolve(m.group(1), values, missing)) for m in matches
    ]
    _rewrite_spans(paragraph, spans)
    return len(matches)


def _substitute_part(
    xml_bytes: bytes, values: Mapping[str, str], missing: List[str]
) -> Tuple[bytes, int]:
    """Substitute placeholders throughout one XML part."""
    part = _parse_part(xml_bytes)
    count = 0
    for paragraph in part.paragraphs:
        count += _substitute_paragraph(paragraph, values, missing)
    # Unchanged parts come back as their original bytes; changed ones differ only
    # in the byte ranges of the substituted text.
    return part.serialize(), count


def render_template(
    template_path: Path,
    output_path: Path,
    values: Mapping[str, str],
) -> Dict[str, object]:
    """Write ``template_path`` to ``output_path`` with placeholders substituted.

    Returns a small report: how many substitutions were made and which
    placeholder names the template used but the value set did not supply.  The
    caller surfaces those as warnings so a template referring to a field nobody
    fills is noticed on the first batch instead of after a hundred letters have
    gone out.
    """
    if not template_path.is_file():
        raise PlaceholderEngineError(f"Template not found: {template_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    missing: List[str] = []
    substitutions = 0
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    try:
        with zipfile.ZipFile(template_path) as source:
            # Preserve the original compression settings per entry so the output
            # remains a well-formed, Word-friendly package.
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as target:
                for item in source.infolist():
                    data = source.read(item.filename)
                    if _is_text_part(item.filename):
                        try:
                            data, count = _substitute_part(data, values, missing)
                            substitutions += count
                        except OOXMLEditError as exc:
                            raise PlaceholderEngineError(
                                f"Template part {item.filename} is not valid XML: {exc}"
                            ) from exc
                    target.writestr(item, data)
        tmp_path.replace(output_path)
    except zipfile.BadZipFile as exc:
        tmp_path.unlink(missing_ok=True)
        raise PlaceholderEngineError(
            f"Template {template_path.name} is not a readable .docx file."
        ) from exc
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    unresolved = sorted(set(missing))
    if unresolved:
        logger.info(
            "Rendered %s with %d substitutions; unsupplied placeholders: %s",
            output_path.name,
            substitutions,
            ", ".join(unresolved),
        )
    return {"substitutions": substitutions, "unresolved": unresolved}


def discover_placeholders(template_path: Path) -> List[str]:
    """Every placeholder name a template uses, sorted and de-duplicated.

    Read from the concatenated paragraph text, so placeholders Word has split
    across runs are found too -- which is most of them in a real template.
    """
    names: set[str] = set()
    try:
        with zipfile.ZipFile(template_path) as zf:
            for item in zf.infolist():
                if not _is_text_part(item.filename):
                    continue
                try:
                    part = _parse_part(zf.read(item.filename))
                except OOXMLEditError:
                    continue
                for paragraph in part.paragraphs:
                    names.update(
                        m.group(1)
                        for m in PLACEHOLDER_RE.finditer(paragraph.text())
                    )
    except zipfile.BadZipFile as exc:
        raise PlaceholderEngineError(
            f"{template_path.name} is not a readable .docx file."
        ) from exc
    return sorted(names)


def copy_without_substitution(template_path: Path, output_path: Path) -> None:
    """Straight copy, used when a document type needs no substitution."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template_path, output_path)


def iter_known_placeholders(values: Mapping[str, str]) -> Iterable[str]:
    """Placeholder names a value set can satisfy (for UI hints)."""
    return sorted(values.keys())
