"""OCR Text Region Similarity Metric plugin stub (Optional / On-Demand)."""

from app.fidelity.schemas import NormalizedPage, MetricScore
from app.fidelity.metrics.base import SimilarityMetric


class OCRMetric(SimilarityMetric):
    """Optional / heavy metric plugin calculating text region alignment & OCR similarity.
    
    This plugin is executed on-demand (e.g. when SSIM or layout score is low, or explicitly enabled in config).
    """

    @property
    def name(self) -> str:
        return "ocr"

    def compute(
        self,
        source_page: NormalizedPage,
        target_page: NormalizedPage,
    ) -> MetricScore:
        # Stub implementation for Phase 1 architecture definition
        return MetricScore(
            metric_name=self.name,
            score=1.0,
            details={"description": "OCR text similarity metric stub"},
        )
