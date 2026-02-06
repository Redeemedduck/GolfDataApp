"""
Local AI Provider for GolfDataApp.

Provides template-based golf coaching without requiring cloud API calls.
Uses local ML models when available for enhanced predictions.
"""

from services.ai.registry import register_provider

# Import LocalCoach - handles its own dependency checks
from local_coach import LocalCoach


@register_provider
class LocalProvider:
    """Local AI provider using template-based responses and local ML models."""

    PROVIDER_ID = "local"
    DISPLAY_NAME = "Local AI (Offline)"

    def __init__(self, model_type: str = "default", thinking_level: str = "medium"):
        """
        Initialize the local provider.

        Args:
            model_type: Unused, for API compatibility
            thinking_level: Unused, for API compatibility
        """
        self._coach = LocalCoach()
        self._model_type = model_type
        self._thinking_level = thinking_level

    @staticmethod
    def is_configured() -> bool:
        """Local provider is always configured - no API keys needed."""
        return True

    def chat(self, message: str) -> dict:
        """
        Process a chat message and return a response.

        Args:
            message: User's question or request

        Returns:
            Dict with 'response' and 'function_calls' keys to match Gemini format
        """
        coach_response = self._coach.get_response(message)

        # Format response to include suggestions if available
        response_parts = [coach_response.message]
        if coach_response.suggestions:
            response_parts.append("\n**Suggestions:**")
            for suggestion in coach_response.suggestions:
                response_parts.append(f"- {suggestion}")

        return {
            'response': "\n".join(response_parts),
            'function_calls': [],  # Local coach doesn't use function calling
            'data': coach_response.data,  # Extra data for transparency
        }

    def reset_conversation(self):
        """Reset conversation state (no-op for local coach)."""
        # LocalCoach is stateless, so nothing to reset
        pass

    def set_model(self, model_type: str):
        """Set model type (no-op for local coach)."""
        self._model_type = model_type

    def set_thinking_level(self, level: str):
        """Set thinking level (no-op for local coach)."""
        self._thinking_level = level

    def get_model_name(self) -> str:
        """Return the model name."""
        if self._coach.ml_available:
            return "Local (ML-Enhanced)"
        return "Local (Rule-Based)"

    @property
    def ml_available(self) -> bool:
        """Check if ML models are available."""
        return self._coach.ml_available

    def get_capabilities(self) -> dict:
        """Return provider capabilities."""
        return {
            "requires_api_key": False,
            "works_offline": True,
            "ml_enhanced": self._coach.ml_available,
            "supported_intents": [
                "driver_stats", "iron_stats", "club_comparison",
                "session_analysis", "trend_analysis", "swing_issue",
                "consistency", "gapping", "profile"
            ]
        }
