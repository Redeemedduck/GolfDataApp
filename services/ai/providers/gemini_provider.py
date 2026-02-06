import os
import gemini_coach
from services.ai.registry import register_provider


@register_provider
class GeminiProvider:
    PROVIDER_ID = "gemini"
    DISPLAY_NAME = "Gemini (API)"
    MODEL_OPTIONS = {
        "Gemini 3.0 Flash": "flash",
        "Gemini 3.0 Pro": "pro",
    }

    def __init__(self, model_type: str = "flash", thinking_level: str = "medium"):
        self._coach = gemini_coach.GeminiCoach(
            model_type=model_type,
            thinking_level=thinking_level
        )

    @staticmethod
    def is_configured() -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))

    def chat(self, message: str):
        return self._coach.chat(message)

    def reset_conversation(self):
        self._coach.reset_conversation()

    def set_model(self, model_type: str):
        self._coach.set_model(model_type)

    def set_thinking_level(self, level: str):
        self._coach.set_thinking_level(level)

    def get_model_name(self) -> str:
        return self._coach.model_name
