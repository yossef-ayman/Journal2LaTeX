"""Unit test skeleton for ImageRenderer."""

import unittest
from app.fidelity.renderers.image import ImageRenderer
from app.fidelity.schemas import SourceType


class TestImageRenderer(unittest.TestCase):
    """Test skeleton for ImageRenderer."""

    def setUp(self):
        self.renderer = ImageRenderer()

    def test_supported_source_type(self):
        self.assertEqual(self.renderer.supported_source_type, SourceType.IMAGE)

    def test_render_missing_image_path_raises_error(self):
        # Skeleton test stub
        pass


if __name__ == "__main__":
    unittest.main()
