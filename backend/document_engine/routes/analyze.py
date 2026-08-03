"""Upload a .docx, get back what the engine understood.

Read-only.  The uploaded file is parsed in memory, never stored, and never sent
anywhere near the Word -> LaTeX converter or the Document Generator: this
endpoint shares nothing with them but the application object.

The response is the shape the editing UI needs, and it deliberately carries the
engine's uncertainty with it.  Every node reports the ``confidence`` it was
extracted with and the ``evidence`` that produced it, and the document reports
what it failed to find at all.  A UI built on this can put the guesses in front
of the user first, which is the whole reason the fields exist.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from document_engine.extract import SemanticExtractor
from document_engine.model.nodes import Document, Node, Section
from document_engine.ooxml.bytes import OOXMLEditError
from document_engine.ooxml.package import Package

router = APIRouter()

# Large enough for any manuscript, small enough that a mistaken upload fails
# fast rather than filling memory.
_MAX_BYTES = 64 * 1024 * 1024


def _base(node: Optional[Node]) -> Optional[Dict[str, Any]]:
    if node is None:
        return None
    anchor = node.anchor
    return {
        "id": node.id,
        "confidence": round(node.confidence, 3),
        "evidence": list(node.evidence),
        "anchor": (
            {"part": anchor.part, "start": anchor.start, "end": anchor.end}
            if anchor
            else None
        ),
    }


def _text(node) -> Optional[Dict[str, Any]]:
    payload = _base(node)
    if payload is None:
        return None
    payload["text"] = node.text
    return payload


def _section(section: Section) -> Dict[str, Any]:
    payload = _base(section) or {}
    payload.update(
        {
            "title": section.title,
            "level": section.level,
            "number": section.number,
            "kind": section.kind,
            "content": [
                {
                    "id": block.id,
                    "kind": block.kind,
                    "item": _text(block.item) if block.item is not None else None,
                }
                for block in section.content
            ],
            "children": [_section(child) for child in section.children],
        }
    )
    return payload


def _metadata(document: Document) -> Dict[str, Any]:
    meta = document.metadata
    return {
        "title": _text(meta.title),
        "subtitle": _text(meta.subtitle),
        "authors": [
            dict(
                _base(author) or {},
                name=author.name,
                markers=author.markers,
                email=author.email,
                is_corresponding=author.is_corresponding,
                affiliation_ids=author.affiliation_ids,
            )
            for author in meta.authors
        ],
        "affiliations": [
            dict(_base(a) or {}, text=a.text, marker=a.marker)
            for a in meta.affiliations
        ],
        "emails": meta.emails,
        "keywords": meta.keywords,
        "abstract": _section(meta.abstract) if meta.abstract else None,
        "doi": meta.doi,
        "received": meta.received,
        "accepted": meta.accepted,
        "published": meta.published,
    }


def _document(document: Document) -> Dict[str, Any]:
    return {
        "source": document.source,
        "metadata": _metadata(document),
        "sections": [_section(s) for s in document.sections],
        "references": [
            dict(_text(r) or {}, marker=r.marker, ordered=r.ordered)
            for r in document.references
        ],
        "tables": [
            dict(
                _base(t) or {},
                caption=_text(t.caption),
                rows=t.rows,
                columns=t.columns,
                header_rows=t.header_rows,
                cells=t.cells,
            )
            for t in document.tables
        ],
        "figures": [
            dict(
                _base(f) or {},
                caption=_text(f.caption),
                relationship_ids=f.relationship_ids,
                width_emu=f.width_emu,
                height_emu=f.height_emu,
                inline=f.inline,
            )
            for f in document.figures
        ],
        "equations": [
            dict(_text(e) or {}, number=e.number, display=e.display)
            for e in document.equations
        ],
        "headers": [_text(h) for h in document.headers],
        "footers": [_text(f) for f in document.footers],
        "observations": document.observations,
        "warnings": document.warnings,
    }


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Parse and understand one uploaded manuscript."""
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="the uploaded file is empty")
    if len(payload) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="the uploaded file is too large")

    try:
        package = Package.open(io.BytesIO(payload))
    except (OOXMLEditError, KeyError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail=f"this file could not be read as a Word document: {error}",
        ) from error

    if package.document is None:
        raise HTTPException(
            status_code=400,
            detail="this .docx has no word/document.xml part",
        )

    document = SemanticExtractor(package).extract(source=file.filename or "upload.docx")
    return _document(document)


__all__ = ["router"]
