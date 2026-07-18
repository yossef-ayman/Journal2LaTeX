from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel


class PandocResult(BaseModel):
    """Structured result from a Pandoc execution step."""

    success: bool
    output_tex_path: Optional[Path] = None
    extracted_media_dir: Optional[Path] = None
    stdout: str = ""
    stderr: str = ""
    errors: List[str] = []


class CompilationResult(BaseModel):
    """Structured result from a LaTeX compilation step."""

    success: bool
    pdf_path: Optional[Path] = None
    log_path: Optional[Path] = None
    stdout: str = ""
    stderr: str = ""
    errors: List[str] = []
