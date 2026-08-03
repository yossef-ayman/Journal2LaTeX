"""Title and author extraction for uploaded papers.

This module deliberately contains no parsing logic of its own.  The converter
already has a thoroughly exercised Word analyzer, and a second implementation
would drift from it and start producing letters whose titles disagree with the
LaTeX output.  So this is a *read-only adapter*: it calls
``DocumentAnalyzer.analyze_document`` and keeps only the two fields the generator
needs.

The coupling is one-directional and defensive.  The converter knows nothing about
this module; the import happens inside the function so a converter-side import
error degrades one paper's metadata instead of preventing the module from loading,
and every failure path falls back to the file name so a batch always completes.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Tuple

from document_generator.services import author_names

logger = logging.getLogger("document_generator.metadata_extractor")


def title_from_filename(path: Path) -> str:
    """Human-readable fallback title derived from the file name.

    Used when a paper declares no detectable title.  Underscores and hyphens
    become spaces and any leading numbering is dropped, which turns
    ``03_final-draft_smith.docx`` into something an operator recognises in the
    generated letter rather than a blank line.
    """
    stem = path.stem
    stem = re.sub(r"^[\s\d._-]+", "", stem)
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s{2,}", " ", stem).strip()
    return stem or path.stem


def _clean_title(raw: str) -> str:
    """One logical title, however many lines Word wrapped it over.

    A title broken across lines in the manuscript is still a single field in a
    letter, so the line breaks are collapsed to spaces rather than carried into
    the generated document, where they would force the template's own layout to
    reflow.
    """
    title = re.sub(r"\s+", " ", (raw or "").replace("\n", " ")).strip()
    # Trailing footnote and corresponding-author markers are not part of a title.
    return re.sub(r"[\s*†‡§¶#]+$", "", title).strip()


def extract(docx_path: Path, job_id: str) -> Tuple[str, List[str], List[str]]:
    """Return ``(title, authors, warnings)`` for one paper.

    Never raises: a paper the analyzer cannot read still gets a name and a
    warning, because failing an entire twenty-paper batch over one malformed
    file would be the wrong trade for an operator waiting on the output.
    """
    warnings: List[str] = []
    title = ""
    authors: List[str] = []

    try:
        # Imported here, not at module scope: see the module docstring.
        from app.services.document_analyzer import DocumentAnalyzer

        model, _diagnostics = DocumentAnalyzer().analyze_document(docx_path, job_id)
        title = _clean_title(model.title or "")
        # The analyzer reports the author *block*, which in most real papers also
        # carries affiliations, superscript markers and email addresses. Only the
        # names belong in a letter, so the block is filtered on name shape.
        authors, dropped = author_names.clean_authors(
            [a.name for a in (model.authors or [])]
        )
        if dropped and not authors:
            warnings.append(
                f"No author names could be separated from the affiliations in "
                f"{docx_path.name}."
            )
        elif dropped:
            logger.info(
                "Discarded %d non-name line(s) from the author block of %s: %s",
                len(dropped),
                docx_path.name,
                "; ".join(dropped[:5]),
            )
    except Exception as exc:  # noqa: BLE001 - any analyzer failure is non-fatal
        logger.warning(
            "Metadata extraction failed for %s (%s); falling back to the file name.",
            docx_path.name,
            exc,
        )
        warnings.append(
            f"Could not read the document structure of {docx_path.name}; "
            "the file name was used as the title."
        )

    if not title:
        title = title_from_filename(docx_path)
        if not warnings:
            warnings.append(
                f"No title detected in {docx_path.name}; the file name was used."
            )
    if not authors:
        warnings.append(f"No authors detected in {docx_path.name}.")

    return title, authors, warnings


def format_authors(authors: List[str]) -> str:
    """Render an author list the way a letter reads it.

    Two names are joined with "and", more with commas and a final "and", which is
    what a template author expects from ``{{AUTHORS}}`` without having to
    post-process anything.
    """
    names = [a for a in authors if a]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f" and {names[-1]}"
