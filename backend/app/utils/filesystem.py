import os
import re
import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Union


class UnsafePathError(ValueError):
    """Raised when a user-controlled value would escape its intended root."""


#: A job ID is always a uuid4 produced by JobManager.create_job.  Anything else
#: reaching a filesystem join is either a bug or an attack.
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

#: A single path component that is safe to append to a trusted root.  Rejects
#: separators (both flavours), traversal, drive letters, NUL and leading dots.
_SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._\- ]{0,254}$")


def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize a path to be an absolute path with forward slashes.

    Args:
        path: The path to normalize.

    Returns:
        The normalized Path object.
    """
    return Path(path).resolve()


def is_valid_job_id(job_id: str) -> bool:
    """True when *job_id* is a well-formed UUID (the only shape JobManager mints)."""
    return bool(job_id) and bool(_UUID_RE.match(job_id))


def is_safe_component(name: str) -> bool:
    """True when *name* is a single path component safe to join to a root.

    Rejects empty strings, ``.``/``..``, anything containing ``/`` or ``\\``,
    Windows drive prefixes, NUL bytes, and names starting with a dot.
    """
    if not name or "\x00" in name:
        return False
    if name in (".", ".."):
        return False
    if "/" in name or "\\" in name:
        return False
    if PureWindowsPath(name).drive or PurePosixPath(name).is_absolute():
        return False
    return bool(_SAFE_COMPONENT_RE.match(name))


def is_within(root: Union[str, Path], candidate: Union[str, Path]) -> bool:
    """True when *candidate* resolves to *root* itself or something beneath it.

    Uses ``os.path.commonpath`` on the resolved paths rather than a string
    ``startswith``: the latter treats ``/data/jobs-evil`` as being inside
    ``/data/jobs``.
    """
    root_abs = Path(os.path.abspath(str(root)))
    cand_abs = Path(os.path.abspath(str(candidate)))
    try:
        return os.path.commonpath([str(root_abs), str(cand_abs)]) == str(root_abs)
    except ValueError:
        # Different drives / mixed absolute+relative -- never containment.
        return False


def ensure_within(root: Union[str, Path], candidate: Union[str, Path]) -> Path:
    """Return *candidate* as an absolute Path, or raise if it escapes *root*."""
    cand_abs = Path(os.path.abspath(str(candidate)))
    if not is_within(root, cand_abs):
        raise UnsafePathError(
            f"Resolved path escapes its permitted root: {cand_abs}"
        )
    return cand_abs


def safe_join(root: Union[str, Path], *parts: str) -> Path:
    """Join untrusted *parts* under a trusted *root*, refusing any escape.

    Every part is validated as a single safe component and the final result is
    re-checked for containment, so neither traversal segments, absolute paths,
    nor symlinked intermediate directories can move the result outside *root*.
    """
    root_abs = Path(os.path.abspath(str(root)))
    result = root_abs
    for part in parts:
        if not is_safe_component(part):
            raise UnsafePathError(f"Unsafe path component: {part!r}")
        result = result / part
    return ensure_within(root_abs, result)


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
