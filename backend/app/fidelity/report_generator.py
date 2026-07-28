"""Structured Fidelity Report Generator Interface."""

from typing import List, Dict
from app.fidelity.schemas import (
    PageMetricResult,
    DiffArtifact,
    VisualIssue,
    FidelityReport,
    FidelityConfig,
)


class FidelityReportGenerator:
    """Compiles page metrics and semantic visual issues into a structured document FidelityReport."""

    def generate_report(
        self,
        job_id: str,
        total_source_pages: int,
        total_target_pages: int,
        page_results: List[PageMetricResult],
        artifacts: List[DiffArtifact],
        config: FidelityConfig,
    ) -> FidelityReport:
        """Aggregates independent metric scores and semantic visual issues into FidelityReport.

        Args:
            job_id: Identifier of the conversion job.
            total_source_pages: Count of pages in source document.
            total_target_pages: Count of pages in target document.
            page_results: Per-page metric scores and visual issues.
            artifacts: Generated visual difference artifacts.
            config: Configuration settings used for the evaluation run.

        Returns:
            FidelityReport object storing per-metric averages and visual issues.
        """
        # Calculate metric averages
        metric_sums: Dict[str, float] = {}
        metric_counts: Dict[str, int] = {}
        all_visual_issues: List[VisualIssue] = []

        for page in page_results:
            for m in page.metric_scores:
                metric_sums[m.metric_name] = metric_sums.get(m.metric_name, 0.0) + m.score
                metric_counts[m.metric_name] = metric_counts.get(m.metric_name, 0) + 1
            all_visual_issues.extend(page.visual_issues)

        metric_averages = {
            name: round(metric_sums[name] / count, 4)
            for name, count in metric_counts.items()
            if count > 0
        }

        return FidelityReport(
            job_id=job_id,
            total_source_pages=total_source_pages,
            total_target_pages=total_target_pages,
            page_results=page_results,
            metric_averages=metric_averages,
            all_visual_issues=all_visual_issues,
            artifacts=artifacts,
            warnings=[],
            metadata={},
        )
