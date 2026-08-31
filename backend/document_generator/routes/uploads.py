"""Shared upload handling for the module's routes.

Uploads are streamed to a scratch directory before anything inspects them, so a
large batch never has to be held in memory and a rejected file never touches the
module's permanent storage.
"""

from __future__ import annotations

import logging
import re
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Sequence, Tuple

from fastapi import HTTPException, UploadFile, status

from document_generator import config

logger = logging.getLogger("document_generator.uploads")

# 64 MiB per file: comfortably above any real letter template or manuscript,
# low enough that a mistaken upload cannot fill the disk.
MAX_UPLOAD_BYTES = 64 * 1024 * 1024
_CHUNK = 1024 * 1024

_UNSAFE_NAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(name: str) -> str:
    """A file name safe to place on disk, preserving what the operator sees."""
    cleaned = _UNSAFE_NAME_RE.sub("_", Path(name or "").name.strip())
    return cleaned[:180] or "upload"


def require_paper_or_docx(
    filename: str, allow_pdf: bool = True, allow_doc: bool = True
) -> None:
    ext = Path(filename or "").suffix.lower()
    allowed = [".docx"]
    if allow_pdf:
        allowed.append(".pdf")
    if allow_doc:
        allowed.append(".doc")

    if ext not in allowed:
        msg = (
            f"'{filename}' is not a supported paper file. Please upload a .docx, .doc, or .pdf file."
            if allow_pdf
            else f"'{filename}' is not a .docx file. Word documents saved as .doc must be re-saved as .docx first."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )


require_docx = require_paper_or_docx


def convert_doc_to_docx(doc_path: Path) -> Path:
    """Convert a legacy .doc binary file to .docx in the same directory."""
    import platform
    import subprocess

    out_docx = doc_path.with_suffix(".docx")

    # Method 1: Try Word Automation via COM if on Windows
    if platform.system() == "Windows":
        try:
            import pythoncom  # type: ignore[import-not-found]
            import win32com.client  # type: ignore[import-not-found]

            pythoncom.CoInitialize()
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False
            doc = word.Documents.Open(
                str(doc_path.resolve()), ReadOnly=True, Visible=False
            )
            # 16 = wdFormatXMLDocument (.docx)
            doc.SaveAs2(str(out_docx.resolve()), FileFormat=16)
            doc.Close(False)
            word.Quit()
            if out_docx.is_file():
                logger.info("Successfully converted %s to .docx via Word COM", doc_path.name)
                return out_docx
        except Exception as exc:
            logger.warning("Word COM .doc conversion failed for %s: %s", doc_path.name, exc)

    # Method 2: Try LibreOffice Headless
    binary = config.soffice_binary()
    if binary:
        try:
            cmd = [
                binary,
                "--headless",
                "--convert-to",
                "docx",
                str(doc_path.resolve()),
                "--outdir",
                str(doc_path.parent.resolve()),
            ]
            subprocess.run(cmd, capture_output=True, timeout=60, check=True)
            if out_docx.is_file():
                logger.info("Successfully converted %s to .docx via LibreOffice", doc_path.name)
                return out_docx
        except Exception as exc:
            logger.warning("LibreOffice .doc conversion failed for %s: %s", doc_path.name, exc)

    return doc_path


def _write(upload: UploadFile, destination: Path) -> None:
    written = 0
    with destination.open("wb") as handle:
        while True:
            chunk = upload.file.read(_CHUNK)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                handle.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=(
                        f"'{upload.filename}' exceeds the "
                        f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit."
                    ),
                )
            handle.write(chunk)
    if written == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{upload.filename}' is empty.",
        )


@contextmanager
def staged_uploads(
    uploads: Sequence[UploadFile],
    allow_pdf: bool = True,
    allow_doc: bool = True,
) -> Iterator[List[Tuple[str, Path]]]:
    """Stage uploads to disk, yielding ``(original filename, path)`` pairs.

    The staging directory is removed when the block exits, whether or not it
    succeeded, so failed requests leave nothing behind.
    """
    config.ensure_directories()
    area = config.STAGING_DIR / uuid.uuid4().hex[:12]
    area.mkdir(parents=True, exist_ok=True)
    staged: List[Tuple[str, Path]] = []
    try:
        for position, upload in enumerate(uploads, start=1):
            original = upload.filename or f"paper-{position}.docx"
            require_paper_or_docx(original, allow_pdf=allow_pdf, allow_doc=allow_doc)
            # Numbered so two uploads with the same name cannot collide; the
            # operator-facing name is carried separately.
            target = area / f"{position:03d}_{safe_name(original)}"
            _write(upload, target)
            if target.suffix.lower() == ".doc":
                target = convert_doc_to_docx(target)
            staged.append((original, target))
        yield staged
    finally:
        try:
            shutil.rmtree(area, ignore_errors=True)
        except Exception:  # pragma: no cover - cleanup must never raise
            logger.warning("Could not clean up the staging directory %s", area)
