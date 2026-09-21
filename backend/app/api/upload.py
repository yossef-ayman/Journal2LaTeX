import io
import re
import zipfile
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from app.services.job_manager import JobManager
from app.models.job import JobMetadata
from app.utils.filesystem import UnsafePathError, safe_join

import tempfile
from app.utils.doc_converter import convert_doc_to_docx

router = APIRouter(prefix="/upload", tags=["Upload"])

ALLOWED_EXTENSIONS = {".docx", ".doc"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
CHUNK_SIZE = 1024 * 1024  # 1 MB

#: A .docx is an OOXML package, i.e. a ZIP.  Both signatures are legal: "PK\x03\x04"
#: for a normal archive and "PK\x05\x06" for an empty one.
_ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
#: A binary .doc file is an OLE CFBF container starting with this magic byte signature.
_DOC_MAGIC = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"


def _sanitize_filename(filename: str) -> str:
    """Strip path separators and dangerous characters from a filename."""
    name = Path(filename).name  # strips any directory components
    # Windows-style separators survive Path().name on POSIX -- strip them too.
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r'[^\w.\- ]', '', name)  # keep safe chars only
    name = name.strip(". ")  # no leading/trailing dots or spaces
    if not name or set(name) <= {"."}:
        return "paper.docx"
    if name.lower().endswith(".doc"):
        name = name[:-4] + ".docx"
    elif not name.lower().endswith(".docx"):
        name = f"{name}.docx"
    return name[:120]


async def _read_bounded(file: UploadFile, limit: int) -> bytes:
    """Read an upload in chunks, aborting as soon as it exceeds *limit*.

    Reading the whole body first and checking its length afterwards means a
    hostile client can force the server to buffer an arbitrary amount of memory
    before the limit is ever consulted.  Streaming with an early abort caps the
    memory a single request can claim at ``limit + CHUNK_SIZE``.
    """
    buffer = bytearray()
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds {limit // (1024 * 1024)} MB limit.",
            )
    return bytes(buffer)


def _validate_docx_bytes(content: bytes) -> None:
    """Confirm the uploaded bytes really are a Word document, not just named one.

    An extension check alone lets a renamed executable, script or arbitrary blob
    through.  A .docx must be a readable ZIP container holding
    ``word/document.xml``; anything else is rejected before it is stored.
    """
    if len(content) < 4 or not content.startswith(_ZIP_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid .docx document.",
        )
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())
            if "word/document.xml" not in names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The uploaded file is not a valid .docx document "
                           "(missing word/document.xml).",
                )
            # Zip-bomb guard: a 50 MB upload that claims to expand to gigabytes
            # is rejected before any downstream tool opens it.
            declared = sum(info.file_size for info in archive.infolist())
            if declared > 20 * MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The uploaded document expands to an implausible size "
                           "and was rejected.",
                )
    except HTTPException:
        raise
    except (zipfile.BadZipFile, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a readable .docx document.",
        )


@router.post("", response_model=JobMetadata, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
) -> JobMetadata:
    """Upload a document (.docx or .doc) and initialize a job workspace.

    The file is validated by extension, by size (enforced while streaming) and
    by content (it must be a real OOXML package) before anything is written to
    disk.
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required.")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Only .docx and .doc files are allowed.",
        )

    # Read content with the size limit enforced during the read, not after it
    content = await _read_bounded(file, MAX_FILE_SIZE)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    # If legacy .doc format, confirm binary OLE CFBF magic bytes before any conversion
    if ext == ".doc":
        if len(content) < 8 or not content.startswith(_DOC_MAGIC):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is not a valid binary .doc document.",
            )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "upload.doc"
            tmp_path.write_bytes(content)
            converted_path = convert_doc_to_docx(tmp_path)
            if converted_path.suffix.lower() == ".docx" and converted_path.is_file():
                content = converted_path.read_bytes()
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not convert the uploaded .doc file to .docx format. Please save it as .docx and re-upload.",
                )

    # Confirm the bytes match the claimed type before storing them
    _validate_docx_bytes(content)

    job_manager = JobManager()
    safe_name = _sanitize_filename(file.filename)
    metadata = job_manager.create_job(paper_name=safe_name)

    # Save the file to input/ folder with safe name
    job_dir = job_manager._get_job_dir(metadata.job_id)
    try:
        input_file_path = safe_join(job_dir / "input", safe_name)
    except UnsafePathError:
        job_manager.cleanup(metadata.job_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The provided filename is not acceptable.",
        )

    try:
        input_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(input_file_path, "wb") as buffer:
            buffer.write(content)
    except OSError as exc:
        # Never leave a half-initialised workspace behind on a write failure.
        job_manager.cleanup(metadata.job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store the uploaded document: {exc}",
        )

    return metadata
