"""Main Facade Interface for the Visual Fidelity Engine."""

import logging
from typing import List, Optional
from app.fidelity.schemas import (
    FidelityConfig,
    FidelityReport,
    SourceType,
)
from app.fidelity.renderers import (
    DocumentRenderer,
    PDFRenderer,
    DocxRenderer,
    ImageRenderer,
)
from app.fidelity.image_converter import ImageConverter
from app.fidelity.page_matcher import PageMatcher
from app.fidelity.metrics import MetricRegistry, SimilarityMetric
from app.fidelity.visual_diff import VisualDiffEngine
from app.fidelity.report_generator import FidelityReportGenerator
from app.fidelity.exceptions import RenderingError

logger = logging.getLogger(__name__)


class FidelityEngine:
    """Independent main orchestrator for evaluating document visual fidelity."""

    def __init__(
        self,
        renderers: Optional[List[DocumentRenderer]] = None,
        converter: Optional[ImageConverter] = None,
        matcher: Optional[PageMatcher] = None,
        metric_registry: Optional[MetricRegistry] = None,
        diff_engine: Optional[VisualDiffEngine] = None,
        report_generator: Optional[FidelityReportGenerator] = None,
    ):
        """Initializes FidelityEngine with full dependency injection support.

        Args:
            renderers: Optional list of DocumentRenderer instances.
            converter: Optional ImageConverter instance for dimension normalization.
            matcher: Optional PageMatcher instance for page alignment.
            metric_registry: Optional MetricRegistry instance for metric plugins.
            diff_engine: Optional VisualDiffEngine instance for visual artifacts.
            report_generator: Optional FidelityReportGenerator instance for report aggregation.
        """
        self.renderers: List[DocumentRenderer] = renderers or [
            PDFRenderer(),
            DocxRenderer(),
            ImageRenderer(),
        ]
        self.converter: ImageConverter = converter or ImageConverter()
        self.matcher: PageMatcher = matcher or PageMatcher()
        self.registry: MetricRegistry = metric_registry or MetricRegistry(register_defaults=True)
        self.diff_engine: VisualDiffEngine = diff_engine or VisualDiffEngine()
        self.report_generator: FidelityReportGenerator = report_generator or FidelityReportGenerator()

    def register_metric(self, metric: SimilarityMetric) -> None:
        """Registers a custom similarity metric plugin.

        Args:
            metric: Implementation of SimilarityMetric interface.
        """
        self.registry.register(metric)

    def _get_renderer(self, source_type: SourceType) -> DocumentRenderer:
        """Finds registered renderer matching the target SourceType.

        Args:
            source_type: Document input format enum.

        Returns:
            Matching DocumentRenderer instance.

        Raises:
            RenderingError: If no renderer is registered for the specified format.
        """
        for r in self.renderers:
            if r.supported_source_type == source_type:
                return r
        logger.error(f"No document renderer registered for format: {source_type}")
        raise RenderingError(f"No document renderer registered for format: {source_type}")

    def evaluate(
        self,
        source_doc_path: str,
        source_type: SourceType,
        target_pdf_path: str,
        job_id: str,
        config: Optional[FidelityConfig] = None,
    ) -> FidelityReport:
        """Executes document fidelity evaluation workflow independently.

        Pipeline Flow:
            1. Render source document & target PDF into List[NormalizedPage]
            2. Match corresponding pages via PageMatcher
            3. Normalize canvas dimensions via ImageConverter
            4. Execute enabled metric plugins via MetricRegistry (ordering, timing, fault tolerance)
            5. Generate visual diff artifacts via VisualDiffEngine
            6. Compile structured report via FidelityReportGenerator

        Args:
            source_doc_path: Absolute path to reference source document.
            source_type: Source format (pdf, docx, or image).
            target_pdf_path: Absolute path to output compiled PDF.
            job_id: Unique conversion job identifier.
            config: Optional FidelityConfig settings.

        Returns:
            FidelityReport storing per-metric scores, visual issues, and diff artifacts.

        Raises:
            RenderingError: If page rendering fails.
            ConfigurationError: If invalid configuration is supplied.
        """
        cfg = config or FidelityConfig()
        output_dir = cfg.output_dir or f"temp/fidelity/{job_id}"

        logger.info(f"Starting fidelity evaluation for job '{job_id}' (Source format: {source_type.value})")

        # 1. Render source and target documents
        source_renderer = self._get_renderer(source_type)
        target_renderer = self._get_renderer(SourceType.PDF)

        src_pages = source_renderer.render(source_doc_path, f"{output_dir}/source", cfg.rendering.dpi)
        tgt_pages = target_renderer.render(target_pdf_path, f"{output_dir}/target", cfg.rendering.dpi)

        # 2. Pair corresponding pages
        page_matches = self.matcher.match_pages(src_pages, tgt_pages)

        logger.info(f"Fidelity engine paired {len(page_matches)} page(s) for job '{job_id}'")

        # Stub response for architecture definition
        return self.report_generator.generate_report(
            job_id=job_id,
            total_source_pages=len(src_pages),
            total_target_pages=len(tgt_pages),
            page_results=[],
            artifacts=[],
            config=cfg,
        )
