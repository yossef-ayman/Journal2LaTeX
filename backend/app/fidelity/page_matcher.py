"""Page Alignment and Matching Strategy Interface."""

from typing import List
from app.fidelity.schemas import NormalizedPage, PageMatch


class PageMatcher:
    """Pairs corresponding pages between source document and target rendered PDF."""

    def match_pages(
        self,
        source_pages: List[NormalizedPage],
        target_pages: List[NormalizedPage],
    ) -> List[PageMatch]:
        """Maps source document pages to target document pages.

        Args:
            source_pages: List of normalized pages from source document.
            target_pages: List of normalized pages from target rendered document.

        Returns:
            List of paired PageMatch objects.
        """
        # Stub implementation for Phase 1 architecture definition
        matches: List[PageMatch] = []
        for i, src in enumerate(source_pages):
            if i < len(target_pages):
                matches.append(
                    PageMatch(
                        source_page=src,
                        target_page=target_pages[i],
                        confidence_score=1.0,
                    )
                )
        return matches
