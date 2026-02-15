"""Tests for services/time_window.py."""
import unittest
from datetime import datetime, timedelta

import pandas as pd

from services.time_window import filter_by_window, TIME_WINDOWS


class TestFilterByWindow(unittest.TestCase):

    def _make_df(self, dates):
        return pd.DataFrame({
            "session_date": dates,
            "carry": [200] * len(dates),
        })

    def test_empty_df(self):
        df = pd.DataFrame()
        result = filter_by_window(df, "6mo")
        self.assertTrue(result.empty)

    def test_all_window_returns_everything(self):
        dates = [
            (datetime.now() - timedelta(days=500)).strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
        ]
        df = self._make_df(dates)
        result = filter_by_window(df, "all")
        self.assertEqual(len(result), 2)

    def test_3mo_filters_old_data(self):
        dates = [
            (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d"),  # old
            (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),   # recent
            datetime.now().strftime("%Y-%m-%d"),                          # today
        ]
        df = self._make_df(dates)
        result = filter_by_window(df, "3mo")
        self.assertEqual(len(result), 2)

    def test_6mo_default(self):
        dates = [
            (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d"),  # ~7mo, out
            (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),   # 3mo, in
        ]
        df = self._make_df(dates)
        result = filter_by_window(df, "6mo")
        self.assertEqual(len(result), 1)

    def test_null_dates_kept(self):
        """Rows with null session_date should be kept (not excluded)."""
        dates = [None, datetime.now().strftime("%Y-%m-%d")]
        df = self._make_df(dates)
        result = filter_by_window(df, "3mo")
        self.assertEqual(len(result), 2)

    def test_falls_back_to_date_added(self):
        """If session_date is all null, uses date_added."""
        df = pd.DataFrame({
            "date_added": [
                (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d"),
                datetime.now().strftime("%Y-%m-%d"),
            ],
            "carry": [200, 200],
        })
        result = filter_by_window(df, "6mo")
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
