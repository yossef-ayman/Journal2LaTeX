"""PDF rasterization and inspection with pluggable backends.

Uses PyMuPDF (``fitz``) when installed; otherwise falls back to the poppler
command-line tools (``pdftoppm`` / ``pdfinfo``).  This keeps the visual
comparison stage working on machines where only one of the two is available
(PyMuPDF on typical Windows installs, poppler on typical Linux servers).
"""

import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

try:  # pragma: no cover - import guard
    import fitz  # PyMuPDF

    _HAS_FITZ = True
except ImportError:  # pragma: no cover
    _HAS_FITZ = False


class PdfToolsError(Exception):
    """Raised when no usable PDF backend is available or a call fails."""


def available_backend() -> Optional[str]:
    """Return the name of the active PDF backend, or None if none exists."""
    if _HAS_FITZ:
        return "pymupdf"
    if shutil.which("pdftoppm") and shutil.which("pdfinfo"):
        return "poppler"
    return None


def pdf_page_count(pdf_path: Path) -> int:
    """Return the number of pages in a PDF (0 if the file is missing)."""
    if not pdf_path.exists():
        return 0
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
    raise PdfToolsError("No PDF backend available (install PyMuPDF or poppler-utils).")


def render_pdf_to_images(pdf_path: Path, out_dir: Path, dpi: int = 150) -> List[Path]:
    """Render each PDF page to ``out_dir/page_<n>.png`` and return the paths.

    Returns an empty list when the PDF does not exist.  Raises PdfToolsError
    when no rasterization backend is available.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if not pdf_path.exists():
        return []

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

    raise PdfToolsError("No PDF backend available (install PyMuPDF or poppler-utils).")
