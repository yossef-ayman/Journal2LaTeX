import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import List, Optional
from app.core.config import settings
from app.models.conversion import PandocResult
from app.utils.logger import get_job_logger


class PandocException(Exception):
    """Base exception for Pandoc service errors."""
    pass


class PandocValidationError(PandocException):
    """Exception raised when document validation fails."""
    pass


class PandocExecutionError(PandocException):
    """Exception raised when Pandoc execution fails."""

    def __init__(self, message: str, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


class PandocService:
    """Service to handle DOCX validation, conversion, and media extraction using Pandoc."""

    def validate_docx(self, docx_path: Path) -> bool:
        """Validate that the given path is a valid DOCX file.

        Checks file extension and zip structure to ensure it's a valid Word Document.

        Args:
            docx_path: The file path to validate.

        Returns:
            True if valid, False otherwise.
        """
        if not docx_path.exists() or not docx_path.is_file():
            return False

        if docx_path.suffix.lower() != ".docx":
            return False

        try:
            with zipfile.ZipFile(docx_path) as zf:
                # word/document.xml must exist in a valid DOCX
                return "word/document.xml" in zf.namelist()
        except zipfile.BadZipFile:
            return False

    def convert_docx_to_latex(self, docx_path: Path, output_tex_path: Path, job_id: str) -> PandocResult:
        """Convert DOCX file to LaTeX format.

        Args:
            docx_path: Path to the input DOCX file.
            output_tex_path: Path where the output LaTeX file will be created.
            job_id: The job ID for logging purposes.

        Returns:
            A PandocResult object.

        Raises:
            PandocValidationError: If input DOCX is invalid.
            PandocExecutionError: If Pandoc execution fails.
        """
        logger = get_job_logger(job_id, "pandoc")
        logger.info("Starting DOCX to LaTeX conversion: %s -> %s", docx_path, output_tex_path)

        if not self.validate_docx(docx_path):
            msg = f"Invalid DOCX file: {docx_path}"
            logger.error(msg)
            raise PandocValidationError(msg)

        # Ensure output folder exists
        output_tex_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            settings.PANDOC_PATH,
            str(docx_path),
            "-s",
            "-t", "latex",
            "-o", str(output_tex_path)
        ]

        logger.debug("Executing Pandoc command: %s", " ".join(cmd))

        try:
            # We run subprocess in a safe way
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8"
            )

            stdout_content = result.stdout or ""
            stderr_content = result.stderr or ""

            if stdout_content:
                logger.debug("Pandoc stdout: %s", stdout_content)
            if stderr_content:
                logger.warning("Pandoc stderr: %s", stderr_content)

            if result.returncode != 0:
                msg = f"Pandoc failed with return code {result.returncode}"
                logger.error("%s. Stderr: %s", msg, stderr_content)
                raise PandocExecutionError(msg, stdout_content, stderr_content)

            logger.info("Conversion completed successfully.")
            return PandocResult(
                success=True,
                output_tex_path=output_tex_path,
                stdout=stdout_content,
                stderr=stderr_content
            )

        except subprocess.SubprocessError as e:
            msg = f"Subprocess error running Pandoc: {str(e)}"
            logger.exception(msg)
            raise PandocExecutionError(msg)
        except Exception as e:
            if not isinstance(e, PandocException):
                msg = f"Unexpected error during Pandoc conversion: {str(e)}"
                logger.exception(msg)
                raise PandocExecutionError(msg)
            raise

    def extract_media(self, docx_path: Path, output_dir: Path, job_id: str) -> PandocResult:
        """Extract media/images from DOCX file using Pandoc.

        Args:
            docx_path: Path to the input DOCX file.
            output_dir: Output directory where extracted media will be stored.
            job_id: The job ID for logging.

        Returns:
            A PandocResult object.

        Raises:
            PandocValidationError: If input DOCX is invalid.
            PandocExecutionError: If Pandoc execution fails.
        """
        logger = get_job_logger(job_id, "pandoc")
        logger.info("Extracting media from DOCX: %s into %s", docx_path, output_dir)

        if not self.validate_docx(docx_path):
            msg = f"Invalid DOCX file: {docx_path}"
            logger.error(msg)
            raise PandocValidationError(msg)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Use pandoc to extract media while outputting a dummy markdown file
        dummy_out = output_dir / "dummy.md"
        cmd = [
            settings.PANDOC_PATH,
            str(docx_path),
            "-t", "markdown",
            "-o", str(dummy_out),
            f"--extract-media={output_dir}"
        ]

        logger.debug("Executing Pandoc media extraction: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8"
            )

            stdout_content = result.stdout or ""
            stderr_content = result.stderr or ""

            # Delete the dummy output file
            if dummy_out.exists():
                dummy_out.unlink()

            if result.returncode != 0:
                msg = f"Pandoc media extraction failed with return code {result.returncode}"
                logger.error("%s. Stderr: %s", msg, stderr_content)
                raise PandocExecutionError(msg, stdout_content, stderr_content)

            # Flat-nest media folder if created by Pandoc
            nested_media = output_dir / "media"
            if nested_media.exists() and nested_media.is_dir():
                for item in nested_media.iterdir():
                    if item.is_file():
                        shutil.move(str(item), str(output_dir / item.name))
                shutil.rmtree(nested_media)

            # Save to original_assets folder for fidelity verification
            orig_assets_dir = output_dir.parent / "original_assets"
            orig_assets_dir.mkdir(parents=True, exist_ok=True)
            for item in output_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, orig_assets_dir / item.name)

            logger.info("Media extraction completed successfully.")
            return PandocResult(
                success=True,
                extracted_media_dir=output_dir,
                stdout=stdout_content,
                stderr=stderr_content
            )

        except subprocess.SubprocessError as e:
            msg = f"Subprocess error running Pandoc for media extraction: {str(e)}"
            logger.exception(msg)
            raise PandocExecutionError(msg)
        except Exception as e:
            if not isinstance(e, PandocException):
                msg = f"Unexpected error during media extraction: {str(e)}"
                logger.exception(msg)
                raise PandocExecutionError(msg)
            raise
