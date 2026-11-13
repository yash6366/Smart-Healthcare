from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("role", "content", "metadata", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """COMMUNICATION Domain admin for AI assistant conversation sessions."""

    list_display = ("id", "owner", "title", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("owner__username", "owner__email", "title")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("owner",)
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """COMMUNICATION Domain admin for AI assistant conversation turns."""

    list_display = ("id", "conversation", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("conversation__owner__username", "content")
    readonly_fields = ("created_at",)
    raw_id_fields = ("conversation",)

