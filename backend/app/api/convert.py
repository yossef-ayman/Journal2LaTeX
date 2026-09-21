from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.models.job import JobMetadata
from app.services.pipeline_service import PipelineService
from app.services.template_manager import TemplateManager

from app.utils.filesystem import is_valid_job_id

router = APIRouter(prefix="/convert", tags=["Convert"])


class ConvertRequest(BaseModel):
    job_id: str
    template_id: Optional[str] = None
    template_name: Optional[str] = "default"


@router.post("", response_model=JobMetadata)
async def start_conversion(request: ConvertRequest) -> JobMetadata:
    """Trigger the validation, analysis, and asset extraction stages of the pipeline."""
    if not is_valid_job_id(request.job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {request.job_id} not found",
        )

    pipeline_service = PipelineService()
    metadata = pipeline_service.job_manager.get_job(request.job_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {request.job_id} not found",
        )

    # Resolve template metadata
    manager = TemplateManager()
    resolved_id = request.template_id or request.template_name or "default"
    try:
        template_meta = manager.get_template_metadata(resolved_id)
    except Exception:
        template_meta = {
            "template_id": resolved_id,
            "display_name": resolved_id,
            "version": "1.0.0",
            "template_type": "built_in"
        }

    # Update job metadata fields
    metadata.template_id = template_meta.get("template_id") or resolved_id
    metadata.template_name = template_meta.get("display_name") or resolved_id
    metadata.template_version = template_meta.get("version") or "1.0.0"
    metadata.template_type = template_meta.get("template_type") or "built_in"
    pipeline_service.job_manager._save_metadata(metadata)

    # 1. Validate
    if not pipeline_service.validate(request.job_id, metadata.paper_name):
        return pipeline_service.job_manager.get_job(request.job_id)

    # 2. Analyze
    doc_model = pipeline_service.analyze(request.job_id, metadata.paper_name)
    if not doc_model:
        return pipeline_service.job_manager.get_job(request.job_id)

    # 3. Extract Assets
    if not pipeline_service.extract_assets(request.job_id, metadata.paper_name):
        return pipeline_service.job_manager.get_job(request.job_id)

    # 4. Classify Assets
    if not pipeline_service.analyze_assets(request.job_id, doc_model):
        return pipeline_service.job_manager.get_job(request.job_id)

    return pipeline_service.job_manager.get_job(request.job_id)
