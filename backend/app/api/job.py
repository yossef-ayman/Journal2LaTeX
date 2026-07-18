from fastapi import APIRouter, HTTPException, status
from app.services.job_manager import JobManager
from app.models.job import JobMetadata

router = APIRouter(prefix="/job", tags=["Job"])


@router.get("/{job_id}", response_model=JobMetadata)
async def get_job_status(job_id: str) -> JobMetadata:
    """Retrieve the current metadata and status of a job."""
    job_manager = JobManager()
    metadata = job_manager.get_job(job_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )
    return metadata


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str) -> None:
    """Clean up and delete a job's workspace directory."""
    job_manager = JobManager()
    metadata = job_manager.get_job(job_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )

    success = job_manager.cleanup(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workspace for job {job_id}",
        )
