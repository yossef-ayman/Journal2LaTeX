"""Visual Fidelity Engine package initialization."""

from app.fidelity.schemas import (
    SourceType,
    AlignmentMode,
    RenderingConfig,
    IssueSeverity,
    IssueCategory,
    VisualIssue,
    BoundingBox,
    RegionType,
    PageRegion,
    NormalizedPage,
    PageMatch,
    MetricScore,
    RegionMetricResult,
    PageMetricResult,
    DiffArtifact,
    FidelityConfig,
    FidelityReport,
)
from app.fidelity.engine import FidelityEngine

__all__ = [
    "FidelityEngine",
    "SourceType",
    "AlignmentMode",
    "RenderingConfig",
    "IssueSeverity",
    "IssueCategory",
    "VisualIssue",
    "BoundingBox",
    "RegionType",
    "PageRegion",
    "NormalizedPage",
    "PageMatch",
    "MetricScore",
    "RegionMetricResult",
    "PageMetricResult",
    "DiffArtifact",
    "FidelityConfig",
    "FidelityReport",
]
