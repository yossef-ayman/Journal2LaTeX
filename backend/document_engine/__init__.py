"""Document Engine -- understanding and editing arbitrary Word manuscripts.

This package parses a research paper in ``.docx``, extracts its semantic
structure, lets an operator edit that structure, and writes the changes back
into *the same file*.  It is not a template system and it is not a converter.

Three boundaries define it, and all three are deliberate:

* It never regenerates a document.  Every semantic object it extracts holds a
  byte-range anchor into the original package, and editing rewrites only the
  anchored bytes.  Styles, tables, images, headers, footers, bookmarks, fields,
  section breaks, numbering and formatting survive because their bytes are never
  touched -- not because a writer tried to reproduce them.
* It shares nothing with the Word -> LaTeX converter in ``app``, which is a
  stable, completed module and is only ever read.
* It does not replace the Document Generator.  That module produces batch
  correspondence from stored master templates, which is a different job; the two
  live side by side and share exactly one thing, the byte-level OOXML editor
  that now lives in ``document_engine.ooxml.bytes``.

Removing this directory removes the feature: ``app.main`` mounts the router
inside a guarded import, exactly as it does for the Document Generator.
"""

from typing import Any

__all__ = ["router"]


def __getattr__(name: str) -> Any:
    """Expose ``document_engine.router`` without importing the web layer eagerly.

    Resolved on access so importing a service -- or a test, or a script with no
    HTTP stack at all -- does not pull FastAPI and the whole route tree in behind
    it.  The same pattern the Document Generator uses, for the same reason.
    """
    if name == "router":
        from document_engine.routes import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
