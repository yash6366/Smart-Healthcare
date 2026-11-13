from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """SECURITY Domain read-only admin for immutable compliance audit logs."""

    list_display = (
        "id",
        "event_type",
        "actor",
        "action",
        "resource_type",
        "resource_id",
        "is_success",
        "created_at",
    )
    list_filter = ("event_type", "is_success", "resource_type", "created_at")
    search_fields = (
        "actor__username",
        "actor__email",
        "action",
        "resource_type",
        "resource_id",
        "ip_address",
    )
    readonly_fields = (
        "event_type",
        "actor",
        "ip_address",
        "user_agent",
        "resource_type",
        "resource_id",
        "action",
        "details",
        "is_success",
        "created_at",
    )
    raw_id_fields = ("actor",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

