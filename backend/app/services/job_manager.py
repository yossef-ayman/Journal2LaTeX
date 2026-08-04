import datetime
import json
import os
import threading
import uuid
from collections import defaultdict
from pathlib import Path
from typing import List, Optional, Union
from app.core.config import settings
from app.models.job import JobMetadata, JobStatus
from app.utils.filesystem import (
    UnsafePathError,
    delete_file_or_dir,
    is_valid_job_id,
    normalize_path,
    safe_join,
)
from app.utils.logger import close_job_loggers, get_job_logger


# Process-wide locks serializing read-modify-write cycles on each job's
# metadata.json (JobManager instances are created per-request, so the locks
# must live at module scope).
_job_locks: "defaultdict[str, threading.Lock]" = defaultdict(threading.Lock)
_job_locks_guard = threading.Lock()


def _lock_for(job_id: str) -> threading.Lock:
    with _job_locks_guard:
        return _job_locks[job_id]


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

        This is the single chokepoint where a job ID becomes a filesystem path,
        so the ID is validated here: it must be a well-formed UUID (the only
        shape ``create_job`` ever mints) and the join must stay inside the
        workspace root.  Callers reach this via ``get_job``, which converts the
        rejection into a plain "not found".

        Args:
            job_id: UUID of the job.

        Returns:
            The Path to the job directory.

        Raises:
            UnsafePathError: if *job_id* is not a valid UUID.
        """
        if not is_valid_job_id(job_id):
            raise UnsafePathError(f"Invalid job identifier: {job_id!r}")
        return safe_join(self.temp_dir, job_id)

    def list_jobs(self) -> List[JobMetadata]:
        """List all known jobs sorted by creation time descending.

        Returns:
            A list of JobMetadata objects for all discoverable jobs.
        """
        if not self.temp_dir.exists():
            return []

        jobs: List[JobMetadata] = []
        for entry in self.temp_dir.iterdir():
            if not entry.is_dir():
                continue
            metadata_path = entry / "metadata.json"
            if not metadata_path.exists():
                continue
            try:
                data = json.loads(metadata_path.read_text(encoding="utf-8"))
                jobs.append(JobMetadata(**data))
            except Exception:
                continue

        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs

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
        # Atomic write: dump to a temp file in the same directory, then replace,
        # so a crash or concurrent reader never observes a half-written JSON.
        tmp_path = metadata_path.with_suffix(".json.tmp")
        tmp_path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp_path, metadata_path)

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
        try:
            metadata_path = self._get_metadata_path(job_id)
        except UnsafePathError:
            # A malformed / hostile job ID is reported exactly like a missing
            # job, so callers return 404 and nothing leaks about the layout.
            return None
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
        with _lock_for(job_id):
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
        with _lock_for(job_id):
            metadata = self.get_job(job_id)
            if not metadata:
                return None
            metadata.progress = max(0, min(100, progress))
            metadata.current_step = current_step
            self._save_metadata(metadata)

        sys_logger = get_job_logger(job_id, "system")
        sys_logger.info("Progress updated to %d%%: %s", progress, current_step)

        return metadata

    def add_error(self, job_id: str, error: str, fatal: bool = True) -> Optional[JobMetadata]:
        """Add an error message to the job metadata.

        Args:
            job_id: UUID of the job.
            error: The error message string.

        Returns:
            The updated JobMetadata object if found, else None.
        """
        with _lock_for(job_id):
            metadata = self.get_job(job_id)
            if not metadata:
                return None
            metadata.errors.append(error)
            if fatal:
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
        with _lock_for(job_id):
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
        try:
            job_dir = self._get_job_dir(job_id)
        except UnsafePathError:
            return False
        if not job_dir.exists():
            return True

        # Release open log file handles first; otherwise rmtree fails on
        # Windows because the FileHandler keeps logs/<component>.log locked.
        close_job_loggers(job_id)
        try:
            delete_file_or_dir(job_dir)
            return True
        except Exception:
            return False
