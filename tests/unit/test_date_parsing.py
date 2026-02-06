"""
Unit tests for date parsing functionality.

Tests the _parse_date_from_text method in uneekor_portal.py
to ensure all date formats are correctly parsed.
"""

import unittest
from datetime import datetime
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.uneekor_portal import UneekorPortalNavigator


class TestDateParsing(unittest.TestCase):
    """Test date parsing from various text formats."""

    def setUp(self):
        """Set up test fixtures."""
        # Create navigator instance for testing _parse_date_from_text
        # Note: We don't need an actual browser client for parsing tests
        self.navigator = UneekorPortalNavigator.__new__(UneekorPortalNavigator)

    def test_parse_yyyy_dot_mm_dot_dd(self):
        """Test parsing YYYY.MM.DD format (Uneekor report page format)."""
        text = "Session Report 2026.01.15 - Driver Practice"
        result = self.navigator._parse_date_from_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_yyyy_dash_mm_dash_dd(self):
        """Test parsing YYYY-MM-DD format (ISO format)."""
        text = "Report from 2025-12-25"
        result = self.navigator._parse_date_from_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 25)

    def test_parse_dd_dot_mm_dot_yyyy(self):
        """Test parsing DD.MM.YYYY format (European format with dots)."""
        text = "Session on 25.12.2025"
        result = self.navigator._parse_date_from_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 25)

    def test_parse_mm_slash_dd_slash_yyyy(self):
        """Test parsing MM/DD/YYYY format (US format)."""
        text = "Recorded 01/15/2026"
        result = self.navigator._parse_date_from_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        # Note: This could be 01/15 (MM/DD) or 01/15 (DD/MM)
        # The parser tries MM/DD first
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_abbreviated_month(self):
        """Test parsing Jan 25, 2026 format (abbreviated month)."""
        text = "Session from Jan 25, 2026"
        result = self.navigator._parse_date_from_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 25)

    def test_parse_abbreviated_month_no_comma(self):
        """Test parsing Jan 25 2026 format (abbreviated month, no comma)."""
        text = "Recorded Jan 25 2026"
        result = self.navigator._parse_date_from_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 25)

    def test_parse_full_month_name(self):
        """Test parsing January 25, 2026 format (full month)."""
        text = "Practice session January 25, 2026"
        result = self.navigator._parse_date_from_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 25)

    def test_parse_dd_month_yyyy(self):
        """Test parsing 25 January 2026 format."""
        text = "Session 25 January 2026 practice"
        result = self.navigator._parse_date_from_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 25)

    def test_parse_none_for_empty_text(self):
        """Test that empty text returns None."""
        self.assertIsNone(self.navigator._parse_date_from_text(""))
        self.assertIsNone(self.navigator._parse_date_from_text(None))

    def test_parse_none_for_no_date(self):
        """Test that text without a date returns None."""
        text = "Driver Practice Session with no date mentioned"
        result = self.navigator._parse_date_from_text(text)
        self.assertIsNone(result)

    def test_parse_date_in_longer_text(self):
        """Test parsing date embedded in longer text."""
        text = """
        Session Report
        Date: 2026.01.15
        Clubs: Driver, 7 Iron
        Total Shots: 45
        """
        result = self.navigator._parse_date_from_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_various_months(self):
        """Test parsing various month abbreviations."""
        test_cases = [
            ("Feb 14, 2026", 2, 14),
            ("Mar 17, 2026", 3, 17),
            ("Apr 01, 2026", 4, 1),
            ("May 15, 2026", 5, 15),
            ("Jun 20, 2026", 6, 20),
            ("Jul 04, 2026", 7, 4),
            ("Aug 31, 2026", 8, 31),
            ("Sep 22, 2026", 9, 22),
            ("Oct 10, 2026", 10, 10),
            ("Nov 25, 2026", 11, 25),
            ("Dec 31, 2026", 12, 31),
        ]
        for text, expected_month, expected_day in test_cases:
            with self.subTest(text=text):
                result = self.navigator._parse_date_from_text(text)
                self.assertIsNotNone(result, f"Failed to parse: {text}")
                self.assertEqual(result.month, expected_month)
                self.assertEqual(result.day, expected_day)


class TestClubParsing(unittest.TestCase):
    """Test club name parsing from text."""

    def setUp(self):
        """Set up test fixtures."""
        self.navigator = UneekorPortalNavigator.__new__(UneekorPortalNavigator)

    def test_parse_clubs_with_count(self):
        """Test parsing clubs in (count) Club format."""
        text = "(5) Driver (10) 7 Iron (3) Pitching Wedge"
        result = self.navigator._parse_clubs_from_text(text)
        self.assertIn("Driver", result)

    def test_parse_empty_text(self):
        """Test that empty text returns empty list."""
        self.assertEqual(self.navigator._parse_clubs_from_text(""), [])
        self.assertEqual(self.navigator._parse_clubs_from_text(None), [])


if __name__ == '__main__':
    unittest.main()
