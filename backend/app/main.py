import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.upload import router as upload_router
from app.api.convert import router as convert_router
from app.api.compile import router as compile_router
from app.api.download import router as download_router
from app.api.health import router as health_router
from app.api.job import router as job_router
from app.api.job import jobs_router
from app.api.templates import router as templates_router
from app.utils.logger import setup_app_logging

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown configuration."""
    # Startup actions
    setup_app_logging()
    logger.info("Starting Journal2LaTeX Backend Application")
    yield
    # Shutdown actions
    logger.info("Shutting down Journal2LaTeX Backend Application")


app = FastAPI(
    title="Journal2LaTeX API",
    description="Backend foundation and job management API for Journal2LaTeX desktop application.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # False required when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught global exceptions gracefully."""
    logger.exception("An unexpected error occurred: %s", str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred."},
    )


# Include Routers
app.include_router(upload_router)
app.include_router(convert_router)
app.include_router(compile_router)
app.include_router(download_router)
app.include_router(health_router)
app.include_router(job_router)
app.include_router(jobs_router)
app.include_router(templates_router)

# Optional feature module: the Document Generator (acceptance letters, invoices).
# Mounted defensively and additively -- it is an independent feature that shares
# nothing with the Word -> LaTeX pipeline above.  Deleting the
# ``document_generator`` package removes the feature and leaves the converter
# behaving exactly as it did before, which is why this import is guarded rather
# than listed with the converter's own routers.
try:
    from document_generator import router as document_generator_router
except Exception as exc:  # pragma: no cover - the converter must start regardless
    logger.warning("Document Generator module not loaded: %s", exc)
else:
    app.include_router(document_generator_router)
    logger.info("Document Generator module mounted at /document-generator")

# Optional feature module: the Document Engine (understanding and editing whole
# manuscripts).  Mounted on exactly the same terms as the generator above -- a
# guarded, additive import -- because it is likewise an independent feature that
# shares no state with the Word -> LaTeX pipeline, and deleting the
# ``document_engine`` package must leave everything else behaving as it did.
try:
    from document_engine import router as document_engine_router
except Exception as exc:  # pragma: no cover - the converter must start regardless
    logger.warning("Document Engine module not loaded: %s", exc)
else:
    app.include_router(document_engine_router)
# Optional feature module: PDF Analyzer (PyMuPDF standalone analyzer).
try:
    import sys
    from pathlib import Path
    pdf_analyzer_path = Path(__file__).resolve().parents[2] / "pdf_analyzer"
    if str(pdf_analyzer_path) not in sys.path:
        sys.path.insert(0, str(pdf_analyzer_path))
    from main import app as pdf_analyzer_app
except Exception as exc:
    logger.warning("PDF Analyzer module not loaded: %s", exc)
else:
    app.mount("/pdf-analyzer-standalone", pdf_analyzer_app)
    logger.info("PDF Analyzer module mounted at /pdf-analyzer-standalone")

