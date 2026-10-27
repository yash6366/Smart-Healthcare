from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Security and compliance audit trail recording critical platform actions.
    Records cannot be updated or deleted by regular users.
    """

    class EventType(models.TextChoices):
        AUTH_LOGIN = "AUTH_LOGIN", "User Login"
        AUTH_LOGOUT = "AUTH_LOGOUT", "User Logout"
        AUTH_REGISTER = "AUTH_REGISTER", "User Registration"
        AUTH_PASSWORD_CHANGE = "AUTH_PASSWORD_CHANGE", "Password Change"
        DOCTOR_VERIFIED = "DOCTOR_VERIFIED", "Doctor Verification"
        DOCTOR_AVAILABILITY = "DOCTOR_AVAILABILITY", "Doctor Availability Change"
        APPOINTMENT_CREATED = "APPOINTMENT_CREATED", "Appointment Created"
        APPOINTMENT_STATUS_CHANGE = "APPOINTMENT_STATUS_CHANGE", "Appointment Status Change"
        APPOINTMENT_CANCELLED = "APPOINTMENT_CANCELLED", "Appointment Cancelled"
        PRESCRIPTION_ISSUED = "PRESCRIPTION_ISSUED", "Prescription Issued"
        MEDICAL_RECORD_ACCESSED = "MEDICAL_RECORD_ACCESSED", "Medical Record Accessed"
        MEDICAL_RECORD_CREATED = "MEDICAL_RECORD_CREATED", "Medical Record Created"
        AI_QUERY = "AI_QUERY", "AI Query Executed"
        ADMIN_ACTION = "ADMIN_ACTION", "Administrative Action"
        PERMISSION_DENIED = "PERMISSION_DENIED", "Permission Denied"

    event_type = models.CharField(max_length=50, choices=EventType.choices, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    resource_type = models.CharField(max_length=100, blank=True, default="")
    resource_id = models.CharField(max_length=100, blank=True, default="")
    action = models.CharField(max_length=100)
    details = models.JSONField(default=dict, blank=True)
    is_success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def __str__(self):
        actor_name = self.actor.username if self.actor else "Anonymous"
        return f"[{self.created_at}] {self.event_type} by {actor_name} - {self.action}"
