import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for Journal2LaTeX.

    Loads configurations from environment variables or a .env file.
    """

    # Folders
    UPLOAD_FOLDER: str = "uploads"
    TEMP_FOLDER: str = "temp"
    OUTPUT_FOLDER: str = "output"

    # Log Level
    LOG_LEVEL: str = "INFO"

    # Executable paths
    PANDOC_PATH: str = "pandoc"
    LATEXMK_PATH: str = "latexmk"
    PDFLATEX_PATH: str = "pdflatex"
    BIBTEX_PATH: str = "bibtex"

    # Settings config to allow loading from dotenv
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def upload_dir(self) -> Path:
        """Get the absolute path to the upload directory."""
        return Path(self.UPLOAD_FOLDER).resolve()

    @property
    def temp_dir(self) -> Path:
        """Get the absolute path to the temp directory."""
        return Path(self.TEMP_FOLDER).resolve()

    @property
    def output_dir(self) -> Path:
        """Get the absolute path to the output directory."""
        return Path(self.OUTPUT_FOLDER).resolve()


# Instantiate settings
settings = Settings()
