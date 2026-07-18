import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional
from app.core.config import settings
from app.models.conversion import CompilationResult
from app.utils.logger import get_job_logger


class LatexCompilerException(Exception):
    """Base exception for LaTeX compiler errors."""
    pass


class LatexCompilationError(LatexCompilerException):
    """Exception raised when compilation fails."""

    def __init__(self, message: str, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


class LatexCompiler:
    """Service to handle compilation of LaTeX documents using pdflatex or latexmk."""

    MAX_PDFLATEX_PASSES = 3

    def _run_pdflatex(self, tex_path: Path, working_dir: Path, job_id: str) -> subprocess.CompletedProcess:
        """Run a single pdflatex pass."""
        cmd = [
            settings.PDFLATEX_PATH,
            "-interaction=nonstopmode",
            "-file-line-error",
            str(tex_path)
        ]
        logger = get_job_logger(job_id, "compiler")
        logger.debug("Executing pdflatex pass: %s in directory: %s", " ".join(cmd), working_dir)
        return subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace"
        )

    def _file_hash(self, path: Path) -> Optional[str]:
        """Return MD5 hex digest of a file, or None if it doesn't exist."""
        if not path.exists():
            return None
        return hashlib.md5(path.read_bytes()).hexdigest()

    def compile_tex(self, tex_path: Path, output_dir: Path, job_id: str) -> CompilationResult:
        """Compile the LaTeX file into a PDF.

        Tries using latexmk if configured/available, otherwise falls back to pdflatex
        with multiple passes to resolve cross-references.

        Args:
            tex_path: Path to the .tex file.
            output_dir: Directory where the final PDF should be saved.
            job_id: The job ID for logging.

        Returns:
            A CompilationResult object.

        Raises:
            LatexCompilationError: If compilation fails.
        """
        logger = get_job_logger(job_id, "compiler")
        logger.info("Starting LaTeX compilation for: %s", tex_path)

        if not tex_path.exists():
            msg = f"LaTeX file not found: {tex_path}"
            logger.error(msg)
            raise LatexCompilationError(msg)

        # Output dir setup
        output_dir.mkdir(parents=True, exist_ok=True)

        working_dir = tex_path.parent
        pdf_path = working_dir / tex_path.with_suffix(".pdf").name
        log_path = tex_path.with_suffix(".log")
        aux_path = tex_path.with_suffix(".aux")

        stdout_combined = ""
        stderr_combined = ""

        # Determine which tool to use
        use_latexmk = False
        if settings.LATEXMK_PATH:
            try:
                check_res = subprocess.run(
                    [settings.LATEXMK_PATH, "-v"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if check_res.returncode == 0:
                    use_latexmk = True
            except FileNotFoundError:
                logger.warning("latexmk executable not found. Falling back to pdflatex.")

        try:
            if use_latexmk:
                logger.info("Using latexmk compiler.")
                cmd = [
                    settings.LATEXMK_PATH,
                    "-pdf",
                    "-interaction=nonstopmode",
                    "-file-line-error",
                    str(tex_path)
                ]
                result = subprocess.run(
                    cmd,
                    cwd=working_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                    encoding="utf-8",
                    errors="replace"
                )
                stdout_combined = result.stdout or ""
                stderr_combined = result.stderr or ""
            else:
                logger.info("Using pdflatex compiler (up to %d passes).", self.MAX_PDFLATEX_PASSES)
                prev_aux_hash = None
                for pass_num in range(1, self.MAX_PDFLATEX_PASSES + 1):
                    logger.info("pdflatex pass %d/%d", pass_num, self.MAX_PDFLATEX_PASSES)
                    result = self._run_pdflatex(tex_path, working_dir, job_id)
                    if result.stdout:
                        stdout_combined += f"\n--- Pass {pass_num} ---\n" + result.stdout
                    if result.stderr:
                        stderr_combined += f"\n--- Pass {pass_num} ---\n" + result.stderr

                    # Check if aux file has stabilized
                    new_hash = self._file_hash(aux_path)
                    if prev_aux_hash is not None and new_hash == prev_aux_hash:
                        logger.info("References stable after pass %d.", pass_num)
                        break
                    prev_aux_hash = new_hash

            # Collect output
            stdout_content = stdout_combined
            stderr_content = stderr_combined

            success = pdf_path.exists()

            # Write compiler output to job logs
            job_logs_dir = working_dir.parent / "logs"
            job_logs_dir.mkdir(parents=True, exist_ok=True)
            compiler_raw_log = job_logs_dir / "compiler_raw.log"
            compiler_raw_log.write_text(f"STDOUT:\n{stdout_content}\n\nSTDERR:\n{stderr_content}", encoding="utf-8")

            if not success:
                msg = f"LaTeX compilation failed. PDF not generated."
                logger.error("%s Check raw logs for details.", msg)
                raise LatexCompilationError(msg, stdout_content, stderr_content)

            # Copy PDF to output folder
            dest_pdf_path = output_dir / "paper.pdf"
            shutil.copy2(pdf_path, dest_pdf_path)

            # Copy standard log to output
            dest_log_path = output_dir / log_path.name
            if log_path.exists():
                shutil.copy2(log_path, dest_log_path)

            logger.info("Compilation completed successfully. PDF generated at: %s", dest_pdf_path)

            return CompilationResult(
                success=True,
                pdf_path=dest_pdf_path,
                log_path=dest_log_path,
                stdout=stdout_content,
                stderr=stderr_content
            )

        except subprocess.SubprocessError as e:
            msg = f"Subprocess error running compiler: {str(e)}"
            logger.exception(msg)
            raise LatexCompilationError(msg)
        except Exception as e:
            if not isinstance(e, LatexCompilerException):
                msg = f"Unexpected error during compilation: {str(e)}"
                logger.exception(msg)
                raise LatexCompilationError(msg)
            raise
