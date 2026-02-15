"""Tests for services/data_quality.py."""
import unittest

import pandas as pd

from services.data_quality import filter_outliers, get_outlier_summary, _apply_hard_caps, _apply_zscore


class TestFilterOutliers(unittest.TestCase):
    """Test the two-layer outlier filtering."""

    def _make_df(self, rows):
        return pd.DataFrame(rows)

    def test_empty_df(self):
        df = pd.DataFrame()
        result = filter_outliers(df)
        self.assertTrue(result.empty)

    def test_hard_caps_removes_impossible_carry(self):
        """313yd 9 Iron should be removed by hard cap (190yd)."""
        df = self._make_df([
            {"club": "9 Iron", "carry": 150, "smash": 1.25},
            {"club": "9 Iron", "carry": 313, "smash": 1.25},  # impossible
            {"club": "9 Iron", "carry": 160, "smash": 1.25},
        ])
        result = filter_outliers(df, method="caps")
        self.assertEqual(len(result), 2)
        self.assertTrue((result["carry"] <= 190).all())

    def test_hard_caps_removes_impossible_pw(self):
        """278yd PW should be removed by hard cap (180yd)."""
        df = self._make_df([
            {"club": "PW", "carry": 140, "smash": 1.20},
            {"club": "PW", "carry": 278, "smash": 1.20},  # impossible
        ])
        result = filter_outliers(df, method="caps")
        self.assertEqual(len(result), 1)

    def test_driver_within_cap_passes(self):
        """Normal 280yd Driver should pass (cap is 350)."""
        df = self._make_df([
            {"club": "Driver", "carry": 280, "smash": 1.48},
        ])
        result = filter_outliers(df, method="caps")
        self.assertEqual(len(result), 1)

    def test_universal_smash_guard(self):
        """Smash > 2.0 should be removed."""
        df = self._make_df([
            {"club": "Driver", "carry": 280, "smash": 1.48},
            {"club": "Driver", "carry": 280, "smash": 2.5},   # impossible
            {"club": "Driver", "carry": 280, "smash": 0.1},   # too low
        ])
        result = filter_outliers(df)
        self.assertEqual(len(result), 1)

    def test_universal_carry_guard(self):
        """Carry < 10 should be excluded."""
        df = self._make_df([
            {"club": "Driver", "carry": 5, "smash": 1.0},
            {"club": "Driver", "carry": 250, "smash": 1.45},
        ])
        result = filter_outliers(df)
        self.assertEqual(len(result), 1)

    def test_zscore_catches_statistical_outlier(self):
        """A single extreme value in a tight distribution should be caught."""
        rows = [{"club": "7 Iron", "carry": 160 + i, "smash": 1.30} for i in range(20)]
        rows.append({"club": "7 Iron", "carry": 300, "smash": 1.30})  # outlier
        df = self._make_df(rows)
        result = filter_outliers(df, method="zscore")
        self.assertLess(len(result), len(df))
        self.assertTrue(result["carry"].max() < 250)

    def test_null_carry_passes(self):
        """Rows with null carry should not be excluded."""
        df = self._make_df([
            {"club": "Driver", "carry": None, "smash": 1.45},
            {"club": "Driver", "carry": 280, "smash": 1.45},
        ])
        result = filter_outliers(df)
        self.assertEqual(len(result), 2)


class TestOutlierSummary(unittest.TestCase):
    def test_summary_counts(self):
        rows = [
            {"club": "9 Iron", "carry": 150, "smash": 1.25},
            {"club": "9 Iron", "carry": 313, "smash": 1.25},  # caps
            {"club": "PW", "carry": 278, "smash": 1.20},      # caps
        ]
        df = pd.DataFrame(rows)
        summary = get_outlier_summary(df)
        self.assertGreater(summary["total_removed"], 0)
        self.assertGreater(summary["by_caps"], 0)


if __name__ == "__main__":
    unittest.main()
