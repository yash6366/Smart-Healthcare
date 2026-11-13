from django.contrib import admin

from .models import DoctorProfile


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    """CORE Domain admin for healthcare practitioner profiles."""

    list_display = (
        "display_name",
        "user",
        "specialization",
        "is_verified",
        "is_available",
        "consultation_fee",
        "created_at",
    )
    list_filter = ("specialization", "is_verified", "is_available", "is_active")
    search_fields = (
        "display_name",
        "user__username",
        "user__email",
        "license_number",
        "qualifications",
    )
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user",)

