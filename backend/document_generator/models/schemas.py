"""Request/response models for the Document Generator API.

These are the module's own contracts.  They intentionally do not import the
converter's ``DocumentModel``: the generator only needs a title and an author
list, and coupling the API surface to the converter's much larger model would
make the two impossible to evolve separately.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentTypeInfo(BaseModel):
    """A kind of document the module can produce (acceptance letter, invoice...)."""

    key: str = Field(..., description="Stable identifier used in paths and APIs.")
    label: str = Field(..., description="Human-readable name shown in the UI.")
    output_basename: str = Field(
        ..., description="File name (without extension) inside each paper folder."
    )
    description: str = ""


class TemplateInfo(BaseModel):
    """State of one master template slot."""

    key: str
    label: str
    uploaded: bool = False
    original_filename: Optional[str] = None
    uploaded_at: Optional[str] = None
    size_bytes: Optional[int] = None
    # Placeholders discovered in the stored template, so the UI can show which
    # values a template actually consumes instead of a fixed list.
    placeholders: List[str] = []
    # How many superseded versions are retained for this slot.
    archived_versions: int = 0
    # Mapping state: an ordinary Word document becomes a template once its
    # dynamic fields have been mapped, so the UI can prompt for the wizard.
    mapped: bool = False
    mapped_fields: List[str] = []
    # Fields whose saved literal no longer occurs, e.g. after a replacement.
    stale_fields: List[str] = []
    # True when the document carries neither a mapping nor any placeholder, i.e.
    # generation would copy it out unchanged.
    needs_mapping: bool = False


class TemplateFieldInfo(BaseModel):
    """A dynamic field an operator can point at while mapping a template."""

    key: str = Field(..., description="Value name, e.g. TITLE. Matches the context key.")
    label: str = Field(..., description="Human-readable name shown in the wizard.")
    description: str = ""
    required: bool = False


class DocumentSegment(BaseModel):
    """One selectable piece of text from an uploaded document.

    A segment is a paragraph as Word renders it, reassembled from its runs. The
    wizard shows these and the operator selects, inside one, the exact text that
    is the title, the reference number and so on -- a paragraph often carries
    several fields at once.
    """

    id: str = Field(..., description="Stable within one inspection response.")
    part: str = Field(..., description="Package part, e.g. word/document.xml.")
    location: str = Field(
        default="body", description='Where it appears: "body", "header" or "footer".'
    )
    index: int = Field(..., description="Paragraph order within its part.")
    text: str
    in_table: bool = False
    occurrences: int = Field(
        default=1,
        description="How many paragraphs across the document carry identical text.",
    )


class FieldMapping(BaseModel):
    """One confirmed field -> literal-text mapping."""

    field: str = Field(..., description="Field key, e.g. TITLE.")
    text: str = Field(..., description="The literal text in the document to replace.")
    occurrences: int = Field(
        default=0, description="How many times that literal occurs; informational."
    )


class TemplateMapping(BaseModel):
    """The saved mapping that turns a stored document into a reusable template."""

    document_type: str
    mappings: List[FieldMapping] = []
    updated_at: Optional[str] = None
    # Set when a template was replaced and a saved literal no longer appears in
    # the new file, so the UI can ask the operator to re-map just those fields.
    stale_fields: List[str] = []


class FieldSuggestion(BaseModel):
    """A guess at what a piece of text represents, offered to speed up mapping."""

    field: str
    text: str
    segment_id: str
    occurrences: int = 1
    reason: str = ""


class TemplateInspection(BaseModel):
    """Everything the mapping wizard needs for one stored template."""

    document_type: str
    label: str
    fields: List[TemplateFieldInfo] = []
    segments: List[DocumentSegment] = []
    suggestions: List[FieldSuggestion] = []
    mapping: Optional[TemplateMapping] = None


class TemplateMappingUpdate(BaseModel):
    """The wizard's confirmation: the mappings to store permanently."""

    mappings: List[FieldMapping] = []


class PaperMetadata(BaseModel):
    """What the module extracted from one uploaded paper."""

    index: int = Field(..., description="1-based position within the batch.")
    source_filename: str
    title: str = ""
    authors: List[str] = []
    reference_number: str = ""
    # Non-fatal notes, e.g. "title not detected -- file name used".
    warnings: List[str] = []


class GeneratedArtifact(BaseModel):
    """One produced file."""

    document_type: str
    format: str = Field(..., description='"docx" or "pdf".')
    filename: str
    relative_path: str = Field(
        ..., description="Path within the batch output tree, e.g. 'Paper 1/Acceptance.pdf'."
    )
    size_bytes: int = 0
    download_url: str


class DocumentValidation(BaseModel):
    """The result of checking one generated document against its template.

    Reported per document rather than per batch: an operator asked to trust
    twenty letters needs to know *which* one drifted, and a document that fails
    here is never converted to PDF, because Word refuses to export a package
    whose XML is inconsistent.
    """

    document_type: str
    document: str = Field(..., description="File name of the generated document.")
    valid: bool = True
    checks: Dict[str, bool] = Field(
        default_factory=dict,
        description="Check name -> passed, in the order the checks were run.",
    )
    errors: List[str] = []
    fields_replaced: List[str] = []
    fields_missing: List[str] = []


class GeneratedDocumentSet(BaseModel):
    """Everything produced for a single paper."""

    paper: PaperMetadata
    folder: str = Field(..., description="Output folder name for this paper.")
    artifacts: List[GeneratedArtifact] = []
    errors: List[str] = []
    validations: List[DocumentValidation] = []


class BatchGenerationRequest(BaseModel):
    """Values the operator supplies once for a whole batch.

    Dates are accepted as free text and used verbatim.  The module deliberately
    does not parse or reformat them: an acceptance letter must read exactly as
    the operator typed it ("22 July 2026"), and normalising through a date type
    would impose a format the template's language may not want.
    """

    acceptance_date: str = ""
    deadline: str = ""
    reference_prefix: Optional[str] = Field(
        default=None,
        description="Optional literal prefix placed before the generated reference number.",
    )
    reference_suffix: Optional[str] = Field(
        default=None,
        description=(
            "Overrides the configured suffix in "
            "<JournalCode><MMDDYY><BatchOrder><Suffix> for this batch only."
        ),
    )
    journal_code: Optional[str] = Field(
        default=None,
        description="Overrides the configured journal code for this batch only.",
    )
    editor: Optional[str] = None
    journal: Optional[str] = None
    document_types: Optional[List[str]] = Field(
        default=None,
        description="Which document types to produce; defaults to every type with a template.",
    )
    generate_pdf: Optional[bool] = None
    extra_placeholders: Dict[str, str] = Field(
        default_factory=dict,
        description="Ad-hoc placeholder values applied to every document in the batch.",
    )


class BatchSummary(BaseModel):
    """Result of a generation run."""

    batch_id: str
    created_at: str
    paper_count: int
    document_count: int
    documents: List[GeneratedDocumentSet] = []
    zip_available: bool = False
    zip_download_url: Optional[str] = None
    pdf_backend: Optional[str] = None
    warnings: List[str] = []
    # How many generated documents failed validation against their template.
    # Zero is the only acceptable value for a batch an operator will send out.
    validation_failures: int = 0


class GeneratorSettings(BaseModel):
    """Persisted module settings."""

    journal_code: str = ""
    reference_suffix: str = "A"
    editor_name: str = ""
    journal_name: str = ""
    custom_placeholders: Dict[str, str] = {}
    generate_pdf: bool = True
    # Reported, not stored: whether a PDF converter is actually available here.
    pdf_backend_available: bool = False
    pdf_backend: Optional[str] = None


class GeneratorSettingsUpdate(BaseModel):
    """Partial update of the persisted settings."""

    journal_code: Optional[str] = None
    reference_suffix: Optional[str] = None
    editor_name: Optional[str] = None
    journal_name: Optional[str] = None
    custom_placeholders: Optional[Dict[str, Any]] = None
    generate_pdf: Optional[bool] = None
