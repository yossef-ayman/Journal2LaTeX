from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from app.services.job_manager import JobManager

router = APIRouter(prefix="/download", tags=["Download"])


@router.get("/{job_id}", response_class=FileResponse)
async def download_output(job_id: str) -> FileResponse:
    """Mock download endpoint.

    Locates the output PDF or workspace artifact, and returns it.
    Returns a dummy text file if no PDF is compiled yet.
    """
    job_manager = JobManager()
    metadata = job_manager.get_job(job_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )

    # In a real app we'd retrieve output_pdf, for mock we create a dummy file
    job_dir = job_manager._get_job_dir(job_id)
    output_pdf_path = job_dir / "output" / "output.pdf"

    if not output_pdf_path.exists():
        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        output_pdf_path.write_text("Dummy PDF content", encoding="utf-8")

    return FileResponse(
        path=output_pdf_path,
        filename=f"document_{job_id}.pdf",
        media_type="application/pdf",
    )
