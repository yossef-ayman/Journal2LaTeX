"""Structural Similarity Index (SSIM) Metric plugin stub."""

from app.fidelity.schemas import NormalizedPage, MetricScore
from app.fidelity.metrics.base import SimilarityMetric


class SSIMMetric(SimilarityMetric):
    """Calculates Structural Similarity Index (SSIM) between page image pairs."""

    @property
    def name(self) -> str:
        return "ssim"

    def compute(
        self,
        source_page: NormalizedPage,
        target_page: NormalizedPage,
    ) -> MetricScore:
        # Stub implementation for Phase 1 architecture definition
        return MetricScore(
            metric_name=self.name,
            score=1.0,
            details={"description": "SSIM metric stub"},
        )
