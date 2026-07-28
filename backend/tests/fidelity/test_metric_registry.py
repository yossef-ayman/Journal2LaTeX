"""Unit test skeleton for MetricRegistry."""

import unittest
from app.fidelity.metrics import MetricRegistry
from app.fidelity.schemas import FidelityConfig


class TestMetricRegistry(unittest.TestCase):
    """Test skeleton for MetricRegistry."""

    def setUp(self):
        self.registry = MetricRegistry()

    def test_default_active_metrics(self):
        active = [m.name for m in self.registry.get_active_metrics(FidelityConfig())]
        self.assertIn("ssim", active)
        self.assertIn("pixel_diff", active)
        self.assertIn("layout", active)


if __name__ == "__main__":
    unittest.main()
