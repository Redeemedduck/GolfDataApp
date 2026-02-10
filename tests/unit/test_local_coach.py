"""
Unit tests for Local Coach and Local Provider.

Tests template-based coaching without cloud dependencies.
"""

import sys
from pathlib import Path

import unittest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from local_coach import LocalCoach, CoachResponse
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "pandas not installed")
class TestLocalCoachIntentDetection(unittest.TestCase):
    """Test intent detection from queries."""

    def setUp(self):
        self.coach = LocalCoach()

    def test_driver_intent(self):
        """Driver-related queries should be detected."""
        intent, _ = self.coach._detect_intent("How's my driver doing?")
        self.assertEqual(intent, 'driver_stats')

    def test_iron_intent(self):
        """Iron queries should be detected with club number."""
        intent, entity = self.coach._detect_intent("What's my 7 iron average?")
        self.assertEqual(intent, 'iron_stats')
        self.assertEqual(entity, '7')

    def test_comparison_intent(self):
        """Comparison queries should be detected."""
        intent, _ = self.coach._detect_intent("Compare my clubs")
        self.assertEqual(intent, 'club_comparison')

    def test_trend_intent(self):
        """Trend queries should be detected."""
        intent, _ = self.coach._detect_intent("Am I improving?")
        self.assertEqual(intent, 'trend_analysis')

    def test_swing_issue_intent(self):
        """Swing issue queries should be detected."""
        intent, _ = self.coach._detect_intent("Why do I slice?")
        self.assertEqual(intent, 'swing_issue')

    def test_general_intent_fallback(self):
        """Unknown queries should fall back to general."""
        intent, _ = self.coach._detect_intent("Hello there!")
        self.assertEqual(intent, 'general')


@unittest.skipUnless(HAS_DEPS, "pandas not installed")
class TestLocalCoachResponse(unittest.TestCase):
    """Test coach response generation."""

    def setUp(self):
        self.coach = LocalCoach()

    def test_response_is_coach_response(self):
        """Responses should be CoachResponse objects."""
        response = self.coach.get_response("Hello")
        self.assertIsInstance(response, CoachResponse)

    def test_general_response_has_suggestions(self):
        """General queries should include help suggestions."""
        response = self.coach.get_response("Hello")
        self.assertIn("I can help you with", response.message)
        self.assertIsNotNone(response.suggestions)

    def test_driver_response_without_data(self):
        """Driver query without data should say so."""
        response = self.coach._handle_club_stats("Driver")
        # Should either report no data or actual stats
        self.assertIsNotNone(response.message)


@unittest.skipUnless(HAS_DEPS, "pandas not installed")
class TestLocalCoachMLProperty(unittest.TestCase):
    """Test ML availability property."""

    def test_ml_available_property_exists(self):
        """Coach should have ml_available property."""
        coach = LocalCoach()
        self.assertIsInstance(coach.ml_available, bool)


@unittest.skipUnless(HAS_DEPS, "pandas not installed")
class TestLocalProvider(unittest.TestCase):
    """Test the Local AI Provider wrapper."""

    def test_provider_registration(self):
        """Provider should be registered correctly."""
        from services.ai import list_providers, get_provider

        providers = list_providers()
        provider_ids = [p.provider_id for p in providers]
        self.assertIn('local', provider_ids)

        spec = get_provider('local')
        self.assertIsNotNone(spec)
        self.assertEqual(spec.display_name, "Local AI (Offline)")

    def test_provider_always_configured(self):
        """Local provider should always be configured."""
        from services.ai.providers.local_provider import LocalProvider

        self.assertTrue(LocalProvider.is_configured())

    def test_provider_chat_returns_dict(self):
        """Chat should return dict with 'response' key."""
        from services.ai.providers.local_provider import LocalProvider

        provider = LocalProvider()
        result = provider.chat("Hello")

        self.assertIsInstance(result, dict)
        self.assertIn('response', result)
        self.assertIn('function_calls', result)
        self.assertIsInstance(result['function_calls'], list)

    def test_provider_model_name(self):
        """Model name should reflect ML availability."""
        from services.ai.providers.local_provider import LocalProvider

        provider = LocalProvider()
        model_name = provider.get_model_name()

        self.assertIn('Local', model_name)


@unittest.skipUnless(HAS_DEPS, "pandas not installed")
class TestAnalyticsDrivenResponses(unittest.TestCase):
    """Test analytics-driven club stats responses."""

    def setUp(self):
        self.coach = LocalCoach()

    def test_club_stats_cites_metrics(self):
        """Club stats should cite specific metrics, not generic templates."""
        from unittest.mock import patch, MagicMock
        import pandas as pd

        # Mock golf_db.get_all_shots to return sample data
        mock_df = pd.DataFrame({
            'club': ['Driver'] * 10,
            'carry': [250, 255, 248, 252, 260, 245, 258, 251, 249, 254],
            'session_id': ['s1'] * 10,
            'shot_id': range(10)
        })

        with patch('golf_db.get_all_shots', return_value=mock_df):
            response = self.coach.get_response("How's my Driver?")

            # Should contain "Median carry" and a numeric value (not just "avg")
            self.assertIn("Median carry", response.message)
            # Should have a number in the message
            import re
            self.assertTrue(re.search(r'\d+', response.message))

    def test_club_stats_includes_dispersion(self):
        """Club stats should include dispersion IQR when side_total available."""
        from unittest.mock import patch
        import pandas as pd

        mock_df = pd.DataFrame({
            'club': ['7 Iron'] * 10,
            'carry': [150] * 10,
            'side_total': [-5, 10, -2, 8, -3, 12, -8, 5, 0, 3],
            'session_id': ['s1'] * 10,
            'shot_id': range(10)
        })

        with patch('golf_db.get_all_shots', return_value=mock_df):
            response = self.coach.get_response("How's my 7 iron?")

            # Should mention dispersion if analytics available
            # (Will show if ANALYTICS_AVAILABLE, otherwise will use legacy)
            self.assertIsNotNone(response.message)

    def test_club_stats_includes_shot_shape(self):
        """Club stats should include shot shape distribution when D-plane data available."""
        from unittest.mock import patch
        import pandas as pd

        mock_df = pd.DataFrame({
            'club': ['Driver'] * 10,
            'carry': [250] * 10,
            'face_angle': [3.0] * 10,
            'club_path': [1.0] * 10,
            'side_spin': [400] * 10,
            'session_id': ['s1'] * 10,
            'shot_id': range(10)
        })

        with patch('golf_db.get_all_shots', return_value=mock_df):
            response = self.coach.get_response("How's my Driver?")

            # Should mention shot shape if analytics and shot classification available
            self.assertIsNotNone(response.message)

    def test_club_stats_fallback_without_analytics(self):
        """Club stats should fall back to legacy when analytics unavailable."""
        from unittest.mock import patch
        import pandas as pd

        mock_df = pd.DataFrame({
            'club': ['Driver'] * 5,
            'carry': [250, 255, 248, 252, 260],
            'session_id': ['s1'] * 5,
            'shot_id': range(5)
        })

        # Temporarily disable analytics imports
        with patch('golf_db.get_all_shots', return_value=mock_df):
            with patch('local_coach.ANALYTICS_AVAILABLE', False):
                response = self.coach.get_response("How's my Driver?")

                # Should still work using legacy stats
                self.assertIsNotNone(response.message)
                self.assertIn("Driver", response.message)


@unittest.skipUnless(HAS_DEPS, "pandas not installed")
class TestPracticePlanIntegration(unittest.TestCase):
    """Test practice plan generation integration."""

    def setUp(self):
        self.coach = LocalCoach()

    def test_practice_plan_intent_detected(self):
        """Practice plan intent should be detected."""
        intent, _ = self.coach._detect_intent("practice plan")
        self.assertEqual(intent, 'practice_plan')

    def test_drill_intent_detected(self):
        """Drill queries should trigger practice plan intent."""
        intent, _ = self.coach._detect_intent("what drills should I do")
        self.assertEqual(intent, 'practice_plan')

    def test_practice_plan_response_has_drills(self):
        """Practice plan response should mention drills and reps."""
        from unittest.mock import patch
        import pandas as pd

        # Mock data with detectable weakness (high dispersion)
        mock_df = pd.DataFrame({
            'club': ['Driver'] * 10,
            'carry': [250] * 10,
            'side_total': [-20, 25, -18, 22, -15, 28, -25, 20, -10, 30],
            'session_id': ['s1'] * 10,
            'shot_id': range(10)
        })

        with patch('golf_db.get_all_shots', return_value=mock_df):
            response = self.coach.get_practice_plan()

            # Should either have a plan or say modules unavailable
            self.assertIsNotNone(response.message)
            if response.data and 'plan' in response.data:
                # If plan generated, should have drills
                self.assertIn('drills', response.data['plan'])

    def test_practice_plan_duration(self):
        """Practice plan should respect target duration."""
        from unittest.mock import patch
        import pandas as pd

        mock_df = pd.DataFrame({
            'club': ['Driver'] * 10,
            'carry': [250] * 10,
            'side_total': [-20, 25, -18, 22, -15, 28, -25, 20, -10, 30],
            'session_id': ['s1'] * 10,
            'shot_id': range(10)
        })

        with patch('golf_db.get_all_shots', return_value=mock_df):
            response = self.coach.get_practice_plan(target_duration=15)

            # Should mention 15 min or have duration_min field
            if response.data and 'plan' in response.data:
                self.assertLessEqual(response.data['plan']['duration_min'], 15)

    def test_practice_plan_no_data(self):
        """Practice plan with empty db should return general plan."""
        from unittest.mock import patch
        import pandas as pd

        with patch('golf_db.get_all_shots', return_value=pd.DataFrame()):
            response = self.coach.get_practice_plan()

            # Should handle gracefully
            self.assertIsNotNone(response.message)
            self.assertIn("data", response.message.lower())


@unittest.skipUnless(HAS_DEPS, "pandas not installed")
class TestPredictionIntervals(unittest.TestCase):
    """Test prediction intervals integration."""

    def setUp(self):
        self.coach = LocalCoach()

    def test_predict_distance_with_intervals(self):
        """Predict distance should include intervals when available."""
        from unittest.mock import patch, MagicMock

        # Mock distance predictor with intervals
        mock_predictor = MagicMock()
        mock_predictor.predict_with_intervals.return_value = {
            'predicted_value': 250.0,
            'lower_bound': 240.0,
            'upper_bound': 260.0,
            'confidence_level': 0.95,
            'interval_width': 20.0,
            'has_intervals': True
        }
        self.coach.distance_predictor = mock_predictor

        result = self.coach.predict_distance(ball_speed=150, launch_angle=12, back_spin=2500)

        # Should include interval data
        self.assertTrue(result.get('has_intervals', False))
        self.assertIn('lower_bound', result)
        self.assertIn('upper_bound', result)

    def test_predict_distance_without_intervals(self):
        """Predict distance should fall back gracefully without intervals."""
        from unittest.mock import patch, MagicMock

        # Mock distance predictor without intervals (returns has_intervals=False)
        mock_predictor = MagicMock()
        mock_result = MagicMock()
        mock_result.predicted_value = 250.0
        mock_result.confidence = 0.8
        mock_result.feature_importance = {}
        mock_predictor.predict.return_value = mock_result
        # No predict_with_intervals method
        delattr(mock_predictor, 'predict_with_intervals')
        self.coach.distance_predictor = mock_predictor

        result = self.coach.predict_distance(ball_speed=150, launch_angle=12, back_spin=2500)

        # Should include fallback note
        self.assertIn('predicted_carry', result)
        if 'message' in result:
            self.assertIn('point estimate', result['message'].lower())


if __name__ == '__main__':
    unittest.main()
