"""Application configuration.

Loads settings from environment variables or a ``.env`` file via
``pydantic-settings`` when available.  Falls back to a minimal
environment-variable reader so the core pipeline can run in environments
where ``pydantic-settings`` is not installed (e.g. stripped CI sandboxes).
"""

import os
from pathlib import Path

try:  # pragma: no cover - import guard
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _HAS_PYDANTIC_SETTINGS = True
except ImportError:  # pragma: no cover
    _HAS_PYDANTIC_SETTINGS = False


_DEFAULTS = {
    # Folders
    "UPLOAD_FOLDER": "uploads",
    "TEMP_FOLDER": "temp",
    "OUTPUT_FOLDER": "output",
    # Log level
    "LOG_LEVEL": "INFO",
    # Executable paths
    "PANDOC_PATH": "pandoc",
    "LATEXMK_PATH": "latexmk",
    "PDFLATEX_PATH": "pdflatex",
    "BIBTEX_PATH": "bibtex",
    "SOFFICE_PATH": "soffice",
    # Timeouts (seconds)
    "SUBPROCESS_TIMEOUT": 120,
    "COMPILE_TIMEOUT": 300,
    # Layout optimizer
    # The SSIM-driven layout-optimization loop is part of the Visual Fidelity
    # Engine roadmap.  It recompiles the document up to MAX_ITERATIONS times
    # and depends on a LibreOffice reference render, which makes production
    # jobs slow and their output environment-sensitive.  It is therefore
    # disabled by default and must be opted into explicitly; the production
    # DOCX -> LaTeX -> PDF pipeline is deterministic without it.
    "OPTIMIZER_ENABLED": False,
    "OPTIMIZER_MAX_ITERATIONS": 12,
    "OPTIMIZER_TARGET_SIMILARITY": 0.95,
    "OPTIMIZER_PATIENCE": 3,
    # Rasterization DPI for visual comparison
    "COMPARISON_DPI": 150,
}


class _SettingsMixin:
    """Shared computed properties for both settings implementations."""

    @property
    def upload_dir(self) -> Path:
        """Absolute path to the upload directory."""
        return Path(self.UPLOAD_FOLDER).resolve()

    @property
    def temp_dir(self) -> Path:
        """Absolute path to the temp (jobs) directory."""
        return Path(self.TEMP_FOLDER).resolve()

    @property
    def output_dir(self) -> Path:
        """Absolute path to the output directory."""
        return Path(self.OUTPUT_FOLDER).resolve()


if _HAS_PYDANTIC_SETTINGS:

    class Settings(BaseSettings, _SettingsMixin):
        """Application settings for Journal2LaTeX."""

        UPLOAD_FOLDER: str = _DEFAULTS["UPLOAD_FOLDER"]
        TEMP_FOLDER: str = _DEFAULTS["TEMP_FOLDER"]
        OUTPUT_FOLDER: str = _DEFAULTS["OUTPUT_FOLDER"]
        LOG_LEVEL: str = _DEFAULTS["LOG_LEVEL"]
        PANDOC_PATH: str = _DEFAULTS["PANDOC_PATH"]
        LATEXMK_PATH: str = _DEFAULTS["LATEXMK_PATH"]
        PDFLATEX_PATH: str = _DEFAULTS["PDFLATEX_PATH"]
        BIBTEX_PATH: str = _DEFAULTS["BIBTEX_PATH"]
        SOFFICE_PATH: str = _DEFAULTS["SOFFICE_PATH"]
        SUBPROCESS_TIMEOUT: int = _DEFAULTS["SUBPROCESS_TIMEOUT"]
        COMPILE_TIMEOUT: int = _DEFAULTS["COMPILE_TIMEOUT"]
        OPTIMIZER_ENABLED: bool = _DEFAULTS["OPTIMIZER_ENABLED"]
        OPTIMIZER_MAX_ITERATIONS: int = _DEFAULTS["OPTIMIZER_MAX_ITERATIONS"]
        OPTIMIZER_TARGET_SIMILARITY: float = _DEFAULTS["OPTIMIZER_TARGET_SIMILARITY"]
        OPTIMIZER_PATIENCE: int = _DEFAULTS["OPTIMIZER_PATIENCE"]
        COMPARISON_DPI: int = _DEFAULTS["COMPARISON_DPI"]

        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

else:  # pragma: no cover - fallback path

    class Settings(_SettingsMixin):
        """Environment-variable-only settings fallback (pydantic-settings absent)."""

        def __init__(self) -> None:
            for key, default in _DEFAULTS.items():
                raw = os.environ.get(key)
                if raw is None:
                    value = default
                elif isinstance(default, bool):
                    value = raw.lower() in ("1", "true", "yes")
                elif isinstance(default, int):
                    value = int(raw)
                elif isinstance(default, float):
                    value = float(raw)
                else:
                    value = raw
                setattr(self, key, value)


settings = Settings()
