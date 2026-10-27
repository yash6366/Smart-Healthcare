"""
AI Assistant models supporting persistent multi-turn conversations and message history.
"""
from django.conf import settings
from django.db import models
from apps.common.models import TimeStampedModel


class Conversation(TimeStampedModel):
    """
    Persistent AI inquiry session owned exclusively by the authenticated user.
    Strictly isolated: neither doctors nor administrators gain access to patient conversations.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
        db_index=True,
    )
    title = models.CharField(max_length=255, default="General Health Inquiry")

    class Meta:
        verbose_name = "AI Conversation"
        verbose_name_plural = "AI Conversations"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["owner", "updated_at"]),
        ]

    def __str__(self):
        return f"Conversation #{self.id} ({self.title}) - {self.owner.username}"


class Message(models.Model):
    """
    Individual message turn within an AI conversation session.
    """
    class Role(models.TextChoices):
        USER = "USER", "User"
        ASSISTANT = "ASSISTANT", "AI Assistant"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        db_index=True,
    )
    content = models.TextField(help_text="User query or AI-generated guidance")
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="AI provider output metadata: suggested specialization, emergency alerts, disclaimer, provider engine.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "AI Message"
        verbose_name_plural = "AI Messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.role}] Msg #{self.id} in Conv #{self.conversation_id}"
