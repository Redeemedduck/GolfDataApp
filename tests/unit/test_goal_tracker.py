"""Unit tests for goal tracking helpers."""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from components.goal_tracker import compute_goal_progress


class TestComputeGoalProgress(unittest.TestCase):
    """Test cases for compute_goal_progress."""

    def test_progress_within_range(self):
        """Correct ratio for values below target."""
        result = compute_goal_progress(1.20, 1.50)
        self.assertAlmostEqual(result, 0.80, places=2)

    def test_progress_at_target(self):
        """Returns 1.0 when avg equals target."""
        result = compute_goal_progress(1.49, 1.49)
        self.assertAlmostEqual(result, 1.0, places=3)

    def test_progress_exceeds_target(self):
        """Clamps to 1.0 when avg exceeds target."""
        result = compute_goal_progress(1.55, 1.49)
        self.assertEqual(result, 1.0)

    def test_missing_values_return_none(self):
        """Returns None for missing inputs."""
        self.assertIsNone(compute_goal_progress(None, 1.49))
        self.assertIsNone(compute_goal_progress(1.45, None))
        self.assertIsNone(compute_goal_progress(None, None))

    def test_zero_target_returns_none(self):
        """Returns None when target is zero."""
        self.assertIsNone(compute_goal_progress(1.45, 0))


if __name__ == "__main__":
    unittest.main()
