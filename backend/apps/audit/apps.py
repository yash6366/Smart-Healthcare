from django.apps import AppConfig


class AuditConfig(AppConfig):
    """SECURITY Domain: Immutable compliance audit log (table: audit_auditlog)."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    label = "audit"
