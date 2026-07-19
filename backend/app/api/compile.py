from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.models.job import JobMetadata
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/compile", tags=["Compile"])


class CompileRequest(BaseModel):
    job_id: str
    template_id: Optional[str] = None
    template_name: Optional[str] = None


@router.post("", response_model=JobMetadata)
async def compile_latex(request: CompileRequest) -> JobMetadata:
    """Trigger the template loading, LaTeX rendering, and PDF compilation stages of the pipeline."""
    pipeline_service = PipelineService()
    metadata = pipeline_service.job_manager.get_job(request.job_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {request.job_id} not found",
        )
    
    # Clear errors (and a stale FAILED status) for the new compilation run
    metadata.errors = []
    if metadata.status.value == "FAILED":
        from app.models.job import JobStatus
        metadata.status = JobStatus.LOADING_TEMPLATE
    pipeline_service.job_manager._save_metadata(metadata)

    # Determine template ID to use (request.template_id -> request.template_name -> metadata.template_id -> "default")
    template_id = (
        request.template_id or
        metadata.template_id or
        request.template_name or
        metadata.template_name or
        "default"
    )

    # 1. Load template workspace
    if not pipeline_service.load_template(request.job_id, template_id):
        return pipeline_service.job_manager.get_job(request.job_id)

    # Persist the selected template ID and info into the job's metadata
    metadata.template_id = template_id
    try:
        t_meta = pipeline_service.template_manager.get_template_metadata(template_id)
        if t_meta:
            metadata.template_name = t_meta.get("display_name", template_id)
            metadata.template_version = t_meta.get("version", "1.0.0")
            metadata.template_type = t_meta.get("template_type", "built_in")
    except Exception:
        pass
    pipeline_service.job_manager._save_metadata(metadata)

    # 2. Render LaTeX content
    tex_path = pipeline_service.render_latex(request.job_id)
    if not tex_path:
        return pipeline_service.job_manager.get_job(request.job_id)

    # 3. Compile LaTeX project to PDF
    pdf_path = pipeline_service.compile(request.job_id)
    if not pdf_path:
        return pipeline_service.job_manager.get_job(request.job_id)

    # 4. Run fidelity checker + optimization loop on the saved document model
    doc_model = pipeline_service.load_document_model(request.job_id)
    if doc_model:
        pipeline_service.check_fidelity(request.job_id, doc_model)
    else:
        pipeline_service.job_manager.add_error(
            request.job_id,
            "Fidelity check skipped: document_structure.json missing or invalid. Run /convert first.",
            fatal=False,
        )

    return pipeline_service.job_manager.get_job(request.job_id)
