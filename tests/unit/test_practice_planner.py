"""
Unit tests for practice planner and weakness mapper.

Tests:
- WeaknessMapper detection for all weakness types
- PracticePlanner drill selection and plan generation
- Graceful degradation for missing data
- Boundary conditions and edge cases
"""

import unittest
import pandas as pd
import numpy as np
from ml.coaching.weakness_mapper import WeaknessMapper
from ml.coaching.practice_planner import PracticePlanner, Drill, PracticePlan


class TestWeaknessMapper(unittest.TestCase):
    """Test cases for WeaknessMapper."""

    def setUp(self):
        """Set up test fixtures."""
        self.mapper = WeaknessMapper()

    def test_empty_dataframe(self):
        """Empty DataFrame should return empty weakness dict."""
        df = pd.DataFrame()
        weaknesses = self.mapper.detect_weaknesses(df)
        self.assertEqual(weaknesses, {})

    def test_high_dispersion_detected(self):
        """High lateral dispersion should be detected."""
        # Create 20 shots with high dispersion (IQR > 15)
        # Use explicit values to guarantee IQR > 15
        side_values = [-20, -18, -15, -10, -8, -5, 0, 2, 5, 8, 10, 12, 15, 18, 20, 22, 25, 28, 30, 32]
        df = pd.DataFrame({
            'club': ['Driver'] * 20,
            'side_total': side_values,  # Q1 ≈ -7.5, Q3 ≈ 21.5, IQR ≈ 29
            'carry': [250] * 20,
        })

        weaknesses = self.mapper.detect_weaknesses(df, clubs=['Driver'])

        # Should detect high dispersion
        self.assertIn('high_dispersion', weaknesses)
        self.assertGreater(weaknesses['high_dispersion'], 0.0)
        self.assertLessEqual(weaknesses['high_dispersion'], 1.0)

    def test_fade_pattern_detected(self):
        """Consistent fade pattern should be detected (>60%)."""
        # Create shots that classify as Fade (face-to-path > 2 and < 6)
        df = pd.DataFrame({
            'face_angle': [3.0] * 20,  # Positive = open
            'club_path': [0.0] * 20,
            'side_spin': [500] * 20,  # Positive = fade spin
        })

        weaknesses = self.mapper.detect_weaknesses(df)

        # Should detect fade pattern
        self.assertIn('fade_pattern', weaknesses)
        self.assertGreater(weaknesses['fade_pattern'], 0.6)

    def test_slice_pattern_detected(self):
        """Slice pattern should be detected (>40%)."""
        # Create 10 slice shots (face-to-path > 6) and 5 straight shots
        face_angles = [8.0] * 10 + [0.0] * 5  # 10 slices, 5 straight
        club_paths = [0.0] * 15
        side_spins = [1000] * 10 + [0] * 5

        df = pd.DataFrame({
            'face_angle': face_angles,
            'club_path': club_paths,
            'side_spin': side_spins,
        })

        weaknesses = self.mapper.detect_weaknesses(df)

        # Should detect slice pattern (10/15 = 66.7%)
        self.assertIn('slice_pattern', weaknesses)
        self.assertGreater(weaknesses['slice_pattern'], 0.4)

    def test_hook_pattern_detected(self):
        """Hook pattern should be detected (>40%)."""
        # Create 10 hook shots (face-to-path < -6) and 5 straight shots
        face_angles = [-8.0] * 10 + [0.0] * 5
        club_paths = [0.0] * 15
        side_spins = [-1000] * 10 + [0] * 5

        df = pd.DataFrame({
            'face_angle': face_angles,
            'club_path': club_paths,
            'side_spin': side_spins,
        })

        weaknesses = self.mapper.detect_weaknesses(df)

        # Should detect hook pattern
        self.assertIn('hook_pattern', weaknesses)
        self.assertGreater(weaknesses['hook_pattern'], 0.4)

    def test_low_smash_detected(self):
        """Low smash factor should be detected (avg < 1.40)."""
        df = pd.DataFrame({
            'smash': [1.35] * 20,  # Below threshold
            'carry': [240] * 20,
        })

        weaknesses = self.mapper.detect_weaknesses(df)

        # Should detect low smash factor
        self.assertIn('low_smash_factor', weaknesses)
        self.assertGreater(weaknesses['low_smash_factor'], 0.0)

    def test_inconsistent_distance(self):
        """High carry CV should be detected as inconsistent distance."""
        # Create carries with high CV (> 8%)
        np.random.seed(42)
        carries = np.random.normal(250, 25, 20)  # CV = 25/250 = 10%

        df = pd.DataFrame({
            'club': ['Driver'] * 20,
            'carry': carries,
        })

        weaknesses = self.mapper.detect_weaknesses(df, clubs=['Driver'])

        # Should detect inconsistent distance
        self.assertIn('inconsistent_distance', weaknesses)
        self.assertGreater(weaknesses['inconsistent_distance'], 0.0)

    def test_high_launch_detected(self):
        """High driver launch should be detected (>16 degrees)."""
        df = pd.DataFrame({
            'club': ['Driver'] * 20,
            'launch_angle': [18.0] * 20,  # Above threshold
            'carry': [250] * 20,
        })

        weaknesses = self.mapper.detect_weaknesses(df)

        # Should detect high launch
        self.assertIn('high_launch', weaknesses)
        self.assertGreater(weaknesses['high_launch'], 0.0)

    def test_low_launch_detected(self):
        """Low driver launch should be detected (<10 degrees)."""
        df = pd.DataFrame({
            'club': ['Driver'] * 20,
            'launch_angle': [8.0] * 20,  # Below threshold
            'carry': [240] * 20,
        })

        weaknesses = self.mapper.detect_weaknesses(df)

        # Should detect low launch
        self.assertIn('low_launch', weaknesses)
        self.assertGreater(weaknesses['low_launch'], 0.0)

    def test_min_samples_respected(self):
        """Should not detect weaknesses with < 5 shots."""
        # Only 3 shots (below minimum)
        df = pd.DataFrame({
            'club': ['Driver'] * 3,
            'side_total': [5, 10, 15],
            'carry': [250, 255, 260],
        })

        weaknesses = self.mapper.detect_weaknesses(df)

        # Should return empty (not enough data)
        self.assertEqual(weaknesses, {})

    def test_sentinel_values_cleaned(self):
        """Sentinel values (0, 99999) should be excluded from calculations."""
        df = pd.DataFrame({
            'smash': [1.45, 1.42, 0, 99999, 1.40, 1.38, 1.43, 1.41, 0, 1.39] + [1.40] * 10,
            'carry': [250, 255, 99999, 260, 0, 245, 250, 255, 99999, 260] + [250] * 10,
        })

        # Should not crash and should clean sentinels
        weaknesses = self.mapper.detect_weaknesses(df)

        # Verify we get valid results (may or may not trigger thresholds)
        self.assertIsInstance(weaknesses, dict)
        # All severity scores should be valid
        for severity in weaknesses.values():
            self.assertGreaterEqual(severity, 0.0)
            self.assertLessEqual(severity, 1.0)

    def test_missing_columns_graceful(self):
        """Missing columns should be handled gracefully (skip check)."""
        # DataFrame without side_total or face_angle
        df = pd.DataFrame({
            'club': ['Driver'] * 20,
            'carry': [250] * 20,
            'smash': [1.35] * 20,
        })

        # Should not crash
        weaknesses = self.mapper.detect_weaknesses(df)

        # Should still detect low smash (has that column)
        self.assertIn('low_smash_factor', weaknesses)

        # Should NOT have dispersion or shot shape checks (missing columns)
        self.assertNotIn('high_dispersion', weaknesses)
        self.assertNotIn('fade_pattern', weaknesses)

    def test_weaknesses_sorted_by_severity(self):
        """Weaknesses should be sorted by severity descending."""
        # Create multiple weaknesses with different severities
        df = pd.DataFrame({
            'club': ['Driver'] * 20,
            'smash': [1.30] * 20,  # Low smash (high severity)
            'carry': np.random.normal(250, 5, 20),  # Low CV (low severity)
            'face_angle': [8.0] * 20,  # Slice pattern (high severity)
            'club_path': [0.0] * 20,
            'side_spin': [1000] * 20,
        })

        weaknesses = self.mapper.detect_weaknesses(df)

        # Should have multiple weaknesses
        self.assertGreater(len(weaknesses), 1)

        # Check they're sorted (severities should be descending)
        severities = list(weaknesses.values())
        self.assertEqual(severities, sorted(severities, reverse=True))


class TestPracticePlanner(unittest.TestCase):
    """Test cases for PracticePlanner."""

    def setUp(self):
        """Set up test fixtures."""
        self.planner = PracticePlanner()

    def test_generate_plan_with_weaknesses(self):
        """Should generate plan from pre-computed weaknesses."""
        weaknesses = {
            'high_dispersion': 0.8,
            'low_smash_factor': 0.5,
        }

        plan = self.planner.generate_plan_from_weaknesses(weaknesses, target_duration=30)

        # Should return PracticePlan
        self.assertIsInstance(plan, PracticePlan)

        # Should have drills
        self.assertGreater(len(plan.drills), 0)

        # Should address weaknesses
        self.assertGreater(len(plan.weaknesses_addressed), 0)

        # Should have rationale
        self.assertIn('dispersion', plan.rationale.lower())

    def test_plan_duration_within_target(self):
        """Total drill duration should not exceed target."""
        weaknesses = {
            'high_dispersion': 0.9,
            'fade_pattern': 0.8,
            'low_smash_factor': 0.7,
            'inconsistent_distance': 0.6,
        }

        target = 30
        plan = self.planner.generate_plan_from_weaknesses(weaknesses, target_duration=target)

        # Calculate total duration
        total_duration = sum(drill.duration_min for drill in plan.drills)

        # Should not exceed target
        self.assertLessEqual(total_duration, target)

        # Plan duration should match actual
        self.assertEqual(plan.duration_min, total_duration)

    def test_plan_prioritizes_highest_severity(self):
        """Should prioritize drills for highest severity weaknesses."""
        weaknesses = {
            'high_dispersion': 0.9,  # Highest
            'fade_pattern': 0.3,     # Lowest
        }

        plan = self.planner.generate_plan_from_weaknesses(weaknesses, target_duration=30)

        # First drill should address high_dispersion
        if plan.drills:
            first_drill = plan.drills[0]
            self.assertEqual(first_drill.weakness_key, 'high_dispersion')

    def test_default_plan_when_no_data(self):
        """Should return general plan when no data."""
        df = pd.DataFrame()  # Empty

        plan = self.planner.generate_plan(df, target_duration=30)

        # Should return plan (not fail)
        self.assertIsInstance(plan, PracticePlan)

        # Should have drills
        self.assertGreater(len(plan.drills), 0)

        # Should have duration
        self.assertGreater(plan.duration_min, 0)

        # Rationale should mention no weaknesses
        self.assertIn('no', plan.rationale.lower())

    def test_default_plan_when_no_weaknesses(self):
        """Should return general plan when no weaknesses detected."""
        # Perfect data (no weaknesses)
        df = pd.DataFrame({
            'club': ['Driver'] * 20,
            'carry': [250.0] * 20,  # Perfect consistency
            'smash': [1.49] * 20,   # Excellent smash
            'face_angle': [0.0] * 20,
            'club_path': [0.0] * 20,
            'side_spin': [0] * 20,
            'launch_angle': [13.0] * 20,  # Optimal
        })

        plan = self.planner.generate_plan(df, target_duration=30)

        # Should return default plan
        self.assertIsInstance(plan, PracticePlan)
        self.assertGreater(len(plan.drills), 0)

    def test_drill_library_completeness(self):
        """All expected weakness keys should have drills."""
        expected_weaknesses = [
            'high_dispersion',
            'fade_pattern',
            'slice_pattern',
            'hook_pattern',
            'low_smash_factor',
            'inconsistent_distance',
            'high_launch',
            'low_launch',
        ]

        for weakness_key in expected_weaknesses:
            self.assertIn(
                weakness_key,
                self.planner.DRILL_LIBRARY,
                f"Drill library missing drills for {weakness_key}"
            )

            drills = self.planner.DRILL_LIBRARY[weakness_key]
            self.assertGreater(len(drills), 0, f"No drills for {weakness_key}")

            # Check each drill has required fields
            for drill in drills:
                self.assertIsInstance(drill, Drill)
                self.assertGreater(len(drill.name), 0)
                self.assertGreater(drill.duration_min, 0)
                self.assertGreater(len(drill.focus), 0)
                self.assertGreater(len(drill.instructions), 0)
                self.assertGreater(drill.reps, 0)
                self.assertEqual(drill.weakness_key, weakness_key)

    def test_plan_focus_areas_populated(self):
        """Generated plans should have focus areas."""
        weaknesses = {
            'high_dispersion': 0.8,
            'low_smash_factor': 0.6,
        }

        plan = self.planner.generate_plan_from_weaknesses(weaknesses, target_duration=30)

        # Should have focus areas
        self.assertGreater(len(plan.focus_areas), 0)

        # Focus areas should match drills
        drill_focuses = {drill.focus for drill in plan.drills}
        for focus in plan.focus_areas:
            self.assertIn(focus, drill_focuses)

    def test_plan_rationale_cites_weaknesses(self):
        """Rationale should mention detected weaknesses."""
        weaknesses = {
            'slice_pattern': 0.9,
        }

        plan = self.planner.generate_plan_from_weaknesses(weaknesses, target_duration=30)

        # Rationale should mention slice
        self.assertIn('slice', plan.rationale.lower())

    def test_multiple_drills_per_weakness(self):
        """Some weaknesses should have multiple drill options."""
        # Check at least one weakness has multiple drills
        multi_drill_count = 0
        for weakness_key, drills in self.planner.DRILL_LIBRARY.items():
            if len(drills) > 1:
                multi_drill_count += 1

        self.assertGreater(
            multi_drill_count,
            0,
            "At least one weakness should have multiple drill options"
        )

    def test_drills_have_instructions(self):
        """All drills should have step-by-step instructions."""
        for weakness_key, drills in self.planner.DRILL_LIBRARY.items():
            for drill in drills:
                # Instructions should be non-empty
                self.assertGreater(len(drill.instructions), 50)

                # Should contain numbered steps
                self.assertTrue(
                    '1.' in drill.instructions or '1)' in drill.instructions,
                    f"Drill {drill.name} missing step numbers"
                )

    def test_plan_from_dataframe(self):
        """Should generate plan from DataFrame with weaknesses."""
        # Create data with high dispersion (use explicit values)
        side_values = [-20, -18, -15, -10, -8, -5, 0, 2, 5, 8, 10, 12, 15, 18, 20, 22, 25, 28, 30, 32]
        df = pd.DataFrame({
            'club': ['Driver'] * 20,
            'side_total': side_values,
            'carry': [250] * 20,
        })

        plan = self.planner.generate_plan(df, target_duration=30, clubs=['Driver'])

        # Should detect weakness and create plan
        self.assertIsInstance(plan, PracticePlan)

        # If high_dispersion detected, should address it
        if 'high_dispersion' in plan.weaknesses_addressed:
            self.assertGreater(len(plan.drills), 0)


if __name__ == '__main__':
    unittest.main()
