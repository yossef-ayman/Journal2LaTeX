"""Download endpoints.

One endpoint serves both an individual generated file and the whole-batch ZIP,
selected by the ``path`` query parameter, because both are just files inside the
batch's output tree and a single traversal-checked resolver is easier to keep
safe than two.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from document_generator.services.generator_service import (
    OUTPUT_DIR_NAME,
    GenerationError,
    GeneratorService,
)
from document_generator.services.packaging import ZIP_NAME

logger = logging.getLogger("document_generator.routes.download")

router = APIRouter()

_MEDIA_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".zip": "application/zip",
}


@router.get("/download/{batch_id}")
async def download(
    batch_id: str,
    path: str = Query(
        f"{OUTPUT_DIR_NAME}.zip",
        description=(
            "Path within the batch output, e.g. 'Paper 1/Acceptance.pdf'. "
            f"Defaults to '{OUTPUT_DIR_NAME}.zip', the whole batch."
        ),
    ),
) -> FileResponse:
    """Serve one generated file, or the batch archive."""
    try:
        resolved = GeneratorService.resolve_download(batch_id, path)
    except GenerationError as exc:
        # Both a bad identifier and a missing file are reported as 404: the
        # endpoint must not become a probe for what exists on the server.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    if resolved.name == ZIP_NAME:
        # A ZIP of several papers is more recognisable in a download folder when
        # it carries the batch it came from.
        filename = f"{batch_id}_{ZIP_NAME}"
    else:
        # Prefix with the paper folder so twenty "Acceptance.pdf" downloads do
        # not become "Acceptance (7).pdf".
        parts = resolved.parts
        filename = f"{parts[-2]} - {resolved.name}" if len(parts) >= 2 else resolved.name

    return FileResponse(
        path=resolved,
        media_type=_MEDIA_TYPES.get(resolved.suffix.lower(), "application/octet-stream"),
        filename=filename,
    )
