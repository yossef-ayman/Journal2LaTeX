"""Abstract base class for SimilarityMetric plugins."""

from abc import ABC, abstractmethod
from typing import Optional
from app.fidelity.schemas import NormalizedPage, PageRegion, MetricScore, FidelityConfig


class SimilarityMetric(ABC):
    """Abstract plugin interface for computing visual similarity metrics on full pages or regions."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique metric identifier name (e.g. 'ssim', 'pixel_diff', 'layout')."""
        pass

    @property
    def order(self) -> int:
        """Execution order priority sequence (lower numbers execute first). Defaults to 100."""
        return 100

    def is_enabled(self, config: FidelityConfig) -> bool:
        """Checks if this metric plugin is enabled in the provided FidelityConfig."""
        if config.enabled_metrics is not None:
            return self.name in config.enabled_metrics

        # Fallback to boolean flags
        flag_map = {
            "ssim": config.enable_ssim,
            "pixel_diff": config.enable_pixel_diff,
            "layout": config.enable_layout_diff,
            "ocr": config.enable_ocr_diff,
            "feature_matching": config.enable_feature_matching,
        }
        return flag_map.get(self.name, True)

    @abstractmethod
    def compute(
        self,
        source_page: NormalizedPage,
        target_page: NormalizedPage,
    ) -> MetricScore:
        """Calculates visual similarity metric between two normalized page images.

        Args:
            source_page: Normalized source page image.
            target_page: Normalized target page image.

        Returns:
            MetricScore object containing normalized score (0.0 to 1.0) and breakdown details.
        """
        pass

    def compute_region(
        self,
        source_page: NormalizedPage,
        source_region: PageRegion,
        target_page: NormalizedPage,
        target_region: PageRegion,
    ) -> MetricScore:
        """Calculates visual similarity metric for a specific region pair.

        Args:
            source_page: Source page container.
            source_region: Specific region on source page.
            target_page: Target page container.
            target_region: Specific region on target page.

        Returns:
            MetricScore localized to the specified region pair.
        """
        # Default fallback calls full compute or returns default score stub
        return MetricScore(
            metric_name=self.name,
            score=1.0,
            details={"region_id": source_region.id, "region_type": source_region.type},
        )
