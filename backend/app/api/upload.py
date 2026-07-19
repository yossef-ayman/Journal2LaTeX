import re
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from app.services.job_manager import JobManager
from app.models.job import JobMetadata

router = APIRouter(prefix="/upload", tags=["Upload"])

ALLOWED_EXTENSIONS = {".docx"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _sanitize_filename(filename: str) -> str:
    """Strip path separators and dangerous characters from a filename."""
    name = Path(filename).name  # strips any directory components
    name = re.sub(r'[^\w.\- ]', '', name)  # keep safe chars only
    return name or "paper.docx"


@router.post("", response_model=JobMetadata, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
) -> JobMetadata:
    """Upload a document and initialize a job workspace.

    Validates the file extension and size, then saves the file
    to the job's input directory with a safe filename.
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Only .docx files are allowed.",
        )

    # Read content and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit.",
        )

    job_manager = JobManager()
    safe_name = _sanitize_filename(file.filename)
    metadata = job_manager.create_job(paper_name=safe_name)

    # Save the file to input/ folder with safe name
    job_dir = job_manager._get_job_dir(metadata.job_id)
    input_file_path = job_dir / "input" / safe_name

    with open(input_file_path, "wb") as buffer:
        buffer.write(content)

    return metadata
