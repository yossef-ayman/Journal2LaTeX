"""Conversion of LaTeX-unsupported media formats (WMF/EMF/SVG) to PNG.

pdflatex cannot include .wmf/.emf/.svg graphics; Word documents frequently
embed equations and drawings as WMF.  This module batch-converts such files
to PNG using LibreOffice headless (available on both Windows and Linux
installs of LibreOffice).  Original files are kept so asset-matching against
the extracted originals still works.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageChops

from app.core.config import settings
from app.utils.logger import get_job_logger

UNSUPPORTED_SUFFIXES = {".wmf", ".emf", ".svg"}
# EPS is convertible by pdflatex itself via epstopdf -- but only when
# ghostscript is installed.  Without it we must pre-convert.
_EPS_SUFFIX = ".eps"


def _ghostscript_available() -> bool:
    return any(shutil.which(exe) for exe in ("gs", "gswin64c", "gswin32c", "mgs"))


def _autocrop_png(png_path: Path, padding: int = 6) -> None:
    """Trim the white page canvas LibreOffice puts around converted vectors."""
    try:
        with Image.open(png_path) as im:
            rgb = im.convert("RGB")
            bg = Image.new("RGB", rgb.size, (255, 255, 255))
            bbox = ImageChops.difference(rgb, bg).getbbox()
            if not bbox:
                return
            left = max(0, bbox[0] - padding)
            top = max(0, bbox[1] - padding)
            right = min(rgb.size[0], bbox[2] + padding)
            bottom = min(rgb.size[1], bbox[3] + padding)
            if (right - left) < rgb.size[0] or (bottom - top) < rgb.size[1]:
                rgb.crop((left, top, right, bottom)).save(png_path)
    except Exception:
        pass  # keep the uncropped image rather than losing it


def latex_safe_image_name(path_or_name: str) -> str:
    """Map a media filename to the name LaTeX should reference.

    WMF/EMF/SVG files are referenced through their converted PNG sibling.
    """
    p = Path(path_or_name)
    if p.suffix.lower() in UNSUPPORTED_SUFFIXES:
        return p.with_suffix(".png").name
    return p.name


def convert_unsupported_media(media_dir: Path, job_id: str) -> Dict[str, Any]:
    """Convert every WMF/EMF/SVG file in *media_dir* to a PNG sibling.

    Returns a report dict: {"converted": [...], "failed": [...], "backend": str}.
    Never raises: conversion problems are reported, not fatal.
    """
    logger = get_job_logger(job_id, "system")
    report: Dict[str, Any] = {"converted": [], "failed": [], "backend": None}

    if not media_dir.is_dir():
        return report
    suffixes = set(UNSUPPORTED_SUFFIXES)
    if not _ghostscript_available():
        # pdflatex cannot convert EPS without ghostscript; pre-render to PNG
        # so extensionless \includegraphics references still resolve.
        suffixes.add(_EPS_SUFFIX)
    pending: List[Path] = [
        f for f in sorted(media_dir.iterdir())
        if f.is_file()
        and f.suffix.lower() in suffixes
        and not f.with_suffix(".png").exists()
    ]
    if not pending:
        return report

    soffice = shutil.which(settings.SOFFICE_PATH) or shutil.which("libreoffice")
    if not soffice:
        msg = f"{len(pending)} vector media files need conversion but LibreOffice is unavailable."
        logger.warning(msg)
        report["failed"] = [f.name for f in pending]
        return report

    report["backend"] = "libreoffice"
    try:
        result = subprocess.run(
            [soffice, "--headless", "--norestore", "--convert-to", "png",
             "--outdir", str(media_dir)] + [str(f) for f in pending],
            capture_output=True, text=True, check=False,
            timeout=settings.COMPILE_TIMEOUT,
        )
        if result.returncode != 0:
            logger.warning("LibreOffice media conversion rc=%d: %s",
                           result.returncode, (result.stderr or "")[:300])
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("LibreOffice media conversion failed: %s", exc)

    for f in pending:
        png = f.with_suffix(".png")
        if png.exists():
            _autocrop_png(png)
            report["converted"].append(f.name)
        else:
            report["failed"].append(f.name)
    if report["failed"]:
        logger.warning("Media files not converted to PNG: %s", report["failed"][:10])
    logger.info("Vector media conversion: %d converted, %d failed.",
                len(report["converted"]), len(report["failed"]))
    return report
