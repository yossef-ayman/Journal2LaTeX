import json
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import PlainTextResponse
from app.services.job_manager import JobManager
from app.models.job import JobMetadata

router = APIRouter(prefix="/job", tags=["Job"])
jobs_router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _resolve_job_dir(job_id: str) -> Path:
    """Return the job's directory, raising 404 if it does not exist."""
    job_manager = JobManager()
    metadata = job_manager.get_job(job_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )
    return job_manager._get_job_dir(job_id)


def _read_intermediate_json(job_dir: Path, filename: str):
    """Read a JSON file from the job's intermediate directory, returning 404 if missing."""
    file_path = job_dir / "intermediate" / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intermediate file '{filename}' not found for this job. Ensure the convert stage has completed.",
        )
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read '{filename}': {str(e)}",
        )


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


@router.get("/{job_id}/fidelity")
async def get_job_fidelity(job_id: str):
    """Return the fidelity report for a job."""
    job_dir = _resolve_job_dir(job_id)
    return _read_intermediate_json(job_dir, "fidelity_report.json")


@router.get("/{job_id}/assets")
async def get_job_assets(job_id: str):
    """Return the asset classification report for a job."""
    job_dir = _resolve_job_dir(job_id)
    return _read_intermediate_json(job_dir, "assets.json")


@router.get("/{job_id}/document")
async def get_job_document(job_id: str):
    """Return the parsed document structure for a job."""
    job_dir = _resolve_job_dir(job_id)
    return _read_intermediate_json(job_dir, "document_structure.json")


@router.get("/{job_id}/latex", response_class=PlainTextResponse)
async def get_job_latex(job_id: str):
    """Return the generated main.tex as plain text."""
    job_dir = _resolve_job_dir(job_id)
    tex_path = job_dir / "rendered" / "main.tex"
    if not tex_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LaTeX source not found for this job. Ensure the compile stage has completed.",
        )
    try:
        return tex_path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read LaTeX source: {str(e)}",
        )


@jobs_router.get("")
async def list_jobs() -> List[dict]:
    """Return all jobs sorted by creation time descending."""
    job_manager = JobManager()
    all_jobs = job_manager.list_jobs()
    return [
        {
            "job_id": j.job_id,
            "paper_name": j.paper_name,
            "status": j.status.value,
            "progress": j.progress,
            "created_at": j.created_at,
            "updated_at": j.updated_at,
        }
        for j in all_jobs
    ]
