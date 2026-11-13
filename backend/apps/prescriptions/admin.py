from django.contrib import admin

from .models import Prescription, PrescriptionItem


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    """HEALTHCARE Domain admin for clinical prescriptions."""

    list_display = ("id", "patient", "doctor", "status", "issued_at", "is_active")
    list_filter = ("status", "is_active", "issued_at")
    search_fields = (
        "patient__user__username",
        "doctor__display_name",
        "diagnosis",
    )
    readonly_fields = ("issued_at", "created_at", "updated_at")
    raw_id_fields = ("patient", "doctor", "appointment")
    inlines = [PrescriptionItemInline]


@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    """HEALTHCARE Domain admin for prescription medication line items."""

    list_display = ("id", "prescription", "medication_name", "dosage", "frequency", "duration")
    search_fields = ("medication_name", "prescription__patient__user__username")
    raw_id_fields = ("prescription",)

