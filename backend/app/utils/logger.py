"""Application and per-job logging utilities.

Job loggers write to ``<temp>/<job_id>/logs/<component>.log``.  Handlers are
cached and can be released with :func:`close_job_loggers`, which JobManager
calls before deleting a job workspace (on Windows an open FileHandler keeps
the log file locked and makes the cleanup ``rmtree`` fail).
"""

import logging
import sys
import threading
from pathlib import Path
from typing import Dict

from app.core.config import settings

# Cache of job loggers so repeated calls do not attach duplicate handlers.
_logger_cache: Dict[str, logging.Logger] = {}
_cache_lock = threading.Lock()


def setup_app_logging() -> None:
    """Configure the root logger for the application (idempotent)."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if not root_logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d]: %(message)s"
        )
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        stdout_handler.setLevel(log_level)
        root_logger.addHandler(stdout_handler)

    logging.getLogger("app.core").info(
        "Application logging initialized at level %s", settings.LOG_LEVEL
    )


def get_job_logger(job_id: str, component: str) -> logging.Logger:
    """Return a job-specific file logger for a given component.

    Args:
        job_id: The UUID of the job.
        component: Component name (e.g. 'system', 'pandoc', 'compiler').

    Returns:
        A configured logging.Logger instance writing to the job's logs folder.
    """
    logger_name = f"job.{job_id}.{component}"

    with _cache_lock:
        if logger_name in _logger_cache:
            return _logger_cache[logger_name]

        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        job_log_dir = Path(settings.TEMP_FOLDER) / job_id / "logs"
        job_log_dir.mkdir(parents=True, exist_ok=True)
        log_file = job_log_dir / f"{component}.log"

        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d]: %(message)s"
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

        logger.addHandler(file_handler)
        _logger_cache[logger_name] = logger
        return logger


def close_job_loggers(job_id: str) -> None:
    """Close and release all cached loggers/file handles for a job.

    Must be called before deleting the job's workspace directory so that the
    log files are not held open (this makes ``rmtree`` fail on Windows).
    """
    prefix = f"job.{job_id}."
    with _cache_lock:
        for name in [n for n in _logger_cache if n.startswith(prefix)]:
            logger = _logger_cache.pop(name)
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass
