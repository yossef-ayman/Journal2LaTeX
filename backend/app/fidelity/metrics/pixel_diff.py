"""Pixel Difference Metric plugin stub."""

from app.fidelity.schemas import NormalizedPage, MetricScore
from app.fidelity.metrics.base import SimilarityMetric


class PixelDifferenceMetric(SimilarityMetric):
    """Calculates Mean Squared Error (MSE) / Peak Signal-to-Noise Ratio (PSNR) pixel differences."""

    @property
    def name(self) -> str:
        return "pixel_diff"

    def compute(
        self,
        source_page: NormalizedPage,
        target_page: NormalizedPage,
    ) -> MetricScore:
        # Stub implementation for Phase 1 architecture definition
        return MetricScore(
            metric_name=self.name,
            score=1.0,
            details={"description": "Pixel difference metric stub"},
        )
