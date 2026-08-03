"""HTTP surface of the Document Engine.

All endpoints live under ``/document-engine``.  Neither the converter's routers
nor the Document Generator's are imported or modified: the three feature sets
share only the FastAPI application object.
"""

from fastapi import APIRouter

from document_engine.routes import analyze, edit, status, suggest

router = APIRouter(prefix="/document-engine", tags=["Document Engine"])
router.include_router(status.router)
router.include_router(analyze.router)
router.include_router(edit.router)
router.include_router(suggest.router)

__all__ = ["router"]
