"""Shared image-similarity helpers (Pillow RMS based)."""

import math
from pathlib import Path
from typing import Optional

from PIL import Image, ImageChops


def rms_similarity(
    img_path1: Path,
    img_path2: Path,
    top_fraction: Optional[float] = None,
) -> float:
    """RMS-difference similarity in [0, 1] between two images.

    Args:
        img_path1: Reference image.
        img_path2: Candidate image (resized to the reference size if needed).
        top_fraction: When set (e.g. 0.15), compare only the top strip of the
            pages -- used for header-region similarity.
    """
    try:
        with Image.open(img_path1) as im1, Image.open(img_path2) as im2:
            img1 = im1.convert("L")
            img2 = im2.convert("L")
            if img1.size != img2.size:
                img2 = img2.resize(img1.size)
            w, h = img1.size
            if top_fraction is not None:
                h = max(1, int(h * top_fraction))
                img1 = img1.crop((0, 0, w, h))
                img2 = img2.crop((0, 0, w, h))
            diff = ImageChops.difference(img1, img2)
            if diff.getbbox() is None:
                return 1.0
            hist = diff.histogram()
            sq = sum(count * (value ** 2) for value, count in enumerate(hist))
            rms = math.sqrt(sq / float(w * h))
            return max(0.0, min(1.0, 1.0 - rms / 255.0))
    except Exception:
        return 0.0
