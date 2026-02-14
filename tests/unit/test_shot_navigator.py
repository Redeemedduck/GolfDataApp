"""Unit tests for shot navigator helpers."""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from components.shot_navigator import clamp_index


class TestClampIndex(unittest.TestCase):
    """Test cases for clamp_index."""

    def test_clamp_within_bounds(self):
        """Index within range is returned unchanged."""
        self.assertEqual(clamp_index(2, 5), 2)
        self.assertEqual(clamp_index(0, 5), 0)
        self.assertEqual(clamp_index(4, 5), 4)

    def test_clamp_negative(self):
        """Negative index is clamped to 0."""
        self.assertEqual(clamp_index(-1, 5), 0)
        self.assertEqual(clamp_index(-100, 5), 0)

    def test_clamp_over_max(self):
        """Index beyond total is clamped to last valid index."""
        self.assertEqual(clamp_index(5, 5), 4)
        self.assertEqual(clamp_index(100, 5), 4)

    def test_clamp_zero_total(self):
        """Zero total returns 0."""
        self.assertEqual(clamp_index(0, 0), 0)
        self.assertEqual(clamp_index(3, 0), 0)


if __name__ == "__main__":
    unittest.main()
