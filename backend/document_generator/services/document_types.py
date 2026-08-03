"""Registry of producible document types.

Each entry pairs a master-template slot with the file name its output takes
inside a paper's folder.  Adding a certificate, a review letter or a copyright
form later is a single entry here plus an uploaded template -- no route,
service, storage or UI change is required, because every other part of the
module iterates this registry rather than naming the types it knows about.
"""

from __future__ import annotations

from typing import Dict, List

from document_generator.models.schemas import DocumentTypeInfo

# Ordered: the UI and the generated output follow this sequence.
_REGISTRY: Dict[str, DocumentTypeInfo] = {
    "acceptance": DocumentTypeInfo(
        key="acceptance",
        label="Acceptance Template",
        output_basename="Acceptance",
        description="Acceptance letter issued to the corresponding author.",
    ),
    "invoice": DocumentTypeInfo(
        key="invoice",
        label="Invoice Template",
        output_basename="Invoice",
        description="Publication-fee invoice accompanying the acceptance letter.",
    ),
}


def list_document_types() -> List[DocumentTypeInfo]:
    """Every registered document type, in presentation order."""
    return list(_REGISTRY.values())


def get_document_type(key: str) -> DocumentTypeInfo:
    """Look up one document type.

    Raises ``KeyError`` for an unknown key so callers can turn it into a 404
    rather than silently generating nothing.
    """
    return _REGISTRY[key]


def is_known(key: str) -> bool:
    return key in _REGISTRY


def register_document_type(info: DocumentTypeInfo) -> None:
    """Add a document type at runtime.

    The extension point for future document kinds: a plugin (or a later release)
    registers its type and the rest of the module -- template slot, upload
    route, batch generation, output layout, ZIP packaging, UI listing -- picks it
    up without modification.
    """
    _REGISTRY[info.key] = info
