"""Conversion of legacy Word .doc binary files to modern .docx XML packages.

Supports both Windows Word COM automation and cross-platform LibreOffice headless.
All embedded text, formatting, equations, AND figures/images inside .doc are preserved
in the generated .docx file.
"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("app.utils.doc_converter")


def convert_doc_to_docx(doc_path: Path) -> Path:
    """Convert a legacy .doc binary file to .docx in the same directory.

    Returns the path to the converted .docx file if successful, or the original
    path if conversion failed or was unnecessary.
    """
    if doc_path.suffix.lower() != ".doc":
        return doc_path

    out_docx = doc_path.with_suffix(".docx")

    # Method 1: Windows Word COM Automation (Most accurate for Word binary format)
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
            if out_docx.is_file() and out_docx.stat().st_size > 0:
                logger.info(
                    "Successfully converted %s to .docx via Word COM automation",
                    doc_path.name,
                )
                return out_docx
        except Exception as exc:
            logger.warning(
                "Word COM .doc conversion failed for %s: %s", doc_path.name, exc
            )

    # Method 2: LibreOffice Headless (Cross-platform)
    try:
        soffice = (
            shutil.which("soffice")
            or shutil.which("libreoffice")
            or r"C:\Program Files\LibreOffice\program\soffice.exe"
        )
        if soffice and Path(soffice).exists():
            cmd = [
                str(soffice),
                "--headless",
                "--convert-to",
                "docx",
                str(doc_path.resolve()),
                "--outdir",
                str(doc_path.parent.resolve()),
            ]
            res = subprocess.run(cmd, capture_output=True, timeout=60, check=False)
            if res.returncode == 0 and out_docx.is_file() and out_docx.stat().st_size > 0:
                logger.info(
                    "Successfully converted %s to .docx via LibreOffice",
                    doc_path.name,
                )
                return out_docx
            else:
                logger.warning(
                    "LibreOffice returncode %d for %s: %s",
                    res.returncode,
                    doc_path.name,
                    res.stderr.decode("utf-8", errors="ignore"),
                )
    except Exception as exc:
        logger.warning(
            "LibreOffice .doc conversion failed for %s: %s", doc_path.name, exc
        )

    return doc_path
