"""PDF Document Renderer implementation."""

import logging
from pathlib import Path
from typing import List
from PIL import Image
from app.fidelity.schemas import NormalizedPage, SourceType
from app.fidelity.renderers.base import DocumentRenderer
from app.fidelity.exceptions import RenderingError
from app.utils.pdf_tools import render_pdf_to_images

logger = logging.getLogger(__name__)


class PDFRenderer(DocumentRenderer):
    """Renderer implementation for PDF document files using PyMuPDF / pdf_tools."""

    @property
    def supported_source_type(self) -> SourceType:
        return SourceType.PDF

    def render(self, document_path: str, output_dir: str, dpi: int = 150) -> List[NormalizedPage]:
        """Renders PDF pages into normalized page images.

        Args:
            document_path: Path to input PDF file.
            output_dir: Path to export page images.
            dpi: Rendering resolution DPI.

        Returns:
            List of NormalizedPage objects containing dimensions and file paths.

        Raises:
            RenderingError: If the PDF file is missing or rasterization fails.
        """
        doc_path = Path(document_path)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        if not doc_path.exists():
            logger.error(f"PDF document file missing at: {document_path}")
            raise RenderingError(f"PDF document not found: {document_path}")

        try:
            image_paths = render_pdf_to_images(doc_path, out_path, dpi=dpi)
        except Exception as exc:
            logger.error(f"Failed to rasterize PDF {document_path}: {exc}")
            raise RenderingError(f"PDF rasterization failed for {document_path}: {exc}") from exc

        normalized_pages: List[NormalizedPage] = []
        for idx, img_path in enumerate(image_paths, start=1):
            with Image.open(img_path) as img:
                w, h = img.size

            normalized_pages.append(
                NormalizedPage(
                    page_number=idx,
                    image_path=str(img_path.resolve()),
                    width=w,
                    height=h,
                    dpi=dpi,
                    source_type=SourceType.PDF,
                    regions=[],
                )
            )

        logger.info(f"PDFRenderer successfully rendered {len(normalized_pages)} page(s) from {doc_path.name}")
        return normalized_pages
