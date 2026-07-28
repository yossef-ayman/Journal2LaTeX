"""Similarity Metrics plugin package initialization."""

from app.fidelity.metrics.base import SimilarityMetric
from app.fidelity.metrics.ssim import SSIMMetric
from app.fidelity.metrics.pixel_diff import PixelDifferenceMetric
from app.fidelity.metrics.layout import LayoutMetric
from app.fidelity.metrics.ocr import OCRMetric
from app.fidelity.metrics.feature import FeatureMatchingMetric
from app.fidelity.metrics.registry import MetricRegistry

__all__ = [
    "SimilarityMetric",
    "MetricRegistry",
    "SSIMMetric",
    "PixelDifferenceMetric",
    "LayoutMetric",
    "OCRMetric",
    "FeatureMatchingMetric",
]
