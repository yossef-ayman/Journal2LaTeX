"""Turning a parsed Word package into an understood document.

The extractors read Layer 0 and build Layer 1.  They never write, and they never
touch the legacy Word -> LaTeX pipeline: this whole subpackage is additive, and
deleting it would leave the existing workflow byte-for-byte unchanged.
"""

from document_engine.extract.extractor import SemanticExtractor
from document_engine.extract.metadata import MetadataExtractor
from document_engine.extract.objects import (
    extract_equations,
    extract_figures,
    extract_tables,
    parse_caption,
)
from document_engine.extract.references import (
    extract_references,
    looks_like_a_bibliography,
)
from document_engine.extract.sections import SectionBuilder
from document_engine.extract.signals import DocumentSignals, Verdict

__all__ = [
    "DocumentSignals",
    "MetadataExtractor",
    "SectionBuilder",
    "SemanticExtractor",
    "Verdict",
    "extract_equations",
    "extract_figures",
    "extract_references",
    "extract_tables",
    "looks_like_a_bibliography",
    "parse_caption",
]
