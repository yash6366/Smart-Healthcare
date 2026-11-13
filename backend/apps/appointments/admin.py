from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """HEALTHCARE Domain admin for clinical consultation appointments."""

    list_display = (
        "id",
        "patient",
        "doctor",
        "appointment_date",
        "start_time",
        "end_time",
        "status",
        "created_at",
    )
    list_filter = ("status", "appointment_date", "is_active")
    search_fields = (
        "patient__user__username",
        "patient__user__email",
        "doctor__display_name",
        "reason",
    )
    readonly_fields = ("created_at", "updated_at", "cancelled_at")
    raw_id_fields = ("patient", "doctor", "cancelled_by")

