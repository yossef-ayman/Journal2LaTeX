"""Layer 2: proposing edits, deciding on them, and writing them back.

Layer 0 knows where things are in the bytes, Layer 1 knows what they mean, and
this layer changes them -- but only the ones a person said yes to, and only the
byte ranges those edits actually touch.

Nothing in here is imported by the Word -> LaTeX converter or by the Document
Generator.  Deleting this subpackage would leave both of them byte-for-byte
unchanged, which is the same guarantee Phases 1 and 2 carry and the reason the
engine can be developed against a production system without endangering it.
"""

from document_engine.edit.diff import Hunk, changed_span, diff_words, summarize
from document_engine.edit.preview import PartImpact, Preview, PreviewEngine
from document_engine.edit.suggestions import (
    ACCEPTED,
    PENDING,
    REJECTED,
    Suggestion,
    SuggestionError,
    SuggestionSet,
)
from document_engine.edit.writer import (
    AppliedEdit,
    RefusedEdit,
    WordWriter,
    WriteError,
    WriteResult,
)

__all__ = [
    "ACCEPTED",
    "AppliedEdit",
    "Hunk",
    "PENDING",
    "PartImpact",
    "Preview",
    "PreviewEngine",
    "REJECTED",
    "RefusedEdit",
    "Suggestion",
    "SuggestionError",
    "SuggestionSet",
    "WordWriter",
    "WriteError",
    "WriteResult",
    "changed_span",
    "diff_words",
    "summarize",
]
