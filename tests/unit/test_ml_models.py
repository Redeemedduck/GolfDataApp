"""
Unit tests for ML models.

Tests the ML module including:
- Distance prediction
- Shot shape classification
- Swing flaw detection
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import numpy as np
    import pandas as pd
    from ml.classifiers import (
        ShotShapeClassifier,
        ShotShape,
        classify_shot_shape,
        ClassificationResult,
    )
    from ml.anomaly_detection import (
        SwingFlawDetector,
        SwingFlaw,
        detect_swing_flaws,
        compute_swing_metrics,
        FlawDetectionResult,
    )
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "numpy/sklearn not installed")
class TestShotShapeClassification(unittest.TestCase):
    """Test shot shape classification."""

    def test_straight_shot(self):
        """Shot with minimal face-to-path should be straight."""
        result = classify_shot_shape(
            face_angle=0.5,
            club_path=0.5,
            side_spin=50,
        )
        self.assertEqual(result.shape, ShotShape.STRAIGHT)
        self.assertGreater(result.confidence, 0.5)

    def test_draw_shot(self):
        """Closed face relative to path should be a draw."""
        result = classify_shot_shape(
            face_angle=-2.0,
            club_path=1.0,  # Face closed to path
        )
        self.assertEqual(result.shape, ShotShape.DRAW)

    def test_fade_shot(self):
        """Open face relative to path should be a fade."""
        result = classify_shot_shape(
            face_angle=2.0,
            club_path=-1.0,  # Face open to path
        )
        self.assertEqual(result.shape, ShotShape.FADE)

    def test_hook_severe_draw(self):
        """Severely closed face should be a hook."""
        result = classify_shot_shape(
            face_angle=-8.0,
            club_path=2.0,  # Very closed to path
        )
        self.assertEqual(result.shape, ShotShape.HOOK)

    def test_slice_severe_fade(self):
        """Severely open face should be a slice."""
        result = classify_shot_shape(
            face_angle=8.0,
            club_path=-2.0,  # Very open to path
        )
        self.assertEqual(result.shape, ShotShape.SLICE)

    def test_pull_shot(self):
        """Straight shot left of target."""
        result = classify_shot_shape(
            face_angle=-3.0,
            club_path=-3.0,  # Face and path aligned, but left
        )
        self.assertEqual(result.shape, ShotShape.PULL)

    def test_push_shot(self):
        """Straight shot right of target."""
        result = classify_shot_shape(
            face_angle=3.0,
            club_path=3.0,  # Face and path aligned, but right
        )
        self.assertEqual(result.shape, ShotShape.PUSH)

    def test_unknown_with_no_data(self):
        """No data should return unknown."""
        result = classify_shot_shape()
        self.assertEqual(result.shape, ShotShape.UNKNOWN)
        self.assertEqual(result.confidence, 0.0)

    def test_side_spin_only(self):
        """Classification from side spin only."""
        # Left spin = draw
        result = classify_shot_shape(side_spin=-1000)
        self.assertEqual(result.shape, ShotShape.DRAW)

        # Right spin = fade
        result = classify_shot_shape(side_spin=1000)
        self.assertEqual(result.shape, ShotShape.FADE)


@unittest.skipUnless(HAS_DEPS, "numpy/sklearn not installed")
class TestShotShapeClassifier(unittest.TestCase):
    """Test the ShotShapeClassifier class."""

    def setUp(self):
        self.classifier = ShotShapeClassifier()

    def test_rule_based_classification(self):
        """Classifier should work without training."""
        result = self.classifier.classify(
            face_angle=-2.0,
            club_path=1.0,
        )
        self.assertEqual(result.shape, ShotShape.DRAW)

    def test_batch_classification(self):
        """Batch classification should work."""
        df = pd.DataFrame({
            'face_angle': [0.0, -3.0, 3.0],
            'club_path': [0.0, 0.0, 0.0],
        })
        shapes = self.classifier.classify_batch(df)

        self.assertEqual(len(shapes), 3)
        self.assertEqual(shapes.iloc[0], 'straight')


@unittest.skipUnless(HAS_DEPS, "numpy/sklearn not installed")
class TestSwingFlawDetection(unittest.TestCase):
    """Test swing flaw detection."""

    def test_good_swing_no_flaws(self):
        """A good swing should have no flaws."""
        result = detect_swing_flaws(
            ball_speed=165,
            club_speed=110,
            attack_angle=-1.0,
            club_path=0.0,
            face_angle=0.0,
            impact_x=0.0,
            impact_y=0.0,
        )
        self.assertEqual(result.flaws, [SwingFlaw.NONE])
        self.assertFalse(result.is_outlier)
        self.assertLess(result.anomaly_score, 0.3)

    def test_over_the_top_detection(self):
        """Steep out-to-in path should be detected."""
        result = detect_swing_flaws(
            club_path=-8.0,  # Severe out-to-in
        )
        self.assertIn(SwingFlaw.OVER_THE_TOP, result.flaws)

    def test_early_release_detection(self):
        """Low smash factor should indicate early release."""
        result = detect_swing_flaws(
            ball_speed=130,
            club_speed=100,  # Smash = 1.30 (low)
        )
        self.assertIn(SwingFlaw.EARLY_RELEASE, result.flaws)

    def test_inconsistent_contact(self):
        """Off-center impact should be detected."""
        result = detect_swing_flaws(
            impact_x=20.0,  # 20mm off center
            impact_y=15.0,
        )
        self.assertIn(SwingFlaw.INCONSISTENT_CONTACT, result.flaws)

    def test_steep_attack_angle(self):
        """Very negative attack angle should be detected."""
        result = detect_swing_flaws(
            attack_angle=-7.0,  # Very steep
        )
        self.assertIn(SwingFlaw.STEEP_ATTACK, result.flaws)

    def test_shallow_attack_angle(self):
        """Very positive attack angle should be detected."""
        result = detect_swing_flaws(
            attack_angle=10.0,  # Very shallow/upward
        )
        self.assertIn(SwingFlaw.SHALLOW_ATTACK, result.flaws)

    def test_clubface_control(self):
        """Severely open or closed face should be detected."""
        result = detect_swing_flaws(
            face_angle=8.0,  # Very open
        )
        self.assertIn(SwingFlaw.CLUBFACE_CONTROL, result.flaws)


@unittest.skipUnless(HAS_DEPS, "numpy/sklearn not installed")
class TestSwingMetrics(unittest.TestCase):
    """Test swing metrics computation."""

    def test_smash_factor_calculation(self):
        """Smash factor should be ball_speed / club_speed."""
        metrics = compute_swing_metrics(
            ball_speed=165,
            club_speed=110,
        )
        self.assertAlmostEqual(metrics.smash_factor, 1.5, places=2)

    def test_face_to_path(self):
        """Face-to-path should be face_angle - club_path."""
        metrics = compute_swing_metrics(
            ball_speed=165,
            club_speed=110,
            face_angle=-2.0,
            club_path=1.0,
        )
        self.assertAlmostEqual(metrics.face_to_path, -3.0, places=1)

    def test_impact_consistency(self):
        """Impact consistency should be distance from center."""
        metrics = compute_swing_metrics(
            ball_speed=165,
            club_speed=110,
            impact_x=3.0,
            impact_y=4.0,  # 3-4-5 triangle
        )
        self.assertAlmostEqual(metrics.impact_consistency, 5.0, places=1)


@unittest.skipUnless(HAS_DEPS, "numpy/sklearn not installed")
class TestSwingFlawDetector(unittest.TestCase):
    """Test SwingFlawDetector class."""

    def setUp(self):
        self.detector = SwingFlawDetector()

    def test_unfitted_uses_rules(self):
        """Unfitted detector should use rule-based detection."""
        self.assertFalse(self.detector.is_fitted())

        result = self.detector.detect(
            club_path=-8.0,
        )
        self.assertIn(SwingFlaw.OVER_THE_TOP, result.flaws)

    def test_session_analysis(self):
        """Session analysis should work."""
        # Create sample session data
        df = pd.DataFrame({
            'ball_speed': [165, 160, 155, 145],
            'club_speed': [110, 108, 105, 100],
            'attack_angle': [-1.0, -2.0, -3.0, -8.0],  # Last one is steep
            'club_path': [0.0, -1.0, -2.0, -10.0],  # Last one is OTT
            'face_angle': [0.0, 0.5, -0.5, -2.0],
        })

        analysis = self.detector.analyze_session(df)

        self.assertEqual(analysis['total_shots'], 4)
        self.assertIn('outlier_count', analysis)
        self.assertIn('flaw_counts', analysis)
        self.assertIn('recommendations', analysis)


class TestMLImportFallback(unittest.TestCase):
    """Test ML import failure scenarios and graceful degradation."""

    def test_ml_available_flag_exists(self):
        """Verify ML_AVAILABLE flag is accessible."""
        import ml
        self.assertIsInstance(ml.ML_AVAILABLE, bool)

    def test_ml_missing_deps_is_list(self):
        """Verify ML_MISSING_DEPS is a list."""
        import ml
        self.assertIsInstance(ml.ML_MISSING_DEPS, list)

    @unittest.skipIf(HAS_DEPS, "ML dependencies are installed, testing unavailable scenario")
    def test_ml_unavailable_when_deps_missing(self):
        """When dependencies are missing, ML_AVAILABLE should be False."""
        import ml
        self.assertFalse(ml.ML_AVAILABLE)
        self.assertGreater(len(ml.ML_MISSING_DEPS), 0)

    def test_ml_exports_none_when_unavailable(self):
        """When ML unavailable, exported classes should be None."""
        import ml
        if not ml.ML_AVAILABLE:
            # At least one of these should be None
            exports = [
                ml.DistancePredictor,
                ml.ShotShapeClassifier,
                ml.SwingFlawDetector,
            ]
            self.assertTrue(
                any(exp is None for exp in exports),
                "When ML_AVAILABLE is False, at least one export should be None"
            )


if __name__ == '__main__':
    unittest.main()
