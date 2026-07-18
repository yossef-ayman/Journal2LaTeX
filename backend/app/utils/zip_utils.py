import zipfile
from pathlib import Path
from typing import Union
from app.utils.filesystem import normalize_path


def zip_directory(dir_path: Union[str, Path], zip_file_path: Union[str, Path]) -> Path:
    """Zip the contents of a directory into a zip archive.

    Args:
        dir_path: Path to the directory to zip.
        zip_file_path: Path to the output zip file.

    Returns:
        The path to the created zip file.
    """
    src_dir = normalize_path(dir_path)
    archive_path = normalize_path(zip_file_path)

    if not src_dir.exists() or not src_dir.is_dir():
        raise FileNotFoundError(f"Source directory does not exist or is not a directory: {src_dir}")

    archive_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk(src_dir):
            for file in files:
                file_path = Path(root) / file
                # Store files relative to the src_dir
                archive_name = file_path.relative_to(src_dir)
                zip_file.write(file_path, archive_name)

    return archive_path


import os


def extract_zip(zip_file_path: Union[str, Path], extract_dir: Union[str, Path]) -> Path:
    """Extract a zip archive into a destination directory.

    Args:
        zip_file_path: Path to the zip archive.
        extract_dir: Destination directory path.

    Returns:
        The destination directory path.
    """
    archive_path = normalize_path(zip_file_path)
    dest_dir = normalize_path(extract_dir)

    if not archive_path.exists() or not archive_path.is_file():
        raise FileNotFoundError(f"Zip file does not exist or is not a file: {archive_path}")

    dest_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path, "r") as zip_ref:
        zip_ref.extractall(dest_dir)

    return dest_dir
