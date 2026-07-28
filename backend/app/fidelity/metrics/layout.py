"""Layout Difference Metric plugin stub."""

from app.fidelity.schemas import NormalizedPage, MetricScore
from app.fidelity.metrics.base import SimilarityMetric


class LayoutMetric(SimilarityMetric):
    """Calculates spatial bounding box overlap and layout structure similarity."""

    @property
    def name(self) -> str:
        return "layout"

    def compute(
        self,
        source_page: NormalizedPage,
        target_page: NormalizedPage,
    ) -> MetricScore:
        # Stub implementation for Phase 1 architecture definition
        return MetricScore(
            metric_name=self.name,
            score=1.0,
            details={"description": "Layout metric stub"},
        )
