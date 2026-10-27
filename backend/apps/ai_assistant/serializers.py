from rest_framework import serializers
from .models import Conversation, Message


class AIGuidanceRequestSerializer(serializers.Serializer):
    query = serializers.CharField(
        min_length=5,
        max_length=1000,
        required=True,
        help_text="Health question, symptoms, or wellness query (5 to 1000 characters)",
    )
    context = serializers.JSONField(required=False, default=dict)


class AIGuidanceResponseSerializer(serializers.Serializer):
    provider = serializers.CharField()
    guidance = serializers.CharField()
    suggested_specialization = serializers.CharField(required=False)
    disclaimer = serializers.CharField()
    is_emergency_alert = serializers.BooleanField(default=False)


class AISummarizeRecordRequestSerializer(serializers.Serializer):
    record_id = serializers.IntegerField(required=True)


class AISummarizeResponseSerializer(serializers.Serializer):
    provider = serializers.CharField()
    summary = serializers.CharField()
    disclaimer = serializers.CharField()


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "role",
            "content",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "role", "content", "metadata", "created_at"]


class ConversationListSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "created_at",
            "updated_at",
            "message_count",
            "last_message",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                "role": last_msg.role,
                "content_preview": last_msg.content[:100] + ("..." if len(last_msg.content) > 100 else ""),
                "created_at": last_msg.created_at,
            }
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "created_at",
            "updated_at",
            "messages",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "messages"]


class ConversationCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, default="General Health Inquiry")
    query = serializers.CharField(
        min_length=5,
        max_length=1000,
        required=True,
        help_text="Initial health inquiry or symptom description (5 to 1000 characters)",
    )


class MessageCreateSerializer(serializers.Serializer):
    query = serializers.CharField(
        min_length=5,
        max_length=1000,
        required=True,
        help_text="Follow-up question or clarification (5 to 1000 characters)",
    )
