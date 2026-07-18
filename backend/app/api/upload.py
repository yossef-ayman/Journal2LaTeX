from fastapi import APIRouter, File, UploadFile, status
from app.services.job_manager import JobManager
from app.models.job import JobMetadata

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("", response_model=JobMetadata, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
) -> JobMetadata:
    """Upload a document and initialize a job workspace.

    Saves the uploaded file to the job's input directory.
    """
    job_manager = JobManager()
    
    # Create the job and its directory layout
    metadata = job_manager.create_job(paper_name=file.filename or "uploaded_paper")
    
    # Save the file to input/ folder
    job_dir = job_manager._get_job_dir(metadata.job_id)
    input_file_path = job_dir / "input" / (file.filename or "paper.docx")
    
    with open(input_file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    return metadata
