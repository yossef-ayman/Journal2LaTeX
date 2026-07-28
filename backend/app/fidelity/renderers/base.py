"""Abstract base class for document renderers."""

from abc import ABC, abstractmethod
from typing import List
from app.fidelity.schemas import NormalizedPage, SourceType


class DocumentRenderer(ABC):
    """Abstract interface for converting arbitrary document formats into NormalizedPages."""

    @property
    @abstractmethod
    def supported_source_type(self) -> SourceType:
        """Returns the document source format supported by this renderer implementation."""
        pass

    @abstractmethod
    def render(self, document_path: str, output_dir: str, dpi: int = 150) -> List[NormalizedPage]:
        """Renders input document pages into standardized NormalizedPage objects.

        Args:
            document_path: Absolute path to the source document.
            output_dir: Directory where rendered page images should be saved.
            dpi: Output resolution rendering DPI.

        Returns:
            List of NormalizedPage objects.
        """
        pass
