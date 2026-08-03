"""DOCX to PDF conversion.

The requirement is fidelity: the PDF must look like the Word template, because it
is the artefact that actually reaches an author.  That rules out re-drawing the
document with a PDF library -- every such approach re-implements Word's layout
and gets fonts, tabs, tables and headers subtly wrong.

Two backends render the document with the software that understands the format:

* **Microsoft Word automation** (Windows only, via COM).  Word exporting its own
  format is the highest-fidelity option available anywhere, so it is preferred
  when the host actually has Word installed.
* **LibreOffice headless.**  The portable backend, and the one used on Linux
  servers.  Its Word layout engine is close enough that a letter-style document
  is visually identical.

Both are driven so the source file is never modified and each conversion runs in
its own profile directory, which is what makes concurrent batch conversions safe.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from document_generator import config

logger = logging.getLogger("document_generator.pdf")

# Generous: a first LibreOffice start-up on a cold container is slow, and a
# batch's first document should not fail because of it.
_CONVERSION_TIMEOUT = 180

_BACKEND_WORD = "Microsoft Word"
_BACKEND_SOFFICE = "LibreOffice"


class PdfConversionError(Exception):
    """Raised when a DOCX could not be converted to PDF."""


def _word_available() -> bool:
    """Whether Word automation can be used on this host."""
    if platform.system() != "Windows":
        return False
    try:
        import win32com.client  # noqa: F401  (probe only)
    except Exception:
        return False
    return True


def backend_name() -> Optional[str]:
    """Which backend would be used here, or ``None`` if PDF export is unavailable."""
    if _word_available():
        return _BACKEND_WORD
    if config.soffice_binary():
        return _BACKEND_SOFFICE
    return None


def is_available() -> bool:
    return backend_name() is not None


def _convert_with_word(docx_path: Path, output_path: Path) -> None:
    """Export via Word automation (Windows)."""
    import pythoncom  # type: ignore[import-not-found]
    import win32com.client  # type: ignore[import-not-found]

    # Each conversion initialises COM for its own thread: FastAPI runs blocking
    # work in a thread pool, and an uninitialised thread fails cryptically.
    pythoncom.CoInitialize()
    word = None
    document = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        # ReadOnly and AddToRecentFiles=False keep the master template and the
        # operator's Word environment untouched.
        document = word.Documents.Open(
            str(docx_path), ReadOnly=True, AddToRecentFiles=False, Visible=False
        )
        # 17 = wdExportFormatPDF
        document.ExportAsFixedFormat(str(output_path), 17)
    except Exception as exc:  # noqa: BLE001 - COM raises a wide variety
        raise PdfConversionError(f"Word could not export {docx_path.name}: {exc}") from exc
    finally:
        try:
            if document is not None:
                document.Close(False)
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass
        pythoncom.CoUninitialize()


def _convert_with_soffice(docx_path: Path, output_path: Path) -> None:
    """Export via LibreOffice headless."""
    binary = config.soffice_binary()
    if not binary:
        raise PdfConversionError("LibreOffice is not installed on this server.")

    # A private profile per conversion: LibreOffice refuses to start a second
    # instance against a shared profile, which would serialise (or break) the
    # conversions of a batch.
    with tempfile.TemporaryDirectory(prefix="dg_soffice_") as profile:
        out_dir = Path(profile) / "out"
        out_dir.mkdir()
        command = [
            binary,
            "--headless",
            "--norestore",
            "--invisible",
            "--nolockcheck",
            "--nodefault",
            "--nologo",
            f"-env:UserInstallation=file://{Path(profile) / 'profile'}",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            str(out_dir),
            str(docx_path),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=_CONVERSION_TIMEOUT,
                env={**os.environ, "HOME": profile},
            )
        except subprocess.TimeoutExpired as exc:
            raise PdfConversionError(
                f"PDF conversion of {docx_path.name} timed out after "
                f"{_CONVERSION_TIMEOUT}s."
            ) from exc
        except OSError as exc:
            raise PdfConversionError(f"Could not run LibreOffice: {exc}") from exc

        produced = out_dir / f"{docx_path.stem}.pdf"
        if not produced.is_file():
            # LibreOffice exits 0 on some failures, so the output file -- not the
            # return code -- is the authority on success.
            detail = (result.stderr or result.stdout or "").strip()[:500]
            raise PdfConversionError(
                f"LibreOffice produced no PDF for {docx_path.name}."
                + (f" Details: {detail}" if detail else "")
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(produced), str(output_path))


def convert_to_pdf(docx_path: Path, output_path: Path) -> str:
    """Convert ``docx_path`` to ``output_path``. Returns the backend used."""
    if not docx_path.is_file():
        raise PdfConversionError(f"Document not found: {docx_path}")

    backend = backend_name()
    if backend is None:
        raise PdfConversionError(
            "No PDF converter is available on this server. Install LibreOffice "
            "(or run the service on a host with Microsoft Word) to export PDFs."
        )

    if backend == _BACKEND_WORD:
        _convert_with_word(docx_path, output_path)
    else:
        _convert_with_soffice(docx_path, output_path)

    logger.info("Converted %s to PDF via %s", docx_path.name, backend)
    return backend
