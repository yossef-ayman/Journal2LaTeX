"""Ask the assistant what it would change.

``GET /document-engine/plugins`` lists what is available and which plugins are
on by default, so the UI renders the assistant's capabilities instead of
hard-coding a list that drifts from the backend.

``POST /document-engine/suggest`` runs them over an uploaded manuscript and
returns suggestions and notes.  It **writes nothing and returns no document**:
the response is a decision set the user reviews and then posts back to
``/document-engine/preview`` or ``/document-engine/apply``, which are the only
endpoints that touch a document's bytes.  Suggestion ids are deterministic, so a
decision made against this response is still valid against the next one.

Like the rest of the engine's HTTP surface this is stateless -- the manuscript
is read, reviewed and dropped -- and it touches neither the Word -> LaTeX
converter nor the Document Generator.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from document_engine.assist import DocumentAssistant, default_registry
from document_engine.edit.preview import PreviewEngine
from document_engine.ooxml.bytes import OOXMLEditError

router = APIRouter()

_MAX_BYTES = 64 * 1024 * 1024


def _selected(raw: str) -> Optional[List[str]]:
    """``""`` means "the defaults"; a list means exactly those."""
    names = [part.strip() for part in raw.split(",") if part.strip()]
    return names or None


@router.get("/plugins")
def plugins() -> Dict[str, Any]:
    """Every plugin this deployment has, with its default state."""
    return {"plugins": default_registry().describe()}


@router.post("/suggest")
async def suggest(
    file: UploadFile = File(...),
    plugins: str = Form(""),
) -> Dict[str, Any]:
    """Review a manuscript.  Proposes only; changes nothing."""
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="the uploaded file is empty")
    if len(payload) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="the uploaded file is too large")

    try:
        engine = PreviewEngine.open(io.BytesIO(payload))
        document = engine.analyze(source=file.filename or "upload.docx")
    except (OOXMLEditError, KeyError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail=f"this file could not be read as a Word document: {error}",
        ) from error

    assistant = DocumentAssistant(default_registry())
    try:
        review = assistant.review(document, _selected(plugins))
    except ValueError as error:      # an unknown plugin name
        raise HTTPException(status_code=400, detail=str(error)) from error

    result = review.as_dict()
    result["source"] = file.filename or "upload.docx"
    return result


__all__ = ["router"]
