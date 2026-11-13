from django.contrib import admin

from .models import PatientProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    """CORE Domain admin for patient demographic and emergency contact profiles."""

    list_display = (
        "user",
        "gender",
        "blood_group",
        "city",
        "state",
        "is_active",
        "created_at",
    )
    list_filter = ("gender", "blood_group", "is_active")
    search_fields = (
        "user__username",
        "user__email",
        "city",
        "state",
        "emergency_contact_name",
    )
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user",)

