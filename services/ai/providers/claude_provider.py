"""Claude AI Coach Provider for GolfDataApp.

Provides golf coaching via the Claude Agent SDK,
using the same tool-equipped agent as the CLI.
"""
from __future__ import annotations

import os
import asyncio
import concurrent.futures
from services.ai.registry import register_provider


@register_provider
class ClaudeProvider:
    """Claude-powered AI golf coach using the Agent SDK."""

    PROVIDER_ID = "claude"
    DISPLAY_NAME = "Claude Golf Coach"

    def __init__(self, model_type: str = "sonnet", thinking_level: str = "medium"):
        self._model_type = model_type
        self._thinking_level = thinking_level

    @staticmethod
    def is_configured() -> bool:
        """Check if ANTHROPIC_API_KEY is available."""
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    def chat(self, message: str) -> dict:
        """Process a chat message using the golf agent.

        Args:
            message: User's question or request

        Returns:
            Dict with 'response' and 'function_calls' keys (matching Gemini format)
        """
        from agent.core import single_query

        try:
            # Run in a thread to avoid crashing inside Streamlit's event loop
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, single_query(message))
                response = future.result(timeout=120)
        except Exception as e:
            response = f"Error communicating with Claude: {e}"

        return {
            "response": response,
            "function_calls": [],
        }

    def reset_conversation(self):
        """Reset conversation state."""
        pass

    def set_model(self, model_type: str):
        """Set model type."""
        self._model_type = model_type

    def set_thinking_level(self, level: str):
        """Set thinking level."""
        self._thinking_level = level

    def get_model_name(self) -> str:
        """Return the model display name."""
        return "Claude Sonnet 4.5"
