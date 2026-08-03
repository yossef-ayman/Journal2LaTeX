"""Preview and apply accepted edits to an uploaded manuscript.

Two endpoints, and the split between them is the directive's "generate a preview
before saving" made structural rather than advisory.

``POST /document-engine/preview`` reports what would happen: every applied edit
with its word-level diff, every refusal with its reason, and which parts of the
package would be rewritten by how many bytes.  It returns no document.

``POST /document-engine/apply`` does the same work and returns the .docx.

Both are stateless.  The client uploads the original document alongside its
decisions, and the server holds nothing between calls -- no session, no job
directory, no temporary copy of somebody's unpublished manuscript.  That is a
deliberate privacy property as much as an architectural one, and it is possible
only because suggestion ids are deterministic: the same document analysed again
produces the same ids, so decisions made against one response are still valid
against the next.

Nothing here touches the Word -> LaTeX converter or the Document Generator.
"""

from __future__ import annotations

import io
import json
from typing import Any, Dict, List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from document_engine.edit.preview import PreviewEngine
from document_engine.edit.suggestions import SuggestionError, SuggestionSet
from document_engine.ooxml.bytes import OOXMLEditError

router = APIRouter()

_MAX_BYTES = 64 * 1024 * 1024

_DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


async def _engine(file: UploadFile) -> PreviewEngine:
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="the uploaded file is empty")
    if len(payload) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="the uploaded file is too large")
    try:
        return PreviewEngine.open(io.BytesIO(payload))
    except (OOXMLEditError, KeyError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail=f"this file could not be read as a Word document: {error}",
        ) from error


def _decisions(raw: str) -> SuggestionSet:
    """Parse the decision set, refusing anything malformed rather than ignoring it."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=400, detail=f"suggestions is not valid JSON: {error}"
        ) from error
    if not isinstance(payload, list):
        raise HTTPException(
            status_code=400, detail="suggestions must be a list of suggestion objects"
        )
    try:
        return SuggestionSet.from_list(payload)
    except SuggestionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/preview")
async def preview(
    file: UploadFile = File(...),
    suggestions: str = Form("[]"),
) -> Dict[str, Any]:
    """What accepting these suggestions would do.  Writes nothing."""
    engine = await _engine(file)
    decisions = _decisions(suggestions)
    result = engine.preview(decisions, source=file.filename or "upload.docx")
    payload = result.as_dict()
    payload["suggestions"] = decisions.counts()
    return payload


@router.post("/apply")
async def apply(
    file: UploadFile = File(...),
    suggestions: str = Form("[]"),
) -> StreamingResponse:
    """The document with the accepted suggestions written into it.

    A refusal does not fail the request: the caller gets the edits that were
    valid, and the report of what was refused travels in a response header so it
    is visible without having to parse the .docx to find out.
    """
    engine = await _engine(file)
    decisions = _decisions(suggestions)
    result = engine.preview(decisions, source=file.filename or "upload.docx")
    data = result.to_bytes()

    refused: List[Dict[str, Any]] = [item.as_dict() for item in result.result.refused]
    name = (file.filename or "document.docx").rsplit("/", 1)[-1]
    headers = {
        "Content-Disposition": f'attachment; filename="edited-{name}"',
        "X-Edits-Applied": str(len(result.result.applied)),
        "X-Edits-Refused": json.dumps(refused) if refused else "0",
    }
    return StreamingResponse(
        io.BytesIO(data), media_type=_DOCX_MEDIA_TYPE, headers=headers
    )


__all__ = ["router"]
