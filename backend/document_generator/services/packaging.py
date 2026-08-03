"""ZIP packaging of a generated batch.

The archive mirrors the output tree exactly (``Output/Paper 1/Acceptance.docx``
and so on) so an operator who unzips it gets the same folders they saw in the UI.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

logger = logging.getLogger("document_generator.packaging")

ZIP_NAME = "Documents.zip"


class PackagingError(Exception):
    """Raised when a batch archive cannot be produced."""


def build_batch_zip(output_root: Path, destination: Path) -> Path:
    """Archive everything under ``output_root`` into ``destination``.

    Written to a temporary file and atomically replaced, so a download that
    starts while a rebuild is in progress can never receive a truncated archive.
    """
    if not output_root.is_dir():
        raise PackagingError("This batch has no generated files to package.")

    files = sorted(p for p in output_root.rglob("*") if p.is_file())
    if not files:
        raise PackagingError("This batch has no generated files to package.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                # Rooted at the parent so the archive expands into an "Output"
                # folder rather than scattering paper folders into the cwd.
                archive.write(path, str(Path(output_root.name) / path.relative_to(output_root)))
        tmp.replace(destination)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise PackagingError(f"Could not build the archive: {exc}") from exc

    logger.info("Packaged %d files into %s", len(files), destination.name)
    return destination
