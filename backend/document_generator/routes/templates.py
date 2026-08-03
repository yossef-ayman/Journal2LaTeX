"""Master-template endpoints.

``upload`` and ``replace`` are the same operation by design: a template slot has
exactly one occupant, and the previous file is archived either way.  Both exist
because the requirement names both, and having a distinct ``replace`` makes the
intent explicit in logs and in the UI.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from document_generator.models.schemas import (
    DocumentTypeInfo,
    TemplateInfo,
    TemplateInspection,
    TemplateMapping,
    TemplateMappingUpdate,
)
from document_generator.routes.uploads import require_docx, staged_uploads
from document_generator.services import document_inspector, document_types
from document_generator.services.document_inspector import DocumentInspectorError
from document_generator.services.template_store import TemplateStore, TemplateStoreError

logger = logging.getLogger("document_generator.routes.templates")

router = APIRouter()


def _store() -> TemplateStore:
    return TemplateStore()


@router.get("/document-types", response_model=List[DocumentTypeInfo])
async def list_document_types() -> List[DocumentTypeInfo]:
    """Every document type the module can produce."""
    return document_types.list_document_types()


@router.get("/templates", response_model=List[TemplateInfo])
async def list_templates() -> List[TemplateInfo]:
    """State of each master-template slot, including its placeholders."""
    return _store().describe_all()


async def _store_template(document_type: str, file: UploadFile) -> TemplateInfo:
    if not document_types.is_known(document_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown document type: {document_type}",
        )
    require_docx(file.filename or "")
    with staged_uploads([file]) as staged:
        original, path = staged[0]
        try:
            return _store().save_template(document_type, path, original)
        except TemplateStoreError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc


@router.get("/templates/{document_type}/inspect", response_model=TemplateInspection)
async def inspect_template(document_type: str) -> TemplateInspection:
    """The document broken into selectable text, for the mapping wizard.

    This is what makes an ordinary Word file usable as a template: the operator
    uploads the real letter, sees its actual lines here, and points at the ones
    that change per paper.  Nothing has to be edited in Word.
    """
    if not document_types.is_known(document_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown document type: {document_type}",
        )
    store = _store()
    if not store.has_template(document_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload the template before mapping its fields.",
        )
    try:
        return document_inspector.inspect(
            store.template_path(document_type),
            document_type,
            store.load_mapping(document_type),
        )
    except DocumentInspectorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/templates/{document_type}/mapping", response_model=TemplateMapping)
async def get_mapping(document_type: str) -> TemplateMapping:
    """The saved mapping for a template, or an empty one if it has none."""
    if not document_types.is_known(document_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown document type: {document_type}",
        )
    mapping = _store().load_mapping(document_type)
    return mapping or TemplateMapping(document_type=document_type)


@router.put("/templates/{document_type}/mapping", response_model=TemplateMapping)
async def put_mapping(
    document_type: str, update: TemplateMappingUpdate
) -> TemplateMapping:
    """Confirm the wizard's mapping and store it permanently.

    Saved once; every later generation reuses it, so the operator is never asked
    to map the same template again.
    """
    if not document_types.is_known(document_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown document type: {document_type}",
        )
    try:
        mapping = _store().save_mapping(document_type, list(update.mappings))
    except TemplateStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    logger.info("Stored field mapping for '%s'", document_type)
    return mapping


@router.post("/templates/upload", response_model=TemplateInfo)
async def upload_template(
    document_type: str,
    file: UploadFile = File(...),
) -> TemplateInfo:
    """Store a master template permanently.

    Uploaded once; every later generation reuses it.  The operator is never asked
    for it again.
    """
    logger.info("Uploading master template for '%s'", document_type)
    return await _store_template(document_type, file)


@router.post("/templates/replace", response_model=TemplateInfo)
async def replace_template(
    document_type: str,
    file: UploadFile = File(...),
) -> TemplateInfo:
    """Replace a master template with a newer version.

    The superseded file is archived, so a mistaken replacement is recoverable.
    """
    logger.info("Replacing master template for '%s'", document_type)
    return await _store_template(document_type, file)
