"""PDF rasterization and inspection with pluggable backends.

Three backends, tried in this order:

``pypdfium2``
    The preferred one.  It renders in-process, which matters because the
    Office-object extractor rasterizes one PDF per embedded object -- a paper
    with 156 MathType equations was spawning 156 ``pdftoppm`` processes, and
    almost all of that time was process startup rather than rendering.  Its
    licence (BSD/Apache, via PDFium) also makes it usable in a commercial
    product without the obligations the alternative carries.

``PyMuPDF`` (``fitz``)
    Kept because it works and some installations already have it, but no
    longer preferred: it is AGPL-licensed.

poppler CLI (``pdftoppm`` / ``pdfinfo``)
    The fallback that needs no Python package at all, so a machine with only
    poppler installed still works.

All three produce ``page_<n>.png`` at the requested DPI, so callers cannot
tell which one ran.
"""

import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

try:  # pragma: no cover - import guard
    import pypdfium2  # PDFium bindings

    _HAS_PDFIUM = True
except ImportError:  # pragma: no cover
    _HAS_PDFIUM = False

try:  # pragma: no cover - import guard
    import fitz  # PyMuPDF

    _HAS_FITZ = True
except ImportError:  # pragma: no cover
    _HAS_FITZ = False

#: PDF user space is 72 units to the inch, so a render scale of dpi/72
#: reproduces exactly the pixel dimensions ``pdftoppm -r <dpi>`` produces.
_PDF_UNITS_PER_INCH = 72.0


class PdfToolsError(Exception):
    """Raised when no usable PDF backend is available or a call fails."""


def available_backend() -> Optional[str]:
    """Return the name of the active PDF backend, or None if none exists."""
    if _HAS_PDFIUM:
        return "pypdfium2"
    if _HAS_FITZ:
        return "pymupdf"
    if shutil.which("pdftoppm") and shutil.which("pdfinfo"):
        return "poppler"
    return None


def pdf_page_count(pdf_path: Path) -> int:
    """Return the number of pages in a PDF (0 if the file is missing)."""
    if not pdf_path.exists():
        return 0
    if _HAS_PDFIUM:
        doc = pypdfium2.PdfDocument(str(pdf_path))
        try:
            return len(doc)
        finally:
            doc.close()
    if _HAS_FITZ:
        with fitz.open(pdf_path) as doc:
            return doc.page_count
    if shutil.which("pdfinfo"):
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True, text=True, check=False, timeout=600,
        )
        match = re.search(r"^Pages:\s+(\d+)", result.stdout, re.MULTILINE)
        if match:
            return int(match.group(1))
        return 0
    raise PdfToolsError(
        "No PDF backend available (install pypdfium2 or poppler-utils).")


def render_pdf_to_images(pdf_path: Path, out_dir: Path, dpi: int = 150) -> List[Path]:
    """Render each PDF page to ``out_dir/page_<n>.png`` and return the paths.

    Returns an empty list when the PDF does not exist.  Raises PdfToolsError
    when no rasterization backend is available.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if not pdf_path.exists():
        return []

    if _HAS_PDFIUM:
        images: List[Path] = []
        doc = pypdfium2.PdfDocument(str(pdf_path))
        try:
            for idx in range(len(doc)):
                page = doc[idx]
                # scale = dpi/72 is the same conversion ``pdftoppm -r <dpi>``
                # applies, so page dimensions match to within the one pixel the
                # two rasterizers' rounding conventions differ by (poppler
                # rounds, PDFium takes the ceiling).
                bitmap = page.render(scale=dpi / _PDF_UNITS_PER_INCH)
                img_path = out_dir / f"page_{idx + 1}.png"
                bitmap.to_pil().save(str(img_path))
                images.append(img_path)
        finally:
            doc.close()
        return images

    if _HAS_FITZ:
        images: List[Path] = []
        with fitz.open(pdf_path) as doc:
            for idx, page in enumerate(doc):
                pix = page.get_pixmap(dpi=dpi)
                img_path = out_dir / f"page_{idx + 1}.png"
                pix.save(str(img_path))
                images.append(img_path)
        return images

    if shutil.which("pdftoppm"):
        prefix = out_dir / "page"
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
            capture_output=True, text=True, check=True, timeout=30000,
        )
        # pdftoppm names files page-1.png / page-01.png depending on count;
        # normalize to page_<n>.png.
        images = []
        for produced in sorted(out_dir.glob("page-*.png")):
            num = int(produced.stem.split("-")[-1])
            target = out_dir / f"page_{num}.png"
            produced.replace(target)
            images.append(target)
        images.sort(key=lambda p: int(p.stem.split("_")[-1]))
        return images

    raise PdfToolsError(
        "No PDF backend available (install pypdfium2 or poppler-utils).")
