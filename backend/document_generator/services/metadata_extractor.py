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


def extract_pdf_metadata(pdf_path: Path) -> Tuple[str, List[str], List[str]]:
    """Extract (title, authors, warnings) from a PDF paper using font-size visual layout analysis."""
    warnings: List[str] = []
    title = ""
    authors: List[str] = []

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)

        if len(doc) == 0:
            doc.close()
            return title_from_filename(pdf_path), [], ["PDF file is empty."]

        journal_regex = re.compile(
            r"^(journal|international journal|ieee|nature|sciencedirect|elsevier|springer|mdpi|volume|vol\.|issn|doi:|http|www\.|page\s+\d|research article|original article|review article)",
            re.IGNORECASE,
        )

        # 1. Inspect PDF metadata title, but IGNORE if it looks like a journal name or generic string
        meta = doc.metadata or {}
        raw_title = (meta.get("title") or "").strip()
        raw_author = (meta.get("author") or "").strip()

        if (
            raw_title
            and len(raw_title) > 5
            and not raw_title.lower().startswith(
                ("untitled", "microsoft word", "latex", "layout", "print", "document", "powerpoint")
            )
            and not journal_regex.search(raw_title)
        ):
            title = _clean_title(raw_title)

        # 2. Page 1 font-size visual layout analysis
        page1 = doc[0]
        page_dict = page1.get_text("dict")

        lines_with_sizes: List[Tuple[float, str]] = []
        for block in page_dict.get("blocks", []):
            if block.get("type") == 0:  # text block
                for line in block.get("lines", []):
                    line_text = ""
                    max_size = 0.0
                    for span in line.get("spans", []):
                        txt = span.get("text", "").strip()
                        if txt:
                            line_text += (" " + txt if line_text else txt)
                            if span.get("size", 0) > max_size:
                                max_size = span.get("size", 0)
                    line_text = line_text.strip()
                    if line_text:
                        lines_with_sizes.append((max_size, line_text))

        # Filter out obvious journal headers and metadata lines from title search
        candidate_title_lines = []
        for size, text in lines_with_sizes:
            lower = text.lower()
            if journal_regex.search(text):
                continue
            if any(kw in lower for kw in ["doi.org", "http://", "https://", "issn ", "isbn "]):
                continue
            if len(text) < 3 or text.isdigit():
                continue
            candidate_title_lines.append((size, text))

        # Find maximum font size among candidate lines
        if not title and candidate_title_lines:
            max_size = max(s for s, _ in candidate_title_lines[:12])
            # Collect lines with font size within 1.5pt of max_size
            title_parts = []
            for size, text in candidate_title_lines[:12]:
                if size >= max_size - 1.5:
                    title_parts.append(text)
                elif title_parts:
                    # Title lines are contiguous; stop once font size drops
                    break

            if title_parts:
                title = _clean_title(" ".join(title_parts))

        # 3. Authors extraction
        if raw_author and not journal_regex.search(raw_author):
            authors, _ = author_names.clean_authors([raw_author])

        if not authors and lines_with_sizes:
            # Find index where title ends, then inspect subsequent lines for author names
            title_found = False
            author_candidates = []
            for size, text in lines_with_sizes[:25]:
                lower = text.lower()
                if any(kw in lower for kw in ["abstract", "keywords", "1. introduction", "introduction"]):
                    break
                if title and _clean_title(text) in title:
                    title_found = True
                    continue
                if title_found or not title:
                    if journal_regex.search(text):
                        continue
                    cleaned, _ = author_names.clean_authors([text])
                    if cleaned:
                        author_candidates.extend(cleaned)
                        if len(author_candidates) >= 1:
                            if any(char in text for char in ["@", "University", "Department", "Faculty"]):
                                break

            if author_candidates:
                authors = author_candidates

        doc.close()
    except Exception as exc:
        logger.warning(
            "PDF font-size visual metadata extraction failed for %s (%s); falling back to file name.",
            pdf_path.name,
            exc,
        )
        warnings.append(
            f"Could not read PDF layout of {pdf_path.name}; file name used as title."
        )

    if not title:
        title = title_from_filename(pdf_path)
        if not warnings:
            warnings.append(f"No title detected in PDF {pdf_path.name}; file name used.")
    if not authors:
        warnings.append(f"No authors detected in PDF {pdf_path.name}.")

    return title, authors, warnings


def extract(paper_path: Path, job_id: str) -> Tuple[str, List[str], List[str]]:
    """Return ``(title, authors, warnings)`` for one paper (.docx or .pdf).

    Never raises: a paper the analyzer cannot read still gets a name and a
    warning, because failing an entire twenty-paper batch over one malformed
    file would be the wrong trade for an operator waiting on the output.
    """
    if paper_path.suffix.lower() == ".pdf":
        return extract_pdf_metadata(paper_path)

    warnings: List[str] = []
    title = ""
    authors: List[str] = []

    try:
        # Imported here, not at module scope: see the module docstring.
        from app.services.document_analyzer import DocumentAnalyzer

        model, _diagnostics = DocumentAnalyzer().analyze_document(paper_path, job_id)
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
                f"{paper_path.name}."
            )
        elif dropped:
            logger.info(
                "Discarded %d non-name line(s) from the author block of %s: %s",
                len(dropped),
                paper_path.name,
                "; ".join(dropped[:5]),
            )
    except Exception as exc:  # noqa: BLE001 - any analyzer failure is non-fatal
        logger.warning(
            "Metadata extraction failed for %s (%s); falling back to the file name.",
            paper_path.name,
            exc,
        )
        warnings.append(
            f"Could not read the document structure of {paper_path.name}; "
            "the file name was used as the title."
        )

    if not title:
        title = title_from_filename(paper_path)
        if not warnings:
            warnings.append(
                f"No title detected in {paper_path.name}; the file name was used."
            )
    if not authors:
        warnings.append(f"No authors detected in {paper_path.name}.")

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
