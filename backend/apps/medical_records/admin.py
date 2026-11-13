from django.contrib import admin

from .models import MedicalRecord


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    """HEALTHCARE Domain admin for electronic health records (EHR)."""

    list_display = (
        "id",
        "record_type",
        "title",
        "patient",
        "doctor",
        "is_active",
        "created_at",
    )
    list_filter = ("record_type", "is_active", "created_at")
    search_fields = (
        "title",
        "description",
        "patient__user__username",
        "doctor__display_name",
    )
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("patient", "doctor")

