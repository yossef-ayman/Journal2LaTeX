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


def require_docx(filename: str) -> None:
    if not (filename or "").lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"'{filename}' is not a .docx file. Word documents saved as .doc "
                "must be re-saved as .docx first."
            ),
        )


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
            require_docx(original)
            # Numbered so two uploads with the same name cannot collide; the
            # operator-facing name is carried separately.
            target = area / f"{position:03d}_{safe_name(original)}"
            _write(upload, target)
            staged.append((original, target))
        yield staged
    finally:
        try:
            shutil.rmtree(area, ignore_errors=True)
        except Exception:  # pragma: no cover - cleanup must never raise
            logger.warning("Could not clean up the staging directory %s", area)
