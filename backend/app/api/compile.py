from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.models.job import JobMetadata
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/compile", tags=["Compile"])


class CompileRequest(BaseModel):
    job_id: str
    template_name: str = "default"


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

    # 1. Load template workspace
    if not pipeline_service.load_template(request.job_id, request.template_name):
        return pipeline_service.job_manager.get_job(request.job_id)

    # 2. Render LaTeX content
    tex_path = pipeline_service.render_latex(request.job_id)
    if not tex_path:
        return pipeline_service.job_manager.get_job(request.job_id)

    # 3. Compile LaTeX project to PDF
    pdf_path = pipeline_service.compile(request.job_id)
    if not pdf_path:
        return pipeline_service.job_manager.get_job(request.job_id)

    # 4. Run Fidelity Checker
    job_dir = pipeline_service.job_manager._get_job_dir(request.job_id)
    structure_file = job_dir / "intermediate" / "document_structure.json"
    import json
    from app.models.document import DocumentModel
    try:
        data = json.loads(structure_file.read_text(encoding="utf-8"))
        doc_model = DocumentModel(**data)
        pipeline_service.check_fidelity(request.job_id, doc_model)
    except Exception as e:
        pipeline_service.job_manager.add_error(request.job_id, f"Fidelity check execution error: {str(e)}")

    return pipeline_service.job_manager.get_job(request.job_id)
