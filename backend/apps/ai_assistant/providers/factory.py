from django.conf import settings
from .base import BaseAIProvider
from .gemini_provider import GeminiAIProvider
from .mock_provider import MockAIProvider
from .openai_provider import OpenAIProvider


def get_ai_provider() -> BaseAIProvider:
    """
    Factory function instantiating the configured AI provider.
    Supports 'openai', 'gemini' (or 'google'), and defaults to 'mock'.
    """
    provider_name = getattr(settings, "AI_PROVIDER", "mock").lower()
    if provider_name in ("openai", "chatgpt"):
        return OpenAIProvider()
    if provider_name in ("gemini", "google"):
        return GeminiAIProvider()
    return MockAIProvider()
