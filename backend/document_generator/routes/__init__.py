"""HTTP surface of the Document Generator module.

All endpoints live under ``/document-generator``.  The converter's routers are
neither imported nor modified: the two feature sets share only the FastAPI
application object.
"""

from fastapi import APIRouter

from document_generator.routes import download, generate, settings, templates

router = APIRouter(prefix="/document-generator", tags=["Document Generator"])
router.include_router(templates.router)
router.include_router(generate.router)
router.include_router(download.router)
router.include_router(settings.router)

__all__ = ["router"]
