from django.apps import AppConfig


class MedicalRecordsConfig(AppConfig):
    """HEALTHCARE Domain: Electronic Health Records (table: medical_records_medicalrecord)."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.medical_records"
    label = "medical_records"
