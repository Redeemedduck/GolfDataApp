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


if __name__ == '__main__':
    unittest.main()
