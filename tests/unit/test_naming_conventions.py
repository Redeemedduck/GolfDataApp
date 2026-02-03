"""Tests for automation.naming_conventions module."""

import unittest
from datetime import datetime
from automation.naming_conventions import (
    ClubNameNormalizer,
    SessionNamer,
    AutoTagger,
    SessionContextParser,
    normalize_club,
    normalize_clubs,
    parse_listing_date,
)


class TestClubNameNormalizer(unittest.TestCase):
    """Tests for ClubNameNormalizer."""

    def setUp(self):
        self.normalizer = ClubNameNormalizer()

    # --- Exact matches ---

    def test_exact_match_driver(self):
        result = self.normalizer.normalize("Driver")
        self.assertEqual(result.normalized, "Driver")
        self.assertEqual(result.confidence, 1.0)

    def test_exact_match_case_insensitive(self):
        result = self.normalizer.normalize("driver")
        self.assertEqual(result.normalized, "Driver")
        self.assertEqual(result.confidence, 1.0)

    def test_exact_match_7_iron(self):
        result = self.normalizer.normalize("7 Iron")
        self.assertEqual(result.normalized, "7 Iron")

    def test_exact_match_pw(self):
        result = self.normalizer.normalize("PW")
        self.assertEqual(result.normalized, "PW")

    # --- Alias patterns ---

    def test_alias_dr_to_driver(self):
        result = self.normalizer.normalize("dr")
        self.assertEqual(result.normalized, "Driver")

    def test_alias_7i_to_7_iron(self):
        result = self.normalizer.normalize("7i")
        self.assertEqual(result.normalized, "7 Iron")

    def test_alias_3w_to_3_wood(self):
        result = self.normalizer.normalize("3w")
        self.assertEqual(result.normalized, "3 Wood")

    def test_alias_4h_to_4_hybrid(self):
        result = self.normalizer.normalize("4h")
        self.assertEqual(result.normalized, "4 Hybrid")

    def test_alias_sand_to_sw(self):
        result = self.normalizer.normalize("sand")
        self.assertEqual(result.normalized, "SW")

    def test_alias_pitching_wedge(self):
        result = self.normalizer.normalize("pitching wedge")
        self.assertEqual(result.normalized, "PW")

    def test_alias_lob_to_lw(self):
        result = self.normalizer.normalize("lob")
        self.assertEqual(result.normalized, "LW")

    def test_alias_putter(self):
        result = self.normalizer.normalize("putt")
        self.assertEqual(result.normalized, "Putter")

    # --- Degree-based wedges ---

    def test_degree_56_to_sw(self):
        result = self.normalizer.normalize("56 deg")
        self.assertEqual(result.normalized, "SW")

    def test_degree_60_to_lw(self):
        result = self.normalizer.normalize("60 deg")
        self.assertEqual(result.normalized, "LW")

    def test_degree_46_to_pw(self):
        result = self.normalizer.normalize("46 deg")
        self.assertEqual(result.normalized, "PW")

    # --- Edge cases ---

    def test_empty_string(self):
        result = self.normalizer.normalize("")
        self.assertEqual(result.normalized, "Unknown")
        self.assertEqual(result.confidence, 0.0)

    def test_unknown_club(self):
        result = self.normalizer.normalize("banana")
        self.assertEqual(result.normalized, "Banana")
        self.assertLess(result.confidence, 0.5)

    def test_whitespace_handling(self):
        result = self.normalizer.normalize("  7i  ")
        self.assertEqual(result.normalized, "7 Iron")

    # --- Custom mappings ---

    def test_custom_mapping(self):
        self.normalizer.add_custom_mapping("my club", "7 Iron")
        result = self.normalizer.normalize("my club")
        self.assertEqual(result.normalized, "7 Iron")
        self.assertEqual(result.confidence, 1.0)

    # --- Batch normalization ---

    def test_normalize_all(self):
        result = self.normalizer.normalize_all(["dr", "7i", "pw"])
        self.assertEqual(result, ["Driver", "7 Iron", "PW"])

    # --- Report ---

    def test_normalization_report(self):
        report = self.normalizer.get_normalization_report(["Driver", "banana"])
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["high_confidence"], 1)
        self.assertEqual(report["low_confidence"], 1)


class TestConvenienceFunctions(unittest.TestCase):
    """Test module-level convenience functions."""

    def test_normalize_club(self):
        self.assertEqual(normalize_club("7i"), "7 Iron")

    def test_normalize_clubs(self):
        self.assertEqual(normalize_clubs(["dr", "pw"]), ["Driver", "PW"])


class TestSessionNamer(unittest.TestCase):
    """Tests for SessionNamer."""

    def setUp(self):
        self.namer = SessionNamer()
        self.date = datetime(2026, 1, 25)

    def test_practice_session(self):
        name = self.namer.generate_name("practice", self.date)
        self.assertEqual(name, "Practice - Jan 25, 2026")

    def test_drill_with_focus(self):
        name = self.namer.generate_name("drill", self.date, drill_focus="Driver Consistency")
        self.assertEqual(name, "Drill - Driver Consistency - Jan 25, 2026")

    def test_round_with_course(self):
        name = self.namer.generate_name("round", self.date, course_name="Pebble Beach")
        self.assertEqual(name, "Pebble Beach Round - Jan 25, 2026")

    def test_fitting_with_club(self):
        name = self.namer.generate_name("fitting", self.date, clubs_used=["Driver"])
        self.assertEqual(name, "Fitting - Driver - Jan 25, 2026")

    def test_unknown_type_capitalized(self):
        name = self.namer.generate_name("custom", self.date)
        self.assertEqual(name, "Custom - Jan 25, 2026")

    def test_infer_warmup(self):
        result = self.namer.infer_session_type(5, ["Driver"])
        self.assertEqual(result, "warmup")

    def test_infer_drill(self):
        # 1 club + 50 shots: drill check (<=2 clubs, >=30 shots) hits before fitting
        result = self.namer.infer_session_type(50, ["Driver"])
        self.assertEqual(result, "drill")

    def test_infer_practice(self):
        result = self.namer.infer_session_type(30, ["Driver", "7 Iron", "PW"])
        self.assertEqual(result, "practice")


class TestAutoTagger(unittest.TestCase):
    """Tests for AutoTagger."""

    def setUp(self):
        self.tagger = AutoTagger()

    def test_driver_focus(self):
        tags = self.tagger.auto_tag(["Driver"], 50)
        self.assertIn("Driver Focus", tags)

    def test_short_game(self):
        tags = self.tagger.auto_tag(["PW", "SW", "LW"], 30)
        self.assertIn("Short Game", tags)

    def test_full_bag(self):
        clubs = [f"{i} Iron" for i in range(3, 10)] + ["Driver", "3 Wood", "PW"]
        tags = self.tagger.auto_tag(clubs, 50)
        self.assertIn("Full Bag", tags)

    def test_high_volume(self):
        tags = self.tagger.auto_tag(["Driver", "7 Iron"], 150)
        self.assertIn("High Volume", tags)

    def test_warmup(self):
        tags = self.tagger.auto_tag(["Driver"], 5)
        self.assertIn("Warmup", tags)

    def test_iron_work(self):
        tags = self.tagger.auto_tag(["5 Iron", "6 Iron", "7 Iron"], 45)
        self.assertIn("Iron Work", tags)

    def test_custom_rule(self):
        self.tagger.add_custom_rule(
            "night_session",
            lambda clubs, count, **kw: count > 200,
            "Marathon"
        )
        tags = self.tagger.auto_tag(["Driver"], 250)
        self.assertIn("Marathon", tags)


class TestSessionContextParser(unittest.TestCase):
    """Tests for SessionContextParser, including listing date parsing."""

    def setUp(self):
        self.parser = SessionContextParser()

    def test_parse_listing_date_full_month(self):
        """Test parsing 'January 15, 2026' format."""
        result = self.parser.parse_listing_date("January 15, 2026")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_listing_date_short_month(self):
        """Test parsing 'Jan 15, 2026' format."""
        result = self.parser.parse_listing_date("Jan 15, 2026")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_listing_date_iso_format(self):
        """Test parsing '2026-01-15' format."""
        result = self.parser.parse_listing_date("2026-01-15")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_listing_date_us_format(self):
        """Test parsing '01/15/2026' format."""
        result = self.parser.parse_listing_date("01/15/2026")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_listing_date_no_comma(self):
        """Test parsing 'January 15 2026' format (no comma)."""
        result = self.parser.parse_listing_date("January 15 2026")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_listing_date_with_whitespace(self):
        """Test that whitespace is trimmed."""
        result = self.parser.parse_listing_date("  February 20, 2026  ")
        self.assertIsNotNone(result)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 20)

    def test_parse_listing_date_invalid(self):
        """Test that invalid dates return None."""
        result = self.parser.parse_listing_date("Not a date")
        self.assertIsNone(result)

    def test_parse_listing_date_empty(self):
        """Test that empty string returns None."""
        result = self.parser.parse_listing_date("")
        self.assertIsNone(result)

    def test_parse_listing_date_convenience_function(self):
        """Test the convenience function."""
        result = parse_listing_date("March 5, 2026")
        self.assertIsNotNone(result)
        self.assertEqual(result.month, 3)
        self.assertEqual(result.day, 5)


if __name__ == "__main__":
    unittest.main()
