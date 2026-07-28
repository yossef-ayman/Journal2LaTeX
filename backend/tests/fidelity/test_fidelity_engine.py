"""Unit test skeleton for FidelityEngine."""

import unittest
from app.fidelity.engine import FidelityEngine
from app.fidelity.schemas import FidelityConfig


class TestFidelityEngine(unittest.TestCase):
    """Test skeleton for FidelityEngine."""

    def setUp(self):
        self.engine = FidelityEngine()

    def test_fidelity_config_validation(self):
        with self.assertRaises(Exception):
            FidelityConfig(dpi=-1)


if __name__ == "__main__":
    unittest.main()
