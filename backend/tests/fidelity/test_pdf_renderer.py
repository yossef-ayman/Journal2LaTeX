"""Unit test skeleton for PDFRenderer."""

import unittest
from app.fidelity.renderers.pdf import PDFRenderer
from app.fidelity.schemas import SourceType


class TestPDFRenderer(unittest.TestCase):
    """Test skeleton for PDFRenderer."""

    def setUp(self):
        self.renderer = PDFRenderer()

    def test_supported_source_type(self):
        self.assertEqual(self.renderer.supported_source_type, SourceType.PDF)

    def test_render_missing_file_raises_error(self):
        # Skeleton test stub
        pass


if __name__ == "__main__":
    unittest.main()
