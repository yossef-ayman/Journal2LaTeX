import logging
import sys
from pathlib import Path
from typing import Dict
from app.core.config import settings

# Global logger cache to prevent adding duplicate handlers
_logger_cache: Dict[str, logging.Logger] = {}


def setup_app_logging() -> None:
    """Configure the root logger for the application."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers if already configured
    if not root_logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d]: %(message)s"
        )

        # Stream handler (stdout)
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        stdout_handler.setLevel(log_level)
        root_logger.addHandler(stdout_handler)

    # Log startup configuration
    logging.getLogger("app.core").info(
        "Application logging initialized at level %s", settings.LOG_LEVEL
    )


def get_job_logger(job_id: str, component: str) -> logging.Logger:
    """Get a job-specific logger for a given component.

    Supported components: 'system', 'pandoc', 'compiler', 'ai'

    Args:
        job_id: The UUID of the job.
        component: The component name ('system', 'pandoc', 'compiler', 'ai').

    Returns:
        A configured logging.Logger instance.
    """
    logger_name = f"job.{job_id}.{component}"

    if logger_name in _logger_cache:
        return _logger_cache[logger_name]

    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  # Job loggers record everything (DEBUG and above)
    logger.propagate = False  # Avoid propagating job-specific logs to the root logger

    # Ensure log directory exists
    job_log_dir = Path(settings.TEMP_FOLDER) / job_id / "logs"
    job_log_dir.mkdir(parents=True, exist_ok=True)

    log_file = job_log_dir / f"{component}.log"

    # Add FileHandler
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d]: %(message)s"
    )
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Clear existing handlers if any (prevent duplicates)
    if logger.handlers:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)

    logger.addHandler(file_handler)
    _logger_cache[logger_name] = logger

    return logger
