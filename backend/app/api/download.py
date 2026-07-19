import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from app.services.job_manager import JobManager

router = APIRouter(prefix="/download", tags=["Download"])


@router.get("/{job_id}", response_class=FileResponse)
async def download_output(job_id: str) -> FileResponse:
    """Download the compiled PDF for a completed job.

    Returns the real output PDF if it exists, or a 404 if not yet compiled.
    """
    job_manager = JobManager()
    metadata = job_manager.get_job(job_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )

    job_dir = job_manager._get_job_dir(job_id)

    # Check real PDF locations in priority order
    candidates = [
        job_dir / "output" / "paper.pdf",
        job_dir / "output" / "output.pdf",
    ]

    pdf_path: Path | None = None
    for candidate in candidates:
        if candidate.exists():
            pdf_path = candidate
            break

    if not pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not available. Ensure the compile stage has completed successfully.",
        )

    safe_name = re.sub(r'[^\w.\- ]', '', metadata.paper_name or "document") or "document"
    return FileResponse(
        path=pdf_path,
        filename=f"{safe_name}.pdf",
        media_type="application/pdf",
    )
