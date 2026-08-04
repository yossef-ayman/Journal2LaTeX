import re
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from app.services.job_manager import JobManager
from app.services.project_packager import ProjectPackager, ProjectPackagerError
from app.utils.filesystem import is_valid_job_id, is_within

router = APIRouter(prefix="/download", tags=["Download"])


def _safe_stem(name: str, fallback: str = "document") -> str:
    """Reduce a user-supplied name to a safe download filename stem."""
    stem = Path(name or "").stem
    stem = re.sub(r"[^\w.\- ]", "", stem).strip()
    # A name of dots only ("..") would still be dangerous in a header.
    if not stem or set(stem) <= {".", " "}:
        return fallback
    return stem[:120]


def _load_job(job_id: str):
    """Validate the job ID and load its metadata, or raise 404."""
    if not is_valid_job_id(job_id):
        # Same response as a genuinely unknown job: a malformed ID must not be
        # distinguishable from a missing one, and must never reach a path join.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )
    job_manager = JobManager()
    metadata = job_manager.get_job(job_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )
    return job_manager, metadata


@router.get("/{job_id}", response_class=FileResponse)
async def download_output(job_id: str) -> FileResponse:
    """Download the compiled PDF for a completed job.

    Returns the real output PDF if it exists, or a 404 if not yet compiled.
    """
    job_manager, metadata = _load_job(job_id)

    job_dir = job_manager._get_job_dir(job_id)

    # Check real PDF locations in priority order
    candidates = [
        job_dir / "output" / "paper.pdf",
        job_dir / "output" / "output.pdf",
    ]

    pdf_path: Path | None = None
    for candidate in candidates:
        # Never serve through a symlink, and never outside this job's workspace.
        if candidate.is_file() and not candidate.is_symlink() \
                and is_within(job_dir, candidate.resolve()):
            pdf_path = candidate
            break

    if not pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not available. Ensure the compile stage has completed successfully.",
        )

    safe_name = _safe_stem(metadata.paper_name)
    return FileResponse(
        path=pdf_path,
        filename=f"{safe_name}.pdf",
        media_type="application/pdf",
    )


@router.get("/{job_id}/project", response_class=FileResponse)
async def download_project(job_id: str) -> FileResponse:
    """Download the complete LaTeX project for a job as a single ZIP archive.

    The archive contains everything needed to compile the document offline --
    ``main.tex``, the template's class/style/bibliography-style files, every
    ``.bib``, all figures and logos, bundled fonts, and any further generated
    asset -- with the original folder structure preserved.  Extracting it and
    running ``latexmk -pdf main.tex`` reproduces the PDF.

    LaTeX build artefacts are excluded so the first build starts clean.
    """
    _job_manager, metadata = _load_job(job_id)

    try:
        zip_path, temp_dir, _report = ProjectPackager().build_project_zip(job_id)
    except ProjectPackagerError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to package the LaTeX project: {exc}",
        )

    safe_name = _safe_stem(metadata.paper_name, fallback="latex-project")
    # The temp directory is removed only after the response body has been sent.
    return FileResponse(
        path=zip_path,
        filename=f"{safe_name}.zip",
        media_type="application/zip",
        background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
    )
