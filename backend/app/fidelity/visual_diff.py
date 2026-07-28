"""Difference Map, Heatmap, and Bounding Box Annotation Generator Interface."""

from typing import List, Dict, Any
from app.fidelity.schemas import NormalizedPage, DiffArtifact


class VisualDiffEngine:
    """Generates visual difference artifacts (heatmaps, contour overlays, side-by-side diffs)."""

    def generate_diff(
        self,
        source_page: NormalizedPage,
        target_page: NormalizedPage,
        output_dir: str,
    ) -> DiffArtifact:
        """Generates difference maps and bounding boxes for a page pair.

        Args:
            source_page: Reference source normalized page.
            target_page: Target rendered normalized page.
            output_dir: Directory where output diff images will be exported.

        Returns:
            DiffArtifact containing paths to diff image, heatmap, and bounding boxes.
        """
        # Stub implementation for Phase 1 architecture definition
        return DiffArtifact(
            page_number=source_page.page_number,
            diff_image_path="",
            heatmap_path=None,
            bounding_boxes=[],
        )
