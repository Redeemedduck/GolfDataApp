"""Unit tests for trajectory visualization helpers."""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from components.trajectory_view import compute_trajectory_points


class TestTrajectoryView(unittest.TestCase):
    """Test cases for trajectory point computation."""

    def test_compute_trajectory_points(self):
        """Returns a smooth arc starting and ending near ground with expected apex."""
        points = compute_trajectory_points(
            carry=200,
            apex=30,
            launch_angle=12,
            descent_angle=40,
        )

        self.assertIsInstance(points, list)
        self.assertGreaterEqual(len(points), 10)
        self.assertIsInstance(points[0], tuple)

        first_x, first_y = points[0]
        last_x, last_y = points[-1]
        max_y = max(y for _, y in points)

        self.assertAlmostEqual(first_x, 0.0, places=3)
        self.assertAlmostEqual(first_y, 0.0, places=3)
        self.assertAlmostEqual(last_x, 200.0, places=3)
        self.assertAlmostEqual(last_y, 0.0, places=3)
        self.assertAlmostEqual(max_y, 30.0, delta=0.5)

    def test_compute_trajectory_missing_data_returns_empty(self):
        """Missing trajectory inputs return an empty list."""
        points = compute_trajectory_points(
            carry=None,
            apex=None,
            launch_angle=None,
            descent_angle=None,
        )
        self.assertEqual(points, [])


if __name__ == "__main__":
    unittest.main()
