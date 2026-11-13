from django.apps import AppConfig


class AiAssistantConfig(AppConfig):
    """COMMUNICATION Domain: AI conversations & messages (tables: ai_assistant_conversation, ai_assistant_message)."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_assistant"
    label = "ai_assistant"
