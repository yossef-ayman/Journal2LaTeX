"""Feature Matching Metric (ORB/SIFT) plugin stub."""

from app.fidelity.schemas import NormalizedPage, MetricScore
from app.fidelity.metrics.base import SimilarityMetric


class FeatureMatchingMetric(SimilarityMetric):
    """Calculates keypoint feature alignment score (ORB / SIFT / FLANN matcher)."""

    @property
    def name(self) -> str:
        return "feature_matching"

    def compute(
        self,
        source_page: NormalizedPage,
        target_page: NormalizedPage,
    ) -> MetricScore:
        # Stub implementation for Phase 1 architecture definition
        return MetricScore(
            metric_name=self.name,
            score=1.0,
            details={"description": "Feature matching metric stub"},
        )
