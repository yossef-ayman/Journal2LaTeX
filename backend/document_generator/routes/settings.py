"""Settings endpoints.

The persisted values a generation falls back to: the reference-number suffix, the
default editor and journal names, standing custom placeholders, and whether PDFs
are produced.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from document_generator import config
from document_generator.models.schemas import GeneratorSettings, GeneratorSettingsUpdate
from document_generator.pdf import converter as pdf_converter
from document_generator.services import reference_numbers

logger = logging.getLogger("document_generator.routes.settings")

router = APIRouter()


def _current() -> GeneratorSettings:
    backend = pdf_converter.backend_name()
    return GeneratorSettings(
        **config.load_settings(),
        pdf_backend_available=backend is not None,
        pdf_backend=backend,
    )


@router.get("/settings", response_model=GeneratorSettings)
async def get_settings() -> GeneratorSettings:
    """Current settings, plus which PDF backend this server can actually use."""
    return _current()


@router.put("/settings", response_model=GeneratorSettings)
async def update_settings(update: GeneratorSettingsUpdate) -> GeneratorSettings:
    """Apply a partial settings update."""
    if update.reference_suffix is not None and len(update.reference_suffix) > 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The reference suffix must be 8 characters or fewer.",
        )
    if update.journal_code is not None and len(update.journal_code) > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The journal code must be 12 characters or fewer.",
        )
    payload = update.model_dump(exclude_none=True)
    if payload.get("journal_code") is not None:
        # Stored normalised so the same journal always numbers the same way, no
        # matter how the code was typed into the form.
        payload["journal_code"] = reference_numbers.normalise_journal_code(
            payload["journal_code"]
        )
    if payload.get("custom_placeholders") is not None:
        # Normalised here so a template can rely on upper-case names regardless
        # of how the operator typed them into the settings form.
        payload["custom_placeholders"] = {
            str(k).strip().upper(): "" if v is None else str(v)
            for k, v in payload["custom_placeholders"].items()
            if str(k).strip()
        }
    config.save_settings(payload)
    return _current()
