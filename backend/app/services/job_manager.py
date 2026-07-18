import datetime
import json
import uuid
from pathlib import Path
from typing import Optional, Union
from app.core.config import settings
from app.models.job import JobMetadata, JobStatus
from app.utils.filesystem import delete_file_or_dir, normalize_path
from app.utils.logger import get_job_logger


class JobManager:
    """Service class for managing jobs and their workspaces."""

    def __init__(self, temp_folder: Optional[Union[str, Path]] = None) -> None:
        """Initialize JobManager.

        Args:
            temp_folder: Directory to store job data. Defaults to settings.TEMP_FOLDER.
        """
        self.temp_dir = normalize_path(temp_folder or settings.TEMP_FOLDER)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _get_job_dir(self, job_id: str) -> Path:
        """Get the directory path for a specific job.

        Args:
            job_id: UUID of the job.

        Returns:
            The Path to the job directory.
        """
        return self.temp_dir / job_id

    def _get_metadata_path(self, job_id: str) -> Path:
        """Get the file path for a job's metadata.json.

        Args:
            job_id: UUID of the job.

        Returns:
            The Path to metadata.json.
        """
        return self._get_job_dir(job_id) / "metadata.json"

    def _save_metadata(self, metadata: JobMetadata) -> None:
        """Save job metadata to metadata.json.

        Args:
            metadata: The JobMetadata object to save.
        """
        metadata_path = self._get_metadata_path(metadata.job_id)
        metadata.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        metadata_path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")

    def create_job(self, paper_name: str = "", template_name: str = "") -> JobMetadata:
        """Create a new job and initialize its folder structure and metadata.json.

        Args:
            paper_name: Optional name of the paper.
            template_name: Optional name of the template.

        Returns:
            The newly created JobMetadata object.
        """
        job_id = str(uuid.uuid4())
        job_dir = self._get_job_dir(job_id)

        # Create job subfolders
        subfolders = ["input", "template", "intermediate", "output", "logs"]
        for folder in subfolders:
            (job_dir / folder).mkdir(parents=True, exist_ok=True)

        # Initialize metadata
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        metadata = JobMetadata(
            job_id=job_id,
            status=JobStatus.CREATED,
            progress=0,
            current_step="Initializing job workspace",
            created_at=now_str,
            updated_at=now_str,
            paper_name=paper_name,
            template_name=template_name,
        )

        # Save metadata
        self._save_metadata(metadata)

        # Log job creation in the job's system log
        sys_logger = get_job_logger(job_id, "system")
        sys_logger.info("Job %s workspace created successfully", job_id)

        return metadata

    def get_job(self, job_id: str) -> Optional[JobMetadata]:
        """Retrieve job metadata by job ID.

        Args:
            job_id: UUID of the job.

        Returns:
            The JobMetadata object if found, else None.
        """
        metadata_path = self._get_metadata_path(job_id)
        if not metadata_path.exists():
            return None

        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            return JobMetadata(**data)
        except Exception as e:
            # Log parsing error if metadata is corrupt
            root_logger = get_job_logger(job_id, "system")
            root_logger.error("Failed to read metadata for job %s: %s", job_id, str(e))
            return None

    def set_status(self, job_id: str, status: JobStatus) -> Optional[JobMetadata]:
        """Update the status of a job.

        Args:
            job_id: UUID of the job.
            status: The new JobStatus.

        Returns:
            The updated JobMetadata object if found, else None.
        """
        metadata = self.get_job(job_id)
        if not metadata:
            return None

        metadata.status = status
        self._save_metadata(metadata)

        sys_logger = get_job_logger(job_id, "system")
        sys_logger.info("Job status updated to: %s", status.value)

        return metadata

    def update_progress(self, job_id: str, progress: int, current_step: str) -> Optional[JobMetadata]:
        """Update progress and current step of a job.

        Args:
            job_id: UUID of the job.
            progress: Progress percentage (0 to 100).
            current_step: Description of the current step.

        Returns:
            The updated JobMetadata object if found, else None.
        """
        metadata = self.get_job(job_id)
        if not metadata:
            return None

        metadata.progress = max(0, min(100, progress))
        metadata.current_step = current_step
        self._save_metadata(metadata)

        sys_logger = get_job_logger(job_id, "system")
        sys_logger.info("Progress updated to %d%%: %s", progress, current_step)

        return metadata

    def add_error(self, job_id: str, error: str) -> Optional[JobMetadata]:
        """Add an error message to the job metadata.

        Args:
            job_id: UUID of the job.
            error: The error message string.

        Returns:
            The updated JobMetadata object if found, else None.
        """
        metadata = self.get_job(job_id)
        if not metadata:
            return None

        metadata.errors.append(error)
        # Automatically mark as FAILED when an error is added
        metadata.status = JobStatus.FAILED
        self._save_metadata(metadata)

        sys_logger = get_job_logger(job_id, "system")
        sys_logger.error("Job error added: %s", error)

        return metadata

    def add_warning(self, job_id: str, warning: str) -> Optional[JobMetadata]:
        """Add a warning message to the job metadata.

        Args:
            job_id: UUID of the job.
            warning: The warning message string.

        Returns:
            The updated JobMetadata object if found, else None.
        """
        metadata = self.get_job(job_id)
        if not metadata:
            return None

        metadata.warnings.append(warning)
        self._save_metadata(metadata)

        sys_logger = get_job_logger(job_id, "system")
        sys_logger.warning("Job warning added: %s", warning)

        return metadata

    def cleanup(self, job_id: str) -> bool:
        """Clean up and delete a job's entire workspace directory.

        Args:
            job_id: UUID of the job.

        Returns:
            True if cleanup was successful or directory did not exist, else False.
        """
        job_dir = self._get_job_dir(job_id)
        if not job_dir.exists():
            return True

        try:
            delete_file_or_dir(job_dir)
            return True
        except Exception:
            return False
