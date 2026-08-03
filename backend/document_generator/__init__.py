"""Document Generator -- an independent document-production module.

This package is deliberately self-contained.  It produces journal
correspondence (acceptance letters, invoices, and whatever document types are
registered later) from permanently stored master Word templates, in batch, with
a matching PDF for every DOCX.

It is **not** part of the DOCX -> LaTeX -> PDF converter and shares no state
with it.  The only thing it borrows is the converter's metadata extraction --
read-only, through a narrow adapter in ``services.metadata_extractor`` -- so
paper titles and authors are recognised by the same well-tested parser rather
than a second implementation that could disagree with it.

Removing this directory removes the feature: ``app.main`` mounts the router
inside a guarded import, so the converter keeps working untouched.
"""

from typing import Any

__all__ = ["router"]


def __getattr__(name: str) -> Any:
    """Expose ``document_generator.router`` without importing the web layer eagerly.

    Resolved on access so importing a service (or a test) does not pull FastAPI
    and the whole route tree in behind it, and so the services stay usable from a
    script or a worker that has no HTTP stack at all.
    """
    if name == "router":
        from document_generator.routes import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
