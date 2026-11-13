from django.apps import AppConfig


class DoctorsConfig(AppConfig):
    """CORE Domain: Doctor credentials & schedules (table: doctors_doctorprofile)."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.doctors"
    label = "doctors"
