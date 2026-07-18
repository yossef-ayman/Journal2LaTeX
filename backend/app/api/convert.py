from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.models.job import JobMetadata
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/convert", tags=["Convert"])


class ConvertRequest(BaseModel):
    job_id: str
    template_name: str = "default"


@router.post("", response_model=JobMetadata)
async def start_conversion(request: ConvertRequest) -> JobMetadata:
    """Trigger the validation, analysis, and asset extraction stages of the pipeline."""
    pipeline_service = PipelineService()
    metadata = pipeline_service.job_manager.get_job(request.job_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {request.job_id} not found",
        )

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
