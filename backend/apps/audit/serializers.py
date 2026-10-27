from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True, default="Anonymous")

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "event_type",
            "actor",
            "actor_username",
            "ip_address",
            "user_agent",
            "resource_type",
            "resource_id",
            "action",
            "details",
            "is_success",
            "created_at",
        ]
        read_only_fields = fields
