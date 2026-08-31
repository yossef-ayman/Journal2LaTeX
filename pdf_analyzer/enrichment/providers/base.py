from abc import ABC, abstractmethod
from typing import List, Dict, Any
from enrichment.parser import ParsedReference

class AcademicProvider(ABC):
    """
    Abstract Base Class for Academic Metadata Providers (OpenAlex, Crossref, etc.).
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """Return provider identifier name (e.g. 'openalex', 'crossref')."""
        pass

    @abstractmethod
    async def search_reference(self, reference: ParsedReference) -> List[Dict[str, Any]]:
        """
        Search provider for candidates matching the parsed reference.
        Returns a list of standardized candidate dictionaries.
        """
        pass
