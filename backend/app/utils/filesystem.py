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


def read_text_file(file_path: Union[str, Path]) -> str:
    """Read a text file with automatic encoding detection and fallback strategy.
    
    Order of fallbacks:
      - Detected encoding (via charset-normalizer / chardet)
      - UTF-8
      - UTF-8-SIG
      - Windows-1252 (cp1252)
      - Latin-1
    """
    path = Path(file_path).resolve()
    raw_bytes = path.read_bytes()
    
    # 1. Try automatic detection using charset_normalizer
    try:
        import charset_normalizer
        result = charset_normalizer.from_bytes(raw_bytes).best()
        if result and result.encoding and result.confidence > 0.5:
            try:
                return str(result)
            except Exception:
                pass
    except Exception:
        pass

    # Fallback to chardet
    try:
        import chardet
        det = chardet.detect(raw_bytes)
        if det and det.get("encoding") and det.get("confidence", 0) > 0.5:
            try:
                return raw_bytes.decode(det["encoding"])
            except Exception:
                pass
    except Exception:
        pass

    # 2. Sequential Fallback Strategy
    fallbacks = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    for enc in fallbacks:
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
            
    # Absolute final fallback
    return raw_bytes.decode("utf-8", errors="replace")
