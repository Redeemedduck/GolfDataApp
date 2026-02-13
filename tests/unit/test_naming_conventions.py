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

    def test_uneekor_format_iron7_medium(self):
        result = self.normalizer.normalize('Iron7 | Medium')
        self.assertEqual(result.normalized, '7 Iron')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_uneekor_format_iron6_medium(self):
        result = self.normalizer.normalize('Iron6 | Medium')
        self.assertEqual(result.normalized, '6 Iron')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_uneekor_format_uppercase(self):
        result = self.normalizer.normalize('IRON7 | MEDIUM')
        self.assertEqual(result.normalized, '7 Iron')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_uneekor_format_driver(self):
        result = self.normalizer.normalize('DRIVER | MEDIUM')
        self.assertEqual(result.normalized, 'Driver')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_uneekor_format_wood3_premium(self):
        result = self.normalizer.normalize('WOOD3 | PREMIUM')
        self.assertEqual(result.normalized, '3 Wood')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_uneekor_format_hybrid4(self):
        result = self.normalizer.normalize('HYBRID4 | MEDIUM')
        self.assertEqual(result.normalized, '4 Hybrid')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_wedge_pitching_reversed(self):
        result = self.normalizer.normalize('Wedge Pitching')
        self.assertEqual(result.normalized, 'PW')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_wedge_sand_reversed(self):
        result = self.normalizer.normalize('Wedge Sand')
        self.assertEqual(result.normalized, 'SW')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_wedge_50_degree_number(self):
        result = self.normalizer.normalize('Wedge 50')
        self.assertEqual(result.normalized, 'GW')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_wedge_56_degree_number(self):
        result = self.normalizer.normalize('Wedge 56')
        self.assertEqual(result.normalized, 'SW')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_iron7_no_space(self):
        result = self.normalizer.normalize('Iron7')
        self.assertEqual(result.normalized, '7 Iron')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_iron6_no_space(self):
        result = self.normalizer.normalize('Iron6')
        self.assertEqual(result.normalized, '6 Iron')
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_iron9_no_space(self):
        result = self.normalizer.normalize('Iron9')
        self.assertEqual(result.normalized, '9 Iron')
        self.assertGreaterEqual(result.confidence, 0.9)

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


class TestNormalizationPipeline(unittest.TestCase):
    """Tests for the two-tier normalization pipeline."""

    def _normalize(self, raw_value):
        from automation.naming_conventions import normalize_with_context
        return normalize_with_context(raw_value)

    # Standard clubs should pass through normalizer directly
    def test_standard_club_7_iron(self):
        result = self._normalize('7 Iron')
        self.assertEqual(result['club'], '7 Iron')
        self.assertIsNone(result['session_type'])

    def test_standard_club_driver(self):
        result = self._normalize('Driver')
        self.assertEqual(result['club'], 'Driver')

    # Session names with embedded clubs should use SessionContextParser
    def test_warmup_pw_extracts_club(self):
        result = self._normalize('Warmup Pw')
        self.assertEqual(result['club'], 'PW')
        self.assertEqual(result['session_type'], 'warmup')

    def test_dst_compressor_8_extracts_club(self):
        result = self._normalize('Dst Compressor 8')
        self.assertEqual(result['club'], '8 Iron')
        self.assertEqual(result['session_type'], 'drill')

    def test_warmup_50_no_extractable_club(self):
        result = self._normalize('Warmup 50')
        self.assertIsNone(result['club'])
        self.assertEqual(result['session_type'], 'warmup')

    def test_8_iron_dst_trainer(self):
        result = self._normalize('8 Iron Dst Trainer')
        self.assertEqual(result['club'], '8 Iron')
        self.assertEqual(result['session_type'], 'drill')

    # Pure session names with no extractable club
    def test_sgt_rd1_no_club(self):
        result = self._normalize('Sgt Rd1')
        self.assertIsNone(result['club'])
        self.assertEqual(result['session_type'], 'sim_round')

    def test_warmup_no_club(self):
        result = self._normalize('Warmup')
        self.assertIsNone(result['club'])
        self.assertEqual(result['session_type'], 'warmup')


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


class TestSessionNamerDisplayName(unittest.TestCase):
    """Tests for SessionNamer.generate_display_name and detect_session_type."""

    def setUp(self):
        self.namer = SessionNamer()

    # --- detect_session_type ---

    def test_detect_driver_focus(self):
        """Session with >60% driver shots should be 'Driver Focus'."""
        clubs = ['Driver'] * 15 + ['7 Iron'] * 5  # 75% driver
        result = self.namer.detect_session_type(clubs)
        self.assertEqual(result, 'Driver Focus')

    def test_detect_iron_work(self):
        """Session with >60% iron shots should be 'Iron Work'."""
        clubs = ['7 Iron'] * 10 + ['6 Iron'] * 8 + ['Driver'] * 2  # 90% irons
        result = self.namer.detect_session_type(clubs)
        self.assertEqual(result, 'Iron Work')

    def test_detect_short_game(self):
        """Session with >60% wedge shots should be 'Short Game'."""
        clubs = ['PW'] * 10 + ['SW'] * 8 + ['Driver'] * 2  # 90% wedges
        result = self.namer.detect_session_type(clubs)
        self.assertEqual(result, 'Short Game')

    def test_detect_mixed_practice(self):
        """Session with no dominant club category should be 'Mixed Practice'."""
        clubs = ['Driver'] * 5 + ['7 Iron'] * 5 + ['PW'] * 5
        result = self.namer.detect_session_type(clubs)
        self.assertEqual(result, 'Mixed Practice')

    def test_detect_warmup(self):
        """Session with <10 shots should be 'Warmup'."""
        clubs = ['Driver'] * 3
        result = self.namer.detect_session_type(clubs)
        self.assertEqual(result, 'Warmup')

    def test_detect_empty_clubs(self):
        """Empty club list should default to 'Mixed Practice'."""
        result = self.namer.detect_session_type([])
        self.assertEqual(result, 'Mixed Practice')

    def test_detect_uses_normalized_names(self):
        """Should work with standard normalized club names."""
        clubs = ['3 Wood'] * 8 + ['5 Wood'] * 8 + ['PW'] * 4  # 80% woods
        result = self.namer.detect_session_type(clubs)
        self.assertEqual(result, 'Woods Focus')

    # --- generate_display_name ---

    def test_display_name_driver_focus(self):
        """Full display name for driver focus session."""
        date = datetime(2026, 2, 2)
        clubs = ['Driver'] * 15 + ['7 Iron'] * 5
        result = self.namer.generate_display_name(date, clubs)
        self.assertEqual(result, '2026-02-02 Driver Focus (20 shots)')

    def test_display_name_mixed_practice(self):
        """Full display name for mixed practice session."""
        date = datetime(2026, 1, 28)
        clubs = ['Driver'] * 5 + ['7 Iron'] * 5 + ['PW'] * 5
        result = self.namer.generate_display_name(date, clubs)
        self.assertEqual(result, '2026-01-28 Mixed Practice (15 shots)')

    def test_display_name_none_date(self):
        """NULL date should use 'Unknown Date' placeholder."""
        clubs = ['Driver'] * 20
        result = self.namer.generate_display_name(None, clubs)
        self.assertEqual(result, 'Unknown Date Driver Focus (20 shots)')

    def test_display_name_string_date(self):
        """Should handle string dates (from database)."""
        clubs = ['PW'] * 15 + ['SW'] * 10
        result = self.namer.generate_display_name('2026-01-15', clubs)
        self.assertEqual(result, '2026-01-15 Short Game (25 shots)')

    def test_display_name_iso_string_date(self):
        """Should handle ISO datetime strings (YYYY-MM-DDTHH:MM:SS)."""
        clubs = ['7 Iron'] * 20
        result = self.namer.generate_display_name('2026-01-15T00:00:00', clubs)
        self.assertEqual(result, '2026-01-15 Iron Work (20 shots)')


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
