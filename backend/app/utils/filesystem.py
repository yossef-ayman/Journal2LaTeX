import os
import shutil
from pathlib import Path
from typing import Union


def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize a path to be an absolute path with forward slashes.

    Args:
        path: The path to normalize.

    Returns:
        The normalized Path object.
    """
    return Path(path).resolve()


def copy_file_or_dir(src: Union[str, Path], dst: Union[str, Path]) -> Path:
    """Copy a file or directory from src to dst.

    Args:
        src: Source path.
        dst: Destination path.

    Returns:
        The destination Path.
    """
    src_path = normalize_path(src)
    dst_path = normalize_path(dst)

    if not src_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {src_path}")

    # Ensure parent directory of destination exists
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if src_path.is_dir():
        if dst_path.exists():
            # If dst exists and is a directory, copytree would fail, so remove it first or copy inside
            shutil.rmtree(dst_path)
        shutil.copytree(src_path, dst_path)
    else:
        shutil.copy2(src_path, dst_path)

    return dst_path


def move_file_or_dir(src: Union[str, Path], dst: Union[str, Path]) -> Path:
    """Move a file or directory from src to dst.

    Args:
        src: Source path.
        dst: Destination path.

    Returns:
        The destination Path.
    """
    src_path = normalize_path(src)
    dst_path = normalize_path(dst)

    if not src_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {src_path}")

    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if dst_path.exists():
        delete_file_or_dir(dst_path)

    shutil.move(str(src_path), str(dst_path))
    return dst_path


def delete_file_or_dir(path: Union[str, Path]) -> None:
    """Delete a file or directory if it exists.

    Args:
        path: Path to delete.
    """
    p = Path(path).resolve()
    if not p.exists():
        return

    if p.is_dir():
        shutil.rmtree(p)
    else:
        p.unlink()
