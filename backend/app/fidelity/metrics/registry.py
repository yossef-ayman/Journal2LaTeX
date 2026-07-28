"""Plugin Registry and Pipeline Manager for Similarity Metrics."""

import time
import logging
from typing import List, Dict, Optional
from app.fidelity.schemas import NormalizedPage, PageRegion, MetricScore, FidelityConfig
from app.fidelity.metrics.base import SimilarityMetric
from app.fidelity.metrics.ssim import SSIMMetric
from app.fidelity.metrics.pixel_diff import PixelDifferenceMetric
from app.fidelity.metrics.layout import LayoutMetric
from app.fidelity.metrics.ocr import OCRMetric
from app.fidelity.metrics.feature import FeatureMatchingMetric

logger = logging.getLogger("fidelity.registry")


class MetricRegistry:
    """Manages loading, ordering, enabling, timing, and fault-tolerant execution of metric plugins."""

    def __init__(self, register_defaults: bool = True):
        self._metrics: Dict[str, SimilarityMetric] = {}
        if register_defaults:
            self.register(SSIMMetric())
            self.register(PixelDifferenceMetric())
            self.register(LayoutMetric())
            self.register(OCRMetric())
            self.register(FeatureMatchingMetric())

    def register(self, metric: SimilarityMetric) -> None:
        """Registers a metric plugin into the registry."""
        if not isinstance(metric, SimilarityMetric):
            raise TypeError(f"Expected SimilarityMetric instance, got {type(metric)}")
        self._metrics[metric.name] = metric
        logger.info(f"Registered fidelity metric plugin: '{metric.name}' (order: {metric.order})")

    def unregister(self, metric_name: str) -> None:
        """Removes a metric plugin from the registry by name."""
        if metric_name in self._metrics:
            del self._metrics[metric_name]

    def get_metric(self, metric_name: str) -> Optional[SimilarityMetric]:
        """Retrieves a registered metric plugin by name."""
        return self._metrics.get(metric_name)

    def get_active_metrics(self, config: FidelityConfig) -> List[SimilarityMetric]:
        """Returns sorted list of active metrics enabled by FidelityConfig."""
        active = [m for m in self._metrics.values() if m.is_enabled(config)]
        active.sort(key=lambda m: m.order)
        return active

    def execute_page_metrics(
        self,
        source_page: NormalizedPage,
        target_page: NormalizedPage,
        config: FidelityConfig,
    ) -> List[MetricScore]:
        """Executes all enabled metric plugins for a page pair with per-metric timing and graceful error handling."""
        active_metrics = self.get_active_metrics(config)
        scores: List[MetricScore] = []

        for metric in active_metrics:
            start_time = time.perf_counter()
            try:
                score_result = metric.compute(source_page, target_page)
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                score_result.execution_time_ms = round(elapsed_ms, 2)
                scores.append(score_result)
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                logger.warning(
                    f"Metric plugin '{metric.name}' failed on page {source_page.page_number}: {exc}",
                    exc_info=True,
                )
                scores.append(
                    MetricScore(
                        metric_name=metric.name,
                        score=0.0,
                        execution_time_ms=round(elapsed_ms, 2),
                        error_message=f"Metric execution error: {str(exc)}",
                        details={"failed": True},
                    )
                )

        return scores

    def execute_region_metrics(
        self,
        source_page: NormalizedPage,
        source_region: PageRegion,
        target_page: NormalizedPage,
        target_region: PageRegion,
        config: FidelityConfig,
    ) -> List[MetricScore]:
        """Executes enabled metrics for a specific region pair with fault tolerance."""
        active_metrics = self.get_active_metrics(config)
        scores: List[MetricScore] = []

        for metric in active_metrics:
            start_time = time.perf_counter()
            try:
                score_result = metric.compute_region(
                    source_page, source_region, target_page, target_region
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                score_result.execution_time_ms = round(elapsed_ms, 2)
                scores.append(score_result)
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                scores.append(
                    MetricScore(
                        metric_name=metric.name,
                        score=0.0,
                        execution_time_ms=round(elapsed_ms, 2),
                        error_message=f"Region metric execution error: {str(exc)}",
                        details={"region_id": source_region.id, "failed": True},
                    )
                )

        return scores
