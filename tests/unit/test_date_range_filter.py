"""Unit tests for date range filtering."""

import sys
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from components.date_range_filter import filter_by_date_range


class TestDateRangeFilter(unittest.TestCase):
    """Test cases for filter_by_date_range()."""

    def test_filter_with_both_dates(self):
        """Filters rows to dates inside inclusive [start, end] range."""
        df = pd.DataFrame(
            {
                "shot_id": ["s1", "s2", "s3", "s4"],
                "session_date": ["2026-01-01", "2026-01-10", "2026-01-20", "2026-02-01"],
            }
        )

        result = filter_by_date_range(df, date(2026, 1, 5), date(2026, 1, 31))

        self.assertEqual(len(result), 2)
        self.assertListEqual(result["shot_id"].tolist(), ["s2", "s3"])

    def test_filter_with_start_only(self):
        """Applies only lower bound when end is None."""
        df = pd.DataFrame(
            {
                "shot_id": ["s1", "s2", "s3"],
                "session_date": ["2026-01-01", "2026-01-10", "2026-01-20"],
            }
        )

        result = filter_by_date_range(df, date(2026, 1, 10), None)

        self.assertEqual(len(result), 2)
        self.assertListEqual(result["shot_id"].tolist(), ["s2", "s3"])

    def test_filter_with_no_dates_returns_all(self):
        """Returns all rows when both start and end are None."""
        df = pd.DataFrame(
            {
                "shot_id": ["s1", "s2", "s3"],
                "session_date": ["2026-01-01", "2026-01-10", "2026-01-20"],
            }
        )

        result = filter_by_date_range(df, None, None)

        self.assertEqual(len(result), len(df))
        self.assertListEqual(result["shot_id"].tolist(), df["shot_id"].tolist())
        self.assertIsNot(result, df)

    def test_filter_empty_dataframe(self):
        """Empty DataFrame stays empty."""
        df = pd.DataFrame(columns=["shot_id", "session_date"])

        result = filter_by_date_range(df, date(2026, 1, 1), date(2026, 1, 31))

        self.assertTrue(result.empty)
        self.assertListEqual(result.columns.tolist(), df.columns.tolist())


if __name__ == "__main__":
    unittest.main()
