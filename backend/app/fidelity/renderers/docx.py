"""DOCX Document Renderer implementation."""

import sys
import shutil
import logging
import subprocess
from pathlib import Path
from typing import List, Optional
from app.fidelity.schemas import NormalizedPage, SourceType
from app.fidelity.renderers.base import DocumentRenderer
from app.fidelity.renderers.pdf import PDFRenderer
from app.fidelity.exceptions import DocxConversionError, RenderingError
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocxRenderer(DocumentRenderer):
    """Renderer implementation for DOCX files (DOCX -> Reference PDF -> Images)."""

    def __init__(self, pdf_renderer: Optional[DocumentRenderer] = None):
        """Initializes DocxRenderer with an injected PDF renderer dependency.

        Args:
            pdf_renderer: Optional DocumentRenderer instance for rasterizing reference PDF.
        """
        self.pdf_renderer: DocumentRenderer = pdf_renderer or PDFRenderer()

    @property
    def supported_source_type(self) -> SourceType:
        return SourceType.DOCX

    def _convert_docx_to_pdf(self, docx_path: Path, pdf_path: Path) -> None:
        """Converts DOCX file to reference PDF using MS Word COM (on Windows) or LibreOffice."""
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        if sys.platform == "win32":
            try:
                self._convert_with_word_com(docx_path, pdf_path)
                if pdf_path.exists() and pdf_path.stat().st_size > 0:
                    logger.info("Successfully converted DOCX to PDF using MS Word COM.")
                    return
            except Exception as exc:
                logger.warning(f"MS Word COM conversion failed: {exc}. Trying LibreOffice fallback.")

        soffice = shutil.which(settings.SOFFICE_PATH) or shutil.which("libreoffice") or shutil.which("soffice")
        if soffice:
            self._convert_with_soffice(soffice, docx_path, pdf_path)
            return

        raise DocxConversionError(
            f"No DOCX-to-PDF backend available to convert {docx_path.name} (need MS Word or LibreOffice)."
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

    @staticmethod
    def _convert_with_soffice(soffice: str, docx_path: Path, pdf_path: Path) -> None:
        out_dir = pdf_path.parent
        result = subprocess.run(
            [
                soffice, "--headless", "--norestore", "--convert-to", "pdf",
                "--outdir", str(out_dir), str(docx_path.resolve())
            ],
            capture_output=True, text=True, check=False,
            timeout=120,
        )
        produced = out_dir / (docx_path.stem + ".pdf")
        if result.returncode != 0 or not produced.exists():
            raise DocxConversionError(f"LibreOffice conversion failed: {result.stderr.strip()[:300]}")
        if produced != pdf_path:
            produced.replace(pdf_path)

    def render(self, document_path: str, output_dir: str, dpi: int = 150) -> List[NormalizedPage]:
        """Converts DOCX to reference PDF and renders pages into NormalizedPage objects.

        Args:
            document_path: Path to input DOCX document.
            output_dir: Path to export page images.
            dpi: Rendering resolution DPI.

        Returns:
            List of NormalizedPage objects.

        Raises:
            RenderingError: If DOCX document is missing or conversion/rasterization fails.
        """
        docx_path = Path(document_path)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        if not docx_path.exists():
            logger.error(f"DOCX document file missing at: {document_path}")
            raise RenderingError(f"DOCX document not found: {document_path}")

        temp_pdf_path = out_path / "reference_docx.pdf"
        self._convert_docx_to_pdf(docx_path, temp_pdf_path)

        pages = self.pdf_renderer.render(str(temp_pdf_path), str(out_path / "pages"), dpi=dpi)
        for page in pages:
            page.source_type = SourceType.DOCX

        logger.info(f"DocxRenderer successfully processed {len(pages)} page(s) from {docx_path.name}")
        return pages
