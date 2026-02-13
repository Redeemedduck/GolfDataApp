"""Tests for SessionClassifier, enhanced ClubNameNormalizer, and data siloing."""

import unittest
import pandas as pd
from datetime import datetime
from automation.naming_conventions import (
    ClubNameNormalizer,
    SessionNamer,
    AutoTagger,
    SessionClassifier,
    ClassificationResult,
    classify_session,
    classify_session_df,
    normalize_club,
)


# ============================================================================
# ENHANCED CLUB NAME NORMALIZATION TESTS
# ============================================================================

class TestSimulatorClubPatterns(unittest.TestCase):
    """Tests for simulator-specific club name patterns."""

    def setUp(self):
        self.normalizer = ClubNameNormalizer()

    # --- M-prefixed formats (common in Uneekor systems) ---

    def test_m_prefixed_iron(self):
        result = self.normalizer.normalize("m7i")
        self.assertEqual(result.normalized, "7 Iron")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_m_prefixed_iron_with_space(self):
        result = self.normalizer.normalize("m 8 iron")
        self.assertEqual(result.normalized, "8 Iron")

    def test_m_prefixed_wood(self):
        result = self.normalizer.normalize("m3w")
        self.assertEqual(result.normalized, "3 Wood")

    def test_m_prefixed_wood_full(self):
        result = self.normalizer.normalize("m 5 wood")
        self.assertEqual(result.normalized, "5 Wood")

    def test_m_prefixed_hybrid(self):
        result = self.normalizer.normalize("m4h")
        self.assertEqual(result.normalized, "4 Hybrid")

    def test_m_prefixed_wedge_pw(self):
        result = self.normalizer.normalize("mpw")
        self.assertEqual(result.normalized, "PW")

    def test_m_prefixed_wedge_sw(self):
        result = self.normalizer.normalize("m sw")
        self.assertEqual(result.normalized, "SW")

    # --- Reversed formats ---

    def test_reversed_wood(self):
        result = self.normalizer.normalize("wood 3")
        self.assertEqual(result.normalized, "3 Wood")

    def test_reversed_hybrid(self):
        result = self.normalizer.normalize("hybrid 5")
        self.assertEqual(result.normalized, "5 Hybrid")

    def test_fw_prefix(self):
        result = self.normalizer.normalize("fw3")
        self.assertEqual(result.normalized, "3 Wood")

    # --- Utility/alternate names ---

    def test_utility_club(self):
        result = self.normalizer.normalize("3ut")
        self.assertEqual(result.normalized, "3 Hybrid")

    def test_utility_full(self):
        result = self.normalizer.normalize("utility 4")
        self.assertEqual(result.normalized, "4 Hybrid")

    # --- Driver variations ---

    def test_driver_drv(self):
        result = self.normalizer.normalize("drv")
        self.assertEqual(result.normalized, "Driver")

    def test_driver_dvr(self):
        result = self.normalizer.normalize("dvr")
        self.assertEqual(result.normalized, "Driver")

    def test_driver_sim_suffix(self):
        result = self.normalizer.normalize("driver sim")
        self.assertEqual(result.normalized, "Driver")

    # --- Iron abbreviations ---

    def test_iron_ir_suffix(self):
        result = self.normalizer.normalize("7ir")
        self.assertEqual(result.normalized, "7 Iron")

    def test_1_iron(self):
        result = self.normalizer.normalize("1 iron")
        self.assertEqual(result.normalized, "1 Iron")

    def test_1_iron_alias(self):
        result = self.normalizer.normalize("1i")
        self.assertEqual(result.normalized, "1 Iron")

    def test_one_iron(self):
        result = self.normalizer.normalize("one iron")
        self.assertEqual(result.normalized, "1 Iron")

    # --- Iron+context compound names ---

    def test_iron_compound_approach(self):
        result = self.normalizer.normalize("7 iron approach")
        self.assertEqual(result.normalized, "7 Iron")

    def test_iron_compound_dst(self):
        result = self.normalizer.normalize("8iron dst")
        self.assertEqual(result.normalized, "8 Iron")

    # --- Bare numbers ---

    def test_bare_number_iron(self):
        """Bare single digit should map to iron with lower confidence."""
        result = self.normalizer.normalize("7")
        self.assertEqual(result.normalized, "7 Iron")
        self.assertLess(result.confidence, 0.9)  # Lower confidence

    def test_bare_number_1(self):
        result = self.normalizer.normalize("1")
        self.assertEqual(result.normalized, "1 Iron")

    # --- Degree-based wedge (bare number) ---

    def test_bare_degree_56(self):
        result = self.normalizer.normalize("56")
        self.assertEqual(result.normalized, "SW")
        self.assertGreaterEqual(result.confidence, 0.8)

    def test_bare_degree_60(self):
        result = self.normalizer.normalize("60")
        self.assertEqual(result.normalized, "LW")

    def test_bare_degree_46(self):
        result = self.normalizer.normalize("46")
        self.assertEqual(result.normalized, "PW")

    def test_bare_degree_50(self):
        result = self.normalizer.normalize("50")
        self.assertEqual(result.normalized, "GW")

    # --- Wood abbreviations ---

    def test_wood_wd_suffix(self):
        result = self.normalizer.normalize("3wd")
        self.assertEqual(result.normalized, "3 Wood")

    def test_wood_wd_with_space(self):
        result = self.normalizer.normalize("5 wd")
        self.assertEqual(result.normalized, "5 Wood")


# ============================================================================
# SESSION CLASSIFIER TESTS
# ============================================================================

class TestSessionClassifier(unittest.TestCase):
    """Tests for SessionClassifier."""

    def setUp(self):
        self.classifier = SessionClassifier()

    # --- Sim round detection ---

    def test_sim_round_full_bag_sequence(self):
        """A round-like sequence with diverse clubs and hole patterns."""
        clubs = (
            ['Driver', '7 Iron', 'PW'] +     # Hole 1
            ['Driver', '5 Iron', 'SW'] +      # Hole 2
            ['3 Wood', '6 Iron', 'PW'] +      # Hole 3
            ['Driver', '8 Iron', 'GW'] +      # Hole 4
            ['7 Iron', 'SW'] +                # Hole 5 (par 3)
            ['Driver', '4 Iron', '9 Iron', 'PW'] +  # Hole 6
            ['3 Wood', '5 Iron', 'SW'] +      # Hole 7
            ['Driver', '6 Iron', 'PW'] +      # Hole 8
            ['8 Iron', 'GW'] +                # Hole 9 (par 3)
            ['Driver', '7 Iron', 'PW'] +      # Hole 10
            ['Driver', '5 Iron', 'SW'] +      # Hole 11
            ['3 Wood', '6 Iron', 'AW'] +      # Hole 12
            ['Driver', '8 Iron', 'PW'] +      # Hole 13
            ['9 Iron', 'LW'] +                # Hole 14 (par 3)
            ['Driver', '4 Iron', 'PW', 'SW'] +  # Hole 15
            ['Driver', '5 Iron', 'GW'] +      # Hole 16
            ['3 Wood', '7 Iron', 'PW'] +      # Hole 17
            ['Driver', '6 Iron', 'SW']        # Hole 18
        )
        result = self.classifier.classify(clubs)
        self.assertEqual(result.category, 'sim_round')
        self.assertGreaterEqual(result.confidence, 0.7)
        self.assertGreater(result.signals.get('hole_sequences', 0), 5)

    def test_sim_round_with_1_iron(self):
        """Sim round with 1 Iron (common in simulator play)."""
        clubs = (
            ['1 Iron', '7 Iron', 'PW'] +
            ['Driver', '5 Iron', 'SW'] +
            ['1 Iron', '6 Iron', 'GW'] +
            ['Driver', '8 Iron', 'PW'] +
            ['9 Iron', 'SW'] +
            ['1 Iron', '4 Iron', 'PW'] +
            ['Driver', '5 Iron', 'AW'] +
            ['1 Iron', '7 Iron', 'SW'] +
            ['8 Iron', 'LW'] +
            ['Driver', '6 Iron', 'PW']
        )
        result = self.classifier.classify(clubs)
        self.assertEqual(result.category, 'sim_round')
        self.assertTrue(result.signals.get('has_1_iron'))

    def test_context_hint_sgt_round(self):
        """Context hint 'Sgt Rd1' should trigger sim round classification."""
        clubs = ['Driver'] * 15  # Even with all driver, context overrides
        result = self.classifier.classify(clubs, context_hint='Sgt Rd1')
        self.assertEqual(result.category, 'sim_round')
        self.assertGreaterEqual(result.confidence, 0.9)

    # --- Practice detection ---

    def test_fitting_single_driver_high_volume(self):
        """50 Driver shots should classify as fitting, not drill or round."""
        clubs = ['Driver'] * 50
        result = self.classifier.classify(clubs)
        self.assertEqual(result.category, 'fitting')
        self.assertNotEqual(result.category, 'sim_round')

    def test_practice_iron_blocks(self):
        """Block practice: repeated iron work in blocks."""
        clubs = (
            ['7 Iron'] * 15 +
            ['8 Iron'] * 15 +
            ['9 Iron'] * 15
        )
        result = self.classifier.classify(clubs)
        self.assertEqual(result.category, 'practice')
        self.assertGreater(result.signals.get('repetition_ratio', 0), 0.5)

    def test_practice_mixed_no_sequence(self):
        """Mixed clubs but in block practice pattern — NOT a round."""
        clubs = (
            ['Driver'] * 10 +
            ['7 Iron'] * 10 +
            ['PW'] * 10 +
            ['SW'] * 10
        )
        result = self.classifier.classify(clubs)
        # High repetition ratio should prevent sim_round classification
        self.assertIn(result.category, ('practice',))

    # --- Drill detection ---

    def test_drill_single_club(self):
        """Single club with many shots = drill."""
        clubs = ['7 Iron'] * 40
        result = self.classifier.classify(clubs)
        self.assertEqual(result.category, 'drill')
        self.assertGreaterEqual(result.confidence, 0.8)

    def test_drill_two_clubs(self):
        """Two clubs with many shots = drill."""
        clubs = ['Driver'] * 20 + ['3 Wood'] * 20
        result = self.classifier.classify(clubs)
        self.assertEqual(result.category, 'drill')

    # --- Warmup detection ---

    def test_warmup_few_shots(self):
        """<10 shots should be warmup."""
        clubs = ['Driver', '7 Iron', 'PW']
        result = self.classifier.classify(clubs)
        self.assertEqual(result.category, 'warmup')
        self.assertGreaterEqual(result.confidence, 0.8)

    # --- Fitting detection ---

    def test_fitting_single_club_high_volume(self):
        """1 club with 50+ shots = fitting."""
        clubs = ['Driver'] * 60
        result = self.classifier.classify(clubs)
        self.assertEqual(result.category, 'fitting')

    # --- Empty/edge cases ---

    def test_empty_clubs(self):
        result = self.classifier.classify([])
        self.assertEqual(result.category, 'practice')
        self.assertEqual(result.confidence, 0.5)

    def test_classify_with_data_empty_df(self):
        result = self.classifier.classify_with_data(pd.DataFrame())
        self.assertEqual(result.category, 'practice')
        self.assertEqual(result.confidence, 0.5)


class TestClassificationResult(unittest.TestCase):
    """Tests for ClassificationResult dataclass."""

    def test_display_type_auto_set(self):
        result = ClassificationResult(category='sim_round', confidence=0.9)
        self.assertEqual(result.display_type, 'Sim Round')

    def test_display_type_practice(self):
        result = ClassificationResult(category='practice', confidence=0.8)
        self.assertEqual(result.display_type, 'Practice')

    def test_display_type_custom(self):
        result = ClassificationResult(category='sim_round', confidence=0.9, display_type='Custom')
        self.assertEqual(result.display_type, 'Custom')

    def test_signals_default_empty(self):
        result = ClassificationResult(category='practice', confidence=0.8)
        self.assertEqual(result.signals, {})


class TestShotSequenceAnalysis(unittest.TestCase):
    """Tests for the shot sequence analysis internals."""

    def setUp(self):
        self.classifier = SessionClassifier()

    def test_single_hole_pattern(self):
        """Driver -> Iron -> Wedge should detect 1 hole."""
        clubs = ['Driver', '7 Iron', 'PW']
        info = self.classifier._analyze_shot_sequence(clubs)
        self.assertEqual(info['hole_sequences'], 1)

    def test_two_hole_pattern(self):
        """Two consecutive hole-like patterns."""
        clubs = ['Driver', '7 Iron', 'PW', 'Driver', '5 Iron', 'SW']
        info = self.classifier._analyze_shot_sequence(clubs)
        self.assertEqual(info['hole_sequences'], 2)

    def test_no_hole_pattern_all_short(self):
        """All short clubs — no hole pattern."""
        clubs = ['PW', 'SW', 'GW', 'LW']
        info = self.classifier._analyze_shot_sequence(clubs)
        self.assertEqual(info['hole_sequences'], 0)

    def test_no_hole_pattern_same_club(self):
        """Same club repeated — no hole pattern."""
        clubs = ['Driver'] * 10
        info = self.classifier._analyze_shot_sequence(clubs)
        self.assertEqual(info['hole_sequences'], 0)

    def test_par3_pattern(self):
        """Mid iron -> wedge is a par-3 hole (no tee shot with long club)."""
        clubs = ['7 Iron', 'PW']
        info = self.classifier._analyze_shot_sequence(clubs)
        # No long club start, so this isn't detected as a hole
        self.assertEqual(info['hole_sequences'], 0)

    def test_transition_count(self):
        """Transitions from long to progressively shorter."""
        clubs = ['Driver', '5 Iron', '9 Iron', 'PW']
        info = self.classifier._analyze_shot_sequence(clubs)
        self.assertGreaterEqual(info['transition_count'], 2)

    def test_too_few_clubs(self):
        """Less than 3 clubs should return zeros."""
        info = self.classifier._analyze_shot_sequence(['Driver', 'PW'])
        self.assertEqual(info['hole_sequences'], 0)


class TestRepetitionRatio(unittest.TestCase):
    """Tests for repetition ratio computation."""

    def setUp(self):
        self.classifier = SessionClassifier()

    def test_no_repetition(self):
        """All different clubs — zero repetition."""
        clubs = ['Driver', '3 Wood', '5 Iron', '7 Iron', 'PW', 'SW']
        ratio = self.classifier._compute_repetition_ratio(clubs)
        self.assertEqual(ratio, 0.0)

    def test_full_repetition(self):
        """All same club — full repetition."""
        clubs = ['Driver'] * 10
        ratio = self.classifier._compute_repetition_ratio(clubs)
        self.assertEqual(ratio, 1.0)

    def test_partial_block(self):
        """Mix of blocks and variety."""
        clubs = ['Driver'] * 5 + ['7 Iron', 'PW', '3 Wood']
        ratio = self.classifier._compute_repetition_ratio(clubs)
        # 5 driver shots in a block of 5 (>=3) out of 8 total
        self.assertAlmostEqual(ratio, 5 / 8, places=2)

    def test_short_runs_not_counted(self):
        """Runs of 2 should NOT count as block practice."""
        clubs = ['Driver', 'Driver', '7 Iron', '7 Iron', 'PW', 'PW']
        ratio = self.classifier._compute_repetition_ratio(clubs)
        self.assertEqual(ratio, 0.0)

    def test_empty(self):
        ratio = self.classifier._compute_repetition_ratio([])
        self.assertEqual(ratio, 0.0)


class TestCategoryBreakdown(unittest.TestCase):
    """Tests for get_category_breakdown."""

    def setUp(self):
        self.classifier = SessionClassifier()

    def test_full_bag_breakdown(self):
        clubs = ['Driver', '3 Wood', '5 Iron', '7 Iron', '9 Iron', 'PW', 'SW']
        breakdown = self.classifier.get_category_breakdown(clubs)
        self.assertIn('Long Game', breakdown)
        self.assertIn('Mid Irons', breakdown)
        self.assertIn('Short Game', breakdown)

    def test_driver_only_breakdown(self):
        clubs = ['Driver'] * 5
        breakdown = self.classifier.get_category_breakdown(clubs)
        self.assertIn('Long Game', breakdown)
        self.assertEqual(breakdown['Long Game']['count'], 5)
        self.assertEqual(breakdown['Long Game']['pct'], 100.0)

    def test_empty_breakdown(self):
        self.assertEqual(self.classifier.get_category_breakdown([]), {})


# ============================================================================
# CLASSIFY_WITH_DATA TESTS (DataFrame-based)
# ============================================================================

class TestClassifyWithData(unittest.TestCase):
    """Tests for classify_with_data using DataFrames."""

    def setUp(self):
        self.classifier = SessionClassifier()

    def test_round_dataframe(self):
        """DataFrame with round-like club sequence and carry variance."""
        clubs = (
            ['Driver', '7 Iron', 'PW'] * 6 +
            ['3 Wood', '5 Iron', 'SW'] * 6 +
            ['8 Iron', 'GW'] * 3
        )
        carries = [250, 165, 120] * 6 + [230, 180, 90] * 6 + [140, 100] * 3
        df = pd.DataFrame({'club': clubs, 'carry': carries})
        result = self.classifier.classify_with_data(df)
        self.assertEqual(result.category, 'sim_round')

    def test_practice_dataframe(self):
        """DataFrame with practice-like repetitive pattern."""
        clubs = ['7 Iron'] * 30 + ['8 Iron'] * 20
        carries = [165] * 30 + [155] * 20
        df = pd.DataFrame({'club': clubs, 'carry': carries})
        result = self.classifier.classify_with_data(df)
        self.assertIn(result.category, ('drill', 'practice'))

    def test_missing_club_column(self):
        """DataFrame without club column should return practice/0.5."""
        df = pd.DataFrame({'carry': [100, 200, 300]})
        result = self.classifier.classify_with_data(df)
        self.assertEqual(result.category, 'practice')
        self.assertEqual(result.confidence, 0.5)

    def test_context_from_session_type(self):
        """If session_type column contains sim round hint, use it."""
        clubs = ['Driver'] * 5 + ['7 Iron'] * 5 + ['PW'] * 5
        df = pd.DataFrame({
            'club': clubs,
            'session_type': ['Sgt Rd1'] * 15,
        })
        result = self.classifier.classify_with_data(df)
        self.assertEqual(result.category, 'sim_round')


# ============================================================================
# SESSION NAMER INTEGRATION TESTS
# ============================================================================

class TestSessionNamerWithClassification(unittest.TestCase):
    """Tests for SessionNamer using sim round detection."""

    def setUp(self):
        self.namer = SessionNamer()

    def test_detect_sim_round_type(self):
        """Sim round should be detected via SessionClassifier."""
        clubs = (
            ['Driver', '7 Iron', 'PW'] * 5 +
            ['3 Wood', '5 Iron', 'SW'] * 5 +
            ['8 Iron', 'GW'] * 3
        )
        result = self.namer.detect_session_type(clubs)
        self.assertEqual(result, 'Sim Round')

    def test_detect_driver_focus_unchanged(self):
        """Driver focus sessions should still work."""
        clubs = ['Driver'] * 18 + ['7 Iron'] * 2
        result = self.namer.detect_session_type(clubs)
        self.assertEqual(result, 'Driver Focus')

    def test_detect_warmup_unchanged(self):
        clubs = ['Driver'] * 3
        result = self.namer.detect_session_type(clubs)
        self.assertEqual(result, 'Warmup')

    def test_context_hint_round(self):
        """Context hint should trigger sim round even with ambiguous clubs."""
        clubs = ['Driver'] * 8 + ['7 Iron'] * 4 + ['PW'] * 4
        result = self.namer.detect_session_type(clubs, context_hint='Sgt Rd1')
        self.assertEqual(result, 'Sim Round')

    def test_display_name_sim_round(self):
        """Display name should include 'Sim Round'."""
        clubs = (
            ['Driver', '7 Iron', 'PW'] * 5 +
            ['3 Wood', '5 Iron', 'SW'] * 5 +
            ['8 Iron', 'GW'] * 3
        )
        date = datetime(2026, 2, 10)
        name = self.namer.generate_display_name(date, clubs)
        self.assertIn('Sim Round', name)
        self.assertIn('2026-02-10', name)

    def test_display_name_mixed_practice_unchanged(self):
        """Mixed practice without round pattern should remain unchanged."""
        clubs = ['Driver'] * 5 + ['7 Iron'] * 5 + ['PW'] * 5
        date = datetime(2026, 2, 10)
        name = self.namer.generate_display_name(date, clubs)
        self.assertIn('Mixed Practice', name)


# ============================================================================
# AUTO TAGGER INTEGRATION TESTS
# ============================================================================

class TestAutoTaggerSimRound(unittest.TestCase):
    """Tests for AutoTagger sim round detection."""

    def setUp(self):
        self.tagger = AutoTagger()

    def test_sim_round_tag_with_sequence(self):
        """Round-like sequence passed via club_sequence kwarg."""
        clubs_unique = ['Driver', '3 Wood', '5 Iron', '6 Iron', '7 Iron',
                       '8 Iron', '9 Iron', 'PW', 'GW', 'SW']
        club_sequence = (
            ['Driver', '7 Iron', 'PW'] * 5 +
            ['3 Wood', '5 Iron', 'SW'] * 5 +
            ['8 Iron', 'GW'] * 3
        )
        tags = self.tagger.auto_tag(
            clubs_unique,
            shot_count=len(club_sequence),
            club_sequence=club_sequence,
        )
        self.assertIn('Sim Round', tags)

    def test_no_sim_round_tag_for_block_practice(self):
        """Block practice should NOT get Sim Round tag."""
        clubs = ['7 Iron', '8 Iron', '9 Iron']
        tags = self.tagger.auto_tag(clubs, 45)
        self.assertNotIn('Sim Round', tags)


# ============================================================================
# CONVENIENCE FUNCTION TESTS
# ============================================================================

class TestConvenienceFunctions(unittest.TestCase):
    """Tests for module-level convenience functions."""

    def test_classify_session(self):
        clubs = ['Driver', '7 Iron', 'PW'] * 10
        result = classify_session(clubs)
        self.assertIsInstance(result, ClassificationResult)
        self.assertIn(result.category, ('practice', 'sim_round', 'drill', 'warmup', 'fitting'))

    def test_classify_session_df(self):
        df = pd.DataFrame({
            'club': ['Driver'] * 5 + ['7 Iron'] * 5,
        })
        result = classify_session_df(df)
        self.assertIsInstance(result, ClassificationResult)

    def test_normalize_club_simulator_format(self):
        self.assertEqual(normalize_club("m7i"), "7 Iron")
        self.assertEqual(normalize_club("wood 3"), "3 Wood")
        self.assertEqual(normalize_club("drv"), "Driver")


if __name__ == "__main__":
    unittest.main()
