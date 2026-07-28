"""Image Document Renderer implementation."""

import logging
from pathlib import Path
from typing import List
from PIL import Image
from app.fidelity.schemas import NormalizedPage, SourceType
from app.fidelity.renderers.base import DocumentRenderer
from app.fidelity.exceptions import RenderingError

logger = logging.getLogger(__name__)


class ImageRenderer(DocumentRenderer):
    """Renderer implementation for image files or folders of images."""

    @property
    def supported_source_type(self) -> SourceType:
        return SourceType.IMAGE

    def render(self, document_path: str, output_dir: str, dpi: int = 150) -> List[NormalizedPage]:
        """Loads and normalizes raw page image files.

        Args:
            document_path: Path to an image file or directory containing page images.
            output_dir: Path to export processed page images.
            dpi: Target resolution DPI.

        Returns:
            List of NormalizedPage objects.

        Raises:
            RenderingError: If image file or directory is missing or unreadable.
        """
        input_path = Path(document_path)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        if not input_path.exists():
            logger.error(f"Image path missing at: {document_path}")
            raise RenderingError(f"Image path not found: {document_path}")

        image_files: List[Path] = []
        if input_path.is_file():
            image_files.append(input_path)
        elif input_path.is_dir():
            valid_exts = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}
            image_files = sorted(
                [f for f in input_path.iterdir() if f.suffix.lower() in valid_exts]
            )

        if not image_files:
            logger.warning(f"No valid image files found at: {document_path}")
            raise RenderingError(f"No valid image files found at: {document_path}")

        normalized_pages: List[NormalizedPage] = []
        for idx, src_file in enumerate(image_files, start=1):
            dest_file = out_path / f"page_{idx}.png"

            try:
                with Image.open(src_file) as img:
                    rgb_img = img.convert("RGB")
                    rgb_img.save(dest_file, "PNG")
                    w, h = rgb_img.size
            except Exception as exc:
                logger.error(f"Failed to process image file {src_file}: {exc}")
                raise RenderingError(f"Failed to process image file {src_file}: {exc}") from exc

            normalized_pages.append(
                NormalizedPage(
                    page_number=idx,
                    image_path=str(dest_file.resolve()),
                    width=w,
                    height=h,
                    dpi=dpi,
                    source_type=SourceType.IMAGE,
                    regions=[],
                )
            )

        logger.info(f"ImageRenderer successfully processed {len(normalized_pages)} page image(s).")
        return normalized_pages
