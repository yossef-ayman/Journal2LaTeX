import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from app.services.template_manager import TemplateManager, TemplateManagerError

router = APIRouter(prefix="/templates", tags=["Templates"])


class TemplateMetadataUpdate(BaseModel):
    display_name: str
    journal_name: str
    version: str
    description: str


@router.get("", response_model=List[dict])
async def list_templates() -> List[dict]:
    """Return all available journal templates (both built-in and uploaded) with metadata."""
    manager = TemplateManager()
    return manager.list_templates()


@router.post("/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_template(file: UploadFile = File(...)) -> dict:
    """Upload a template package in .zip format."""
    # Check suffix
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported template file format. Only ZIP archives are supported."
        )

    # Save to a temporary location to verify
    import tempfile
    temp_zip = Path(tempfile.gettempdir()) / f"temp_template_{uuid_suffix()}.zip"
    try:
        with temp_zip.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        manager = TemplateManager()
        metadata = manager.save_template_package(temp_zip)
        return metadata

    except TemplateManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while uploading template: {str(e)}"
        )
    finally:
        if temp_zip.exists():
            temp_zip.unlink()


@router.get("/{template_id}", response_model=dict)
async def get_template(template_id: str) -> dict:
    """Get metadata for a specific template."""
    manager = TemplateManager()
    try:
        return manager.get_template_metadata(template_id)
    except TemplateManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/{template_id}", response_model=dict)
async def update_template(template_id: str, updates: TemplateMetadataUpdate) -> dict:
    """Update template metadata fields."""
    manager = TemplateManager()
    try:
        return manager.update_template_metadata(template_id, updates.model_dump())
    except TemplateManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: str) -> None:
    """Delete an uploaded template package."""
    manager = TemplateManager()
    try:
        manager.delete_template(template_id)
    except TemplateManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


def uuid_suffix() -> str:
    import uuid
    return str(uuid.uuid4())
