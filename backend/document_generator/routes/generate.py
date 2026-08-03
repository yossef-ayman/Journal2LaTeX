"""Generation endpoints.

Generation is CPU- and subprocess-bound (LibreOffice), so the work runs in a
worker thread rather than on the event loop: a twenty-paper batch would otherwise
block every other request for the duration.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from document_generator.models.schemas import BatchGenerationRequest, BatchSummary
from document_generator.routes.uploads import staged_uploads
from document_generator.services.generator_service import GenerationError, GeneratorService

logger = logging.getLogger("document_generator.routes.generate")

router = APIRouter()


def _parse_extra(raw: Optional[str]) -> dict:
    """Ad-hoc placeholder values arrive as a JSON object in a form field."""
    if not raw or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"extra_placeholders is not valid JSON: {exc}",
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="extra_placeholders must be a JSON object.",
        )
    return {str(k): "" if v is None else str(v) for k, v in parsed.items()}


def _parse_types(raw: Optional[str]) -> Optional[List[str]]:
    """Comma-separated document-type keys; ``None`` means "every uploaded template"."""
    if not raw or not raw.strip():
        return None
    keys = [part.strip() for part in raw.split(",") if part.strip()]
    return keys or None


async def _run(
    files: List[UploadFile],
    request: BatchGenerationRequest,
) -> BatchSummary:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No papers were uploaded."
        )
    service = GeneratorService()
    with staged_uploads(files) as staged:
        try:
            return await run_in_threadpool(service.generate_batch, staged, request)
        except GenerationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc


@router.post("/generate-batch", response_model=BatchSummary)
async def generate_batch(
    files: List[UploadFile] = File(..., description="The paper files (.docx)."),
    acceptance_date: str = Form("", description='Used verbatim, e.g. "22 July 2026".'),
    deadline: str = Form(""),
    reference_prefix: Optional[str] = Form(None),
    reference_suffix: Optional[str] = Form(None),
    journal_code: Optional[str] = Form(None),
    editor: Optional[str] = Form(None),
    journal: Optional[str] = Form(None),
    document_types: Optional[str] = Form(None),
    generate_pdf: Optional[bool] = Form(None),
    extra_placeholders: Optional[str] = Form(None),
) -> BatchSummary:
    """Generate every document type for every uploaded paper.

    Upload twenty papers and the response describes twenty acceptance letters and
    twenty invoices, each in DOCX and PDF, with no manual editing in between.
    """
    request = BatchGenerationRequest(
        acceptance_date=acceptance_date,
        deadline=deadline,
        reference_prefix=reference_prefix,
        reference_suffix=reference_suffix,
        journal_code=journal_code,
        editor=editor,
        journal=journal,
        document_types=_parse_types(document_types),
        generate_pdf=generate_pdf,
        extra_placeholders=_parse_extra(extra_placeholders),
    )
    logger.info("Batch generation requested for %d paper(s)", len(files))
    return await _run(files, request)


@router.post("/generate", response_model=BatchSummary)
async def generate_single(
    file: UploadFile = File(..., description="One paper file (.docx)."),
    acceptance_date: str = Form(""),
    deadline: str = Form(""),
    reference_prefix: Optional[str] = Form(None),
    reference_suffix: Optional[str] = Form(None),
    journal_code: Optional[str] = Form(None),
    editor: Optional[str] = Form(None),
    journal: Optional[str] = Form(None),
    document_types: Optional[str] = Form(None),
    generate_pdf: Optional[bool] = Form(None),
    extra_placeholders: Optional[str] = Form(None),
) -> BatchSummary:
    """Generate the documents for a single paper.

    A batch of one, so the response shape and the output layout are identical --
    the UI and any downstream script need only one code path.
    """
    request = BatchGenerationRequest(
        acceptance_date=acceptance_date,
        deadline=deadline,
        reference_prefix=reference_prefix,
        reference_suffix=reference_suffix,
        journal_code=journal_code,
        editor=editor,
        journal=journal,
        document_types=_parse_types(document_types),
        generate_pdf=generate_pdf,
        extra_placeholders=_parse_extra(extra_placeholders),
    )
    logger.info("Single generation requested for %s", file.filename)
    return await _run([file], request)


@router.get("/batches/{batch_id}", response_model=BatchSummary)
async def get_batch(batch_id: str) -> BatchSummary:
    """Re-read a previous batch, so its files stay downloadable after a reload."""
    try:
        summary = GeneratorService.load_summary(batch_id)
    except GenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown batch."
        )
    return summary
