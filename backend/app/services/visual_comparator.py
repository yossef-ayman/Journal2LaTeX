"""Visual comparison of the original Word document against the rendered PDF.

The reference PDF is produced from the DOCX with the best available backend:
Microsoft Word COM automation on Windows (with correct COM apartment
initialization for worker threads), LibreOffice headless everywhere else.
When neither backend is available the comparison degrades gracefully: the
reports are still written, flagged with ``reference_available = false``.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.config import settings
from app.utils import pdf_tools
from app.utils.imaging import rms_similarity
from app.utils.logger import get_job_logger


class ReferenceConversionError(Exception):
    """Raised when the DOCX cannot be converted to a reference PDF."""


class VisualComparator:
    """Render both PDFs to images and compute page-by-page similarity."""

    def compare_documents(
        self, docx_path: Path, rendered_pdf_path: Path, output_dir: Path, job_id: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        logger = get_job_logger(job_id, "visual")
        output_dir.mkdir(parents=True, exist_ok=True)

        visual_report: Dict[str, Any] = {
            "reference_available": False,
            "reference_backend": None,
            "similarity_score_per_page": {},
            "average_similarity": 0.0,
            "largest_differences": [],
        }
        layout_report: Dict[str, Any] = {
            "page_count": {"original": 0, "rendered": 0},
            "layout_differences": [],
        }

        try:
            orig_pdf_path = output_dir / "original_docx.pdf"
            backend = self._ensure_reference_pdf(docx_path, orig_pdf_path, logger)
            visual_report["reference_available"] = True
            visual_report["reference_backend"] = backend
        except ReferenceConversionError as exc:
            logger.warning("Reference PDF unavailable: %s", exc)
            visual_report["largest_differences"].append(
                f"Reference conversion unavailable: {exc}"
            )
            layout_report["layout_differences"].append(str(exc))
            self._write_reports(output_dir, visual_report, layout_report)
            return visual_report, layout_report

        dpi = settings.COMPARISON_DPI
        try:
            orig_images = pdf_tools.render_pdf_to_images(orig_pdf_path, output_dir / "orig_pages", dpi)
            rend_images = pdf_tools.render_pdf_to_images(rendered_pdf_path, output_dir / "rend_pages", dpi)
        except pdf_tools.PdfToolsError as exc:
            logger.error("PDF rasterization failed: %s", exc)
            layout_report["layout_differences"].append(f"Rasterization failed: {exc}")
            self._write_reports(output_dir, visual_report, layout_report)
            return visual_report, layout_report

        total_sim = 0.0
        max_pages = max(len(orig_images), len(rend_images))
        page_diffs: List[Tuple[float, int]] = []
        for idx in range(max_pages):
            page_num = idx + 1
            if idx < len(orig_images) and idx < len(rend_images):
                sim = self._compute_image_similarity(orig_images[idx], rend_images[idx])
                visual_report["similarity_score_per_page"][f"page_{page_num}"] = f"{sim * 100:.2f}%"
                total_sim += sim
                page_diffs.append((sim, page_num))
            else:
                visual_report["similarity_score_per_page"][f"page_{page_num}"] = "0.00% (Missing Page)"
                visual_report["largest_differences"].append(
                    f"Page {page_num} exists in only one of the documents."
                )
        if max_pages > 0:
            visual_report["average_similarity"] = total_sim / max_pages
        for sim, page_num in sorted(page_diffs)[:3]:
            if sim < 0.98:
                visual_report["largest_differences"].append(
                    f"Page {page_num} similarity {sim * 100:.2f}%"
                )

        layout_report["page_count"]["original"] = pdf_tools.pdf_page_count(orig_pdf_path)
        layout_report["page_count"]["rendered"] = pdf_tools.pdf_page_count(rendered_pdf_path)
        if layout_report["page_count"]["original"] != layout_report["page_count"]["rendered"]:
            layout_report["layout_differences"].append("Page count mismatch detected.")

        self._write_reports(output_dir, visual_report, layout_report)
        return visual_report, layout_report

    # ------------------------------------------------------------------ #
    # Reference PDF conversion backends
    # ------------------------------------------------------------------ #

    def _ensure_reference_pdf(self, docx_path: Path, pdf_path: Path, logger) -> str:
        """Convert DOCX to PDF once per job; reuse a fresh cached conversion."""
        if (
            pdf_path.exists()
            and pdf_path.stat().st_size > 0
            and pdf_path.stat().st_mtime >= docx_path.stat().st_mtime
        ):
            return "cached"

        if sys.platform == "win32":
            try:
                self._convert_with_word_com(docx_path, pdf_path)
                return "ms-word-com"
            except Exception as exc:
                logger.warning("MS Word COM conversion failed (%s); trying LibreOffice.", exc)

        soffice = shutil.which(settings.SOFFICE_PATH) or shutil.which("libreoffice")
        if soffice:
            self._convert_with_soffice(soffice, docx_path, pdf_path)
            return "libreoffice"

        raise ReferenceConversionError(
            "No DOCX-to-PDF backend available (need MS Word on Windows or LibreOffice)."
        )

    @staticmethod
    def _convert_with_word_com(docx_path: Path, pdf_path: Path) -> None:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore

        pythoncom.CoInitialize()
        word = None
        doc = None
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0
            doc = word.Documents.Open(str(docx_path.resolve()), ReadOnly=True)
            doc.SaveAs(str(pdf_path.resolve()), FileFormat=17)  # wdFormatPDF
        finally:
            if doc is not None:
                try:
                    doc.Close(False)
                except Exception:
                    pass
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
        if not pdf_path.exists():
            raise ReferenceConversionError("Word COM did not produce a PDF.")

    @staticmethod
    def _convert_with_soffice(soffice: str, docx_path: Path, pdf_path: Path) -> None:
        out_dir = pdf_path.parent
        result = subprocess.run(
            [soffice, "--headless", "--norestore", "--convert-to", "pdf",
             "--outdir", str(out_dir), str(docx_path)],
            capture_output=True, text=True, check=False,
            timeout=settings.COMPILE_TIMEOUT,
        )
        produced = out_dir / (docx_path.stem + ".pdf")
        if result.returncode != 0 or not produced.exists():
            raise ReferenceConversionError(
                f"LibreOffice conversion failed (rc={result.returncode}): {result.stderr.strip()[:400]}"
            )
        if produced != pdf_path:
            produced.replace(pdf_path)

    # ------------------------------------------------------------------ #

    @staticmethod
    def _compute_image_similarity(img_path1: Path, img_path2: Path) -> float:
        return rms_similarity(img_path1, img_path2)

    @staticmethod
    def _write_reports(output_dir: Path, visual_report: Dict[str, Any], layout_report: Dict[str, Any]) -> None:
        (output_dir / "visual_comparison_report.json").write_text(
            json.dumps(visual_report, indent=2), encoding="utf-8"
        )
        (output_dir / "layout_report.json").write_text(
            json.dumps(layout_report, indent=2), encoding="utf-8"
        )
