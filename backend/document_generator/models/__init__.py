"""Pydantic models for the Document Generator module."""

from document_generator.models.schemas import (  # noqa: F401
    BatchGenerationRequest,
    BatchSummary,
    DocumentSegment,
    DocumentTypeInfo,
    FieldMapping,
    FieldSuggestion,
    GeneratedArtifact,
    GeneratedDocumentSet,
    GeneratorSettings,
    GeneratorSettingsUpdate,
    PaperMetadata,
    TemplateFieldInfo,
    TemplateInfo,
    TemplateInspection,
    TemplateMapping,
    TemplateMappingUpdate,
)

__all__ = [
    "BatchGenerationRequest",
    "BatchSummary",
    "DocumentSegment",
    "DocumentTypeInfo",
    "FieldMapping",
    "FieldSuggestion",
    "GeneratedArtifact",
    "GeneratedDocumentSet",
    "GeneratorSettings",
    "GeneratorSettingsUpdate",
    "PaperMetadata",
    "TemplateFieldInfo",
    "TemplateInfo",
    "TemplateInspection",
    "TemplateMapping",
    "TemplateMappingUpdate",
]
