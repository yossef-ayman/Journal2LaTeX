from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Enumeration of possible job states."""

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    ANALYZING_DOCUMENT = "ANALYZING_DOCUMENT"
    EXTRACTING_ASSETS = "EXTRACTING_ASSETS"
    LOADING_TEMPLATE = "LOADING_TEMPLATE"
    RENDERING_LATEX = "RENDERING_LATEX"
    COMPILING = "COMPILING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobMetadata(BaseModel):
    """Pydantic model representing job metadata.json content."""

    job_id: str
    status: JobStatus = JobStatus.CREATED
    progress: int = Field(default=0, ge=0, le=100)
    current_step: str = ""
    created_at: str
    updated_at: str
    paper_name: str = ""
    template_id: str = ""
    template_name: str = ""
    template_version: str = ""
    template_type: str = ""
    output_pdf: str = ""
    output_tex: str = ""
    compile_success: bool = False
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
