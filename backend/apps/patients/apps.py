from django.apps import AppConfig


class PatientsConfig(AppConfig):
    """CORE Domain: Patient demographic profiles (table: patients_patientprofile)."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.patients"
    label = "patients"
