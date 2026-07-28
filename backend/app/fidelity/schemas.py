"""Data schemas and Pydantic models for the Visual Fidelity Engine."""

import re
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator
from app.fidelity.exceptions import ConfigurationError


class SourceType(str, Enum):
    """Supported document source types for visual fidelity evaluation."""
    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"


class AlignmentMode(str, Enum):
    """Canvas alignment modes for page image dimension normalization."""
    CENTER = "center"
    TOP = "top"
    TOP_LEFT = "top_left"
    FIT = "fit"
    FILL = "fill"


class RenderingConfig(BaseModel):
    """Configuration options for page rendering, DPI normalization, and canvas alignment."""
    dpi: int = Field(default=150, description="Page rasterization DPI resolution")
    alignment_mode: AlignmentMode = Field(default=AlignmentMode.CENTER, description="Canvas padding alignment mode")
    background_color: str = Field(default="#FFFFFF", description="Hex background color for padded canvas")
    auto_rotation: bool = Field(default=False, description="Automatically rotate pages based on orientation metadata")
    auto_orientation_detection: bool = Field(default=False, description="Detect and fix inverted or sideways page aspect ratios")
    preserve_aspect_ratio: bool = Field(default=True, description="Preserve page aspect ratio when scaling or padding")

    @model_validator(mode="after")
    def validate_rendering_config(self) -> "RenderingConfig":
        if self.dpi <= 0:
            raise ConfigurationError(f"Rendering DPI must be greater than 0, got {self.dpi}")
        if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", self.background_color):
            raise ConfigurationError(f"Invalid hex background color format: '{self.background_color}'")
        return self


class IssueSeverity(str, Enum):
    """Severity levels for detected semantic visual issues."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class IssueCategory(str, Enum):
    """Categories of visual components where discrepancies occur."""
    FIGURE = "figure"
    TABLE = "table"
    CAPTION = "caption"
    PARAGRAPH = "paragraph"
    FONT = "font"
    HEADER_FOOTER = "header_footer"
    MARGIN = "margin"
    LAYOUT = "layout"


class BoundingBox(BaseModel):
    """Spatial bounding box coordinates for a region."""
    x: float = Field(description="X coordinate of top-left corner")
    y: float = Field(description="Y coordinate of top-left corner")
    width: float = Field(description="Width of the bounding box")
    height: float = Field(description="Height of the bounding box")


class RegionType(str, Enum):
    """Supported semantic document element region types."""
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    FIGURE = "figure"
    TABLE = "table"
    CAPTION = "caption"
    EQUATION = "equation"
    HEADER = "header"
    FOOTER = "footer"
    BIOGRAPHY = "biography"


class PageRegion(BaseModel):
    """Represents a specific semantic region on a document page."""
    id: str = Field(description="Unique region identifier (e.g. 'fig_1', 'para_3')")
    type: RegionType = Field(description="Type of document element in this region")
    bbox: BoundingBox = Field(description="Spatial bounding box of the region")
    confidence: float = Field(default=1.0, description="Detection confidence score (0.0 to 1.0)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom region metadata (e.g. caption text)")


class VisualIssue(BaseModel):
    """Represents a human-readable semantic visual discrepancy identified on a page or region."""
    issue_type: str = Field(description="Short issue code (e.g. 'figure_shifted', 'table_width_changed')")
    category: IssueCategory = Field(description="Semantic component category")
    severity: IssueSeverity = Field(default=IssueSeverity.WARNING, description="Impact level")
    description: str = Field(description="Human-readable issue summary (e.g. 'Figure moved downward')")
    region_id: Optional[str] = Field(default=None, description="ID of specific PageRegion affected")
    bounding_box: Optional[BoundingBox] = Field(default=None, description="Bounding box of affected region")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional breakdown context")


class NormalizedPage(BaseModel):
    """Represents a single standardized page image with optional detected regions."""
    page_number: int = Field(description="1-based index of the page within the document")
    image_path: str = Field(description="Absolute path to the rendered page image")
    width: int = Field(description="Page image width in pixels")
    height: int = Field(description="Page image height in pixels")
    dpi: int = Field(default=150, description="DPI resolution of the rendered image")
    source_type: SourceType = Field(description="Original document format source")
    regions: List[PageRegion] = Field(default_factory=list, description="Detected semantic document regions")


class PageMatch(BaseModel):
    """Pairs corresponding source and target normalized pages."""
    source_page: NormalizedPage = Field(description="Source reference page")
    target_page: NormalizedPage = Field(description="Target rendered page")
    confidence_score: float = Field(default=1.0, description="Alignment confidence (0.0 to 1.0)")


class MetricScore(BaseModel):
    """Result of a single visual similarity metric plugin."""
    metric_name: str = Field(description="Identifier of the metric implementation")
    score: float = Field(description="Normalized similarity score from 0.0 (different) to 1.0 (identical)")
    execution_time_ms: Optional[float] = Field(default=None, description="Execution time in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if metric execution failed gracefully")
    details: Dict[str, Any] = Field(default_factory=dict, description="Raw breakdown data from metric calculation")


class RegionMetricResult(BaseModel):
    """Similarity metric evaluation for a specific region pair."""
    region_id: str = Field(description="Identifier of the region")
    region_type: RegionType = Field(description="Type of the region element")
    bbox: BoundingBox = Field(description="Bounding box coordinates of the region")
    metric_scores: List[MetricScore] = Field(default_factory=list, description="Per-metric scores for this region")
    visual_issues: List[VisualIssue] = Field(default_factory=list, description="Semantic issues localized to this region")


class PageMetricResult(BaseModel):
    """Per-page similarity metrics, region breakdowns, and semantic visual issues."""
    source_page_num: int
    target_page_num: int
    metric_scores: List[MetricScore] = Field(default_factory=list, description="Independent page-level metric plugin scores")
    region_results: List[RegionMetricResult] = Field(default_factory=list, description="Region-level similarity breakdown")
    visual_issues: List[VisualIssue] = Field(default_factory=list, description="Human-readable visual discrepancies")


class DiffArtifact(BaseModel):
    """Visual difference artifacts generated for a page pair."""
    page_number: int
    diff_image_path: str = Field(description="Path to side-by-side or difference map image")
    heatmap_path: Optional[str] = Field(default=None, description="Path to difference heatmap image")
    bounding_boxes: List[BoundingBox] = Field(
        default_factory=list, description="Detected visual change bounding boxes"
    )


class FidelityConfig(BaseModel):
    """Configuration options for fidelity evaluation run."""
    rendering: RenderingConfig = Field(default_factory=RenderingConfig, description="Rendering & alignment options")
    dpi: int = Field(default=150, description="Rendering resolution DPI")
    enable_region_comparison: bool = Field(default=True, description="Enable region-level element comparison")
    
    # Core lightweight metric plugins (enabled by default)
    enable_ssim: bool = Field(default=True)
    enable_pixel_diff: bool = Field(default=True)
    enable_layout_diff: bool = Field(default=True)

    # Optional / Heavy metric plugins (disabled by default, executed on-demand)
    enable_ocr_diff: bool = Field(default=False, description="Enable OCR text plugin explicitly")
    auto_trigger_ocr_ssim_threshold: float = Field(
        default=0.85, description="Trigger OCR dynamically if SSIM score drops below threshold"
    )
    auto_trigger_ocr_layout_threshold: float = Field(
        default=0.80, description="Trigger OCR dynamically if layout score drops below threshold"
    )

    enable_feature_matching: bool = Field(default=False)
    enabled_metrics: Optional[List[str]] = Field(
        default=None, description="Explicit whitelist of enabled metric plugin names"
    )
    output_dir: Optional[str] = Field(default=None, description="Directory to save diff artifacts and reports")

    @model_validator(mode="after")
    def validate_fidelity_config(self) -> "FidelityConfig":
        if self.dpi <= 0:
            raise ConfigurationError(f"Fidelity DPI must be greater than 0, got {self.dpi}")
        if not (0.0 <= self.auto_trigger_ocr_ssim_threshold <= 1.0):
            raise ConfigurationError(
                f"OCR SSIM trigger threshold must be between 0.0 and 1.0, got {self.auto_trigger_ocr_ssim_threshold}"
            )
        if not (0.0 <= self.auto_trigger_ocr_layout_threshold <= 1.0):
            raise ConfigurationError(
                f"OCR layout trigger threshold must be between 0.0 and 1.0, got {self.auto_trigger_ocr_layout_threshold}"
            )
        return self


class FidelityReport(BaseModel):
    """Structured report summarizing document fidelity, region breakdowns, and semantic visual issues."""
    job_id: str
    total_source_pages: int
    total_target_pages: int
    page_results: List[PageMetricResult] = Field(default_factory=list)
    metric_averages: Dict[str, float] = Field(default_factory=dict, description="Average score per metric plugin")
    all_visual_issues: List[VisualIssue] = Field(default_factory=list, description="Aggregated semantic visual issues")
    artifacts: List[DiffArtifact] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
