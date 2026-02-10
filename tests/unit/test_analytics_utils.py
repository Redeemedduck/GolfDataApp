"""
Unit tests for analytics utility functions.

Tests for IQR outlier filtering, normalization, sample checks, and distance statistics.
"""
import unittest
import pandas as pd
import numpy as np
from analytics.utils import (
    filter_outliers_iqr,
    check_min_samples,
    normalize_score,
    normalize_inverse,
    calculate_distance_stats
)


class TestFilterOutliersIQR(unittest.TestCase):
    """Tests for IQR outlier filtering."""

    def test_filters_outliers(self):
        """Test that known outliers are removed."""
        # Create data with clear outliers
        data = {
            'carry': [200, 202, 198, 201, 199, 203, 197, 250, 150, 200]  # 250 and 150 are outliers
        }
        df = pd.DataFrame(data)

        filtered = filter_outliers_iqr(df, 'carry')

        # Should remove outliers
        self.assertLess(len(filtered), len(df))
        # Extreme values should be gone
        self.assertNotIn(250, filtered['carry'].values)
        self.assertNotIn(150, filtered['carry'].values)

    def test_empty_dataframe(self):
        """Test that empty DataFrame returns empty."""
        df = pd.DataFrame({'carry': []})
        filtered = filter_outliers_iqr(df, 'carry')
        self.assertTrue(filtered.empty)

    def test_all_nan_column(self):
        """Test that column of all NaN returns original DataFrame."""
        df = pd.DataFrame({'carry': [np.nan, np.nan, np.nan]})
        filtered = filter_outliers_iqr(df, 'carry')
        # Should return unfiltered (can't calculate IQR)
        self.assertEqual(len(filtered), len(df))

    def test_small_sample(self):
        """Test that fewer than 3 values returns unfiltered."""
        df = pd.DataFrame({'carry': [200, 210]})
        filtered = filter_outliers_iqr(df, 'carry')
        # Should return unfiltered (need 3+ for IQR)
        self.assertEqual(len(filtered), 2)

    def test_custom_multiplier(self):
        """Test that higher multiplier keeps more data."""
        data = {'carry': [200, 202, 198, 201, 199, 203, 197, 250, 150, 200]}
        df = pd.DataFrame(data)

        filtered_1_5 = filter_outliers_iqr(df, 'carry', multiplier=1.5)
        filtered_3_0 = filter_outliers_iqr(df, 'carry', multiplier=3.0)

        # Higher multiplier should keep more data
        self.assertLessEqual(len(filtered_1_5), len(filtered_3_0))


class TestCheckMinSamples(unittest.TestCase):
    """Tests for minimum sample validation."""

    def test_sufficient_samples(self):
        """Test that sufficient samples return True."""
        data = list(range(10))
        sufficient, msg = check_min_samples(data, min_n=3)
        self.assertTrue(sufficient)
        self.assertEqual(msg, "")

    def test_insufficient_samples(self):
        """Test that insufficient samples return False with message."""
        data = [1, 2]
        sufficient, msg = check_min_samples(data, min_n=3)
        self.assertFalse(sufficient)
        self.assertIn("Need 3+", msg)
        self.assertIn("have 2", msg)

    def test_custom_min_n(self):
        """Test with custom minimum n."""
        data = [1, 2, 3, 4]
        sufficient, msg = check_min_samples(data, min_n=5)
        self.assertFalse(sufficient)
        self.assertIn("Need 5+", msg)

    def test_context_in_message(self):
        """Test that context is included in message."""
        data = [1, 2]
        sufficient, msg = check_min_samples(data, min_n=3, context="Driver")
        self.assertFalse(sufficient)
        self.assertIn("Driver", msg)

    def test_dataframe_input(self):
        """Test with DataFrame input."""
        df = pd.DataFrame({'carry': [200, 210, 205, 208, 202]})
        sufficient, msg = check_min_samples(df, min_n=3)
        self.assertTrue(sufficient)


class TestNormalizeScore(unittest.TestCase):
    """Tests for score normalization."""

    def test_normal_value(self):
        """Test that mid-range value normalizes correctly."""
        score = normalize_score(50, 0, 100)
        self.assertAlmostEqual(score, 50.0, places=1)

    def test_below_min(self):
        """Test that value below min is clamped to 0."""
        score = normalize_score(-10, 0, 100)
        self.assertEqual(score, 0.0)

    def test_above_max(self):
        """Test that value above max is clamped to 100."""
        score = normalize_score(150, 0, 100)
        self.assertEqual(score, 100.0)

    def test_equal_min_max(self):
        """Test that equal min/max returns 50."""
        score = normalize_score(75, 75, 75)
        self.assertEqual(score, 50.0)

    def test_quarter_point(self):
        """Test that 25% point normalizes to 25."""
        score = normalize_score(25, 0, 100)
        self.assertAlmostEqual(score, 25.0, places=1)


class TestNormalizeInverse(unittest.TestCase):
    """Tests for inverse normalization."""

    def test_low_value_scores_high(self):
        """Test that lowest value gets highest score."""
        score = normalize_inverse(0.5, 0.5, 5.0)
        self.assertAlmostEqual(score, 100.0, places=1)

    def test_high_value_scores_low(self):
        """Test that highest value gets lowest score."""
        score = normalize_inverse(5.0, 0.5, 5.0)
        self.assertAlmostEqual(score, 0.0, places=1)

    def test_mid_value(self):
        """Test that mid-range value normalizes inversely."""
        score = normalize_inverse(2.75, 0.5, 5.0)
        self.assertAlmostEqual(score, 50.0, places=1)

    def test_below_min_clamped(self):
        """Test that value below min is clamped."""
        score = normalize_inverse(0.1, 0.5, 5.0)
        self.assertEqual(score, 100.0)


class TestCalculateDistanceStats(unittest.TestCase):
    """Tests for distance statistics calculation."""

    def test_basic_stats(self):
        """Test that basic statistics are calculated correctly."""
        data = {
            'club': ['Driver'] * 10,
            'carry': [250, 252, 248, 251, 249, 253, 247, 250, 252, 251]
        }
        df = pd.DataFrame(data)

        stats = calculate_distance_stats(df, 'Driver')

        self.assertIsNotNone(stats)
        self.assertAlmostEqual(stats['median'], 250.5, places=0)
        self.assertIn('q25', stats)
        self.assertIn('q75', stats)
        self.assertIn('iqr', stats)
        self.assertIn('max', stats)
        self.assertEqual(stats['sample_size'], 10)
        self.assertEqual(stats['confidence'], 'high')

    def test_insufficient_data(self):
        """Test that insufficient data returns None."""
        data = {
            'club': ['Driver', 'Driver'],
            'carry': [250, 252]
        }
        df = pd.DataFrame(data)

        stats = calculate_distance_stats(df, 'Driver')

        self.assertIsNone(stats)

    def test_confidence_levels(self):
        """Test that confidence levels are assigned correctly."""
        # Low confidence (3-4 shots)
        df_low = pd.DataFrame({
            'club': ['Driver'] * 3,
            'carry': [250, 252, 248]
        })
        stats_low = calculate_distance_stats(df_low, 'Driver')
        self.assertEqual(stats_low['confidence'], 'low')

        # Medium confidence (5-9 shots)
        df_medium = pd.DataFrame({
            'club': ['Driver'] * 7,
            'carry': [250, 252, 248, 251, 249, 253, 247]
        })
        stats_medium = calculate_distance_stats(df_medium, 'Driver')
        self.assertEqual(stats_medium['confidence'], 'medium')

        # High confidence (10+ shots)
        df_high = pd.DataFrame({
            'club': ['Driver'] * 15,
            'carry': [250, 252, 248, 251, 249, 253, 247, 250, 252, 251,
                     249, 248, 250, 251, 252]
        })
        stats_high = calculate_distance_stats(df_high, 'Driver')
        self.assertEqual(stats_high['confidence'], 'high')

    def test_outliers_removed(self):
        """Test that outliers are tracked."""
        data = {
            'club': ['Driver'] * 10,
            'carry': [250, 252, 248, 251, 249, 253, 247, 300, 150, 250]  # 300 and 150 are outliers
        }
        df = pd.DataFrame(data)

        stats = calculate_distance_stats(df, 'Driver')

        self.assertIsNotNone(stats)
        # Should track that outliers were removed
        self.assertGreater(stats['outliers_removed'], 0)

    def test_total_distance_stats(self):
        """Test that total distance stats are calculated when available."""
        data = {
            'club': ['Driver'] * 10,
            'carry': [250, 252, 248, 251, 249, 253, 247, 250, 252, 251],
            'total': [260, 262, 258, 261, 259, 263, 257, 260, 262, 261]
        }
        df = pd.DataFrame(data)

        stats = calculate_distance_stats(df, 'Driver')

        self.assertIsNotNone(stats)
        self.assertIn('total_median', stats)
        self.assertIn('total_q25', stats)
        self.assertIn('total_q75', stats)
        self.assertGreater(stats['total_median'], stats['median'])

    def test_club_filtering(self):
        """Test that only specified club is analyzed."""
        data = {
            'club': ['Driver'] * 5 + ['7 Iron'] * 5,
            'carry': [250, 252, 248, 251, 249, 150, 152, 148, 151, 149]
        }
        df = pd.DataFrame(data)

        driver_stats = calculate_distance_stats(df, 'Driver')
        iron_stats = calculate_distance_stats(df, '7 Iron')

        self.assertIsNotNone(driver_stats)
        self.assertIsNotNone(iron_stats)
        # Driver median should be much higher than 7 Iron
        self.assertGreater(driver_stats['median'], iron_stats['median'])


if __name__ == '__main__':
    unittest.main()
