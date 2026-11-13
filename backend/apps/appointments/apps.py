from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    """HEALTHCARE Domain: Consultation scheduling (table: appointments_appointment)."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.appointments"
    label = "appointments"
