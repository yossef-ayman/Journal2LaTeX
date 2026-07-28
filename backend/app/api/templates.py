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


# --------------------------------------------------------------------- #
# ZIP Template Editor: browse / preview / edit / add / delete / download
# / validate template files.
# --------------------------------------------------------------------- #

class TemplateFileWrite(BaseModel):
    content: str
    encoding: str = "text"  # "text" (UTF-8) or "base64" (binary payloads)


def _manager_call(fn, *args, not_found_ok: bool = False):
    """Run a TemplateManager call, mapping errors to proper HTTP statuses."""
    try:
        return fn(*args)
    except TemplateManagerError as e:
        message = str(e)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


@router.get("/{template_id}/files", response_model=List[dict])
async def list_template_files(template_id: str) -> List[dict]:
    """Browse the template's file tree (path, type, size, is_text)."""
    return _manager_call(TemplateManager().list_files, template_id)


@router.get("/{template_id}/files/{file_path:path}", response_model=dict)
async def read_template_file(template_id: str, file_path: str) -> dict:
    """Preview one template file (text content, or base64 for binaries)."""
    return _manager_call(TemplateManager().read_file, template_id, file_path)


@router.put("/{template_id}/files/{file_path:path}", response_model=dict)
async def write_template_file(
    template_id: str, file_path: str, body: TemplateFileWrite
) -> dict:
    """Create or replace a file in an uploaded template (edit / add / replace)."""
    manager = TemplateManager()
    return _manager_call(
        manager.write_file, template_id, file_path, body.content, body.encoding
    )


@router.delete("/{template_id}/files/{file_path:path}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_template_file(template_id: str, file_path: str) -> None:
    """Delete one file (or an empty directory) from an uploaded template."""
    _manager_call(TemplateManager().delete_file, template_id, file_path)


@router.get("/{template_id}/download")
async def download_template(template_id: str):
    """Download the template (including any edits) as a fresh ZIP archive."""
    from fastapi.responses import FileResponse
    import tempfile
    manager = TemplateManager()
    dest = Path(tempfile.mkdtemp(prefix="j2l_template_export_"))
    zip_path = _manager_call(manager.export_zip, template_id, dest)
    meta = manager.get_template_metadata(template_id)
    nice_name = (meta.get("display_name") or template_id).replace(" ", "_")
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"{nice_name}.zip",
    )


@router.get("/{template_id}/validate", response_model=dict)
async def validate_template(template_id: str) -> dict:
    """Validate the template before conversion: entry file, document structure,
    referenced resources, and forbidden file types."""
    return _manager_call(TemplateManager().validate_template, template_id)


def uuid_suffix() -> str:
    import uuid
    return str(uuid.uuid4())
