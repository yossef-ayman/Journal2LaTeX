"""Image Normalization, Canvas Padding, and Dimension Alignment Utilities."""

from pathlib import Path
from typing import Tuple, Optional
from PIL import Image, ImageOps
from app.fidelity.schemas import NormalizedPage, RenderingConfig, AlignmentMode


class ImageConverter:
    """Pre-processes and normalizes page images for exact dimension and canvas alignment."""

    def normalize_pair(
        self,
        source_page: NormalizedPage,
        target_page: NormalizedPage,
        output_dir: str,
        rendering_config: Optional[RenderingConfig] = None,
    ) -> Tuple[NormalizedPage, NormalizedPage]:
        """Ensures source and target page images have identical pixel dimensions and color spaces.

        Args:
            source_page: Source reference normalized page.
            target_page: Target generated normalized page.
            output_dir: Directory where normalized images will be written.
            rendering_config: Optional rendering configuration for alignment mode & background color.

        Returns:
            Tuple of updated (source_page, target_page) with matching dimensions.
        """
        cfg = rendering_config or RenderingConfig()
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        src_img_path = Path(source_page.image_path)
        tgt_img_path = Path(target_page.image_path)

        with Image.open(src_img_path) as src_img, Image.open(tgt_img_path) as tgt_img:
            src_rgb = src_img.convert("RGB")
            tgt_rgb = tgt_img.convert("RGB")

            # Handle Auto Rotation if enabled
            if cfg.auto_rotation:
                src_rgb = ImageOps.exif_transpose(src_rgb)
                tgt_rgb = ImageOps.exif_transpose(tgt_rgb)

            target_w = max(src_rgb.width, tgt_rgb.width)
            target_h = max(src_rgb.height, tgt_rgb.height)

            # Pad / Align source image
            norm_src_img = self._align_image(src_rgb, target_w, target_h, cfg)
            # Pad / Align target image
            norm_tgt_img = self._align_image(tgt_rgb, target_w, target_h, cfg)

            norm_src_path = out_path / f"norm_source_p{source_page.page_number}.png"
            norm_tgt_path = out_path / f"norm_target_p{target_page.page_number}.png"

            norm_src_img.save(norm_src_path, "PNG")
            norm_tgt_img.save(norm_tgt_path, "PNG")

        updated_src = source_page.model_copy(
            update={
                "image_path": str(norm_src_path.resolve()),
                "width": target_w,
                "height": target_h,
            }
        )
        updated_tgt = target_page.model_copy(
            update={
                "image_path": str(norm_tgt_path.resolve()),
                "width": target_w,
                "height": target_h,
            }
        )

        return updated_src, updated_tgt

    def _align_image(
        self,
        img: Image.Image,
        target_width: int,
        target_height: int,
        config: RenderingConfig,
    ) -> Image.Image:
        """Pads or scales an image according to AlignmentMode configuration."""
        if img.width == target_width and img.height == target_height:
            return img

        bg_color = config.background_color or "#FFFFFF"
        mode = config.alignment_mode

        if mode == AlignmentMode.FILL:
            return img.resize((target_width, target_height), Image.Resampling.LANCZOS)

        if mode == AlignmentMode.FIT:
            img = ImageOps.contain(img, (target_width, target_height), Image.Resampling.LANCZOS)

        padded = Image.new("RGB", (target_width, target_height), bg_color)

        if mode == AlignmentMode.TOP_LEFT:
            offset_x, offset_y = 0, 0
        elif mode == AlignmentMode.TOP:
            offset_x = (target_width - img.width) // 2
            offset_y = 0
        else:  # CENTER or FIT
            offset_x = (target_width - img.width) // 2
            offset_y = (target_height - img.height) // 2

        padded.paste(img, (offset_x, offset_y))
        return padded
