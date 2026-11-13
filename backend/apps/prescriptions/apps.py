from django.apps import AppConfig


class PrescriptionsConfig(AppConfig):
    """HEALTHCARE Domain: Prescriptions & items (tables: prescriptions_prescription, prescriptions_prescriptionitem)."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.prescriptions"
    label = "prescriptions"
