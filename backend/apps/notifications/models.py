from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    In-app notifications and alerts. Prepared for future push/email asynchronous worker dispatch.
    """

    class NotificationType(models.TextChoices):
        APPOINTMENT_REQUESTED = "APPOINTMENT_REQUESTED", "Appointment Requested"
        APPOINTMENT_CONFIRMED = "APPOINTMENT_CONFIRMED", "Appointment Confirmed"
        APPOINTMENT_REJECTED = "APPOINTMENT_REJECTED", "Appointment Rejected"
        APPOINTMENT_CANCELLED = "APPOINTMENT_CANCELLED", "Appointment Cancelled"
        APPOINTMENT_COMPLETED = "APPOINTMENT_COMPLETED", "Appointment Completed"
        APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER", "Appointment Reminder"
        PRESCRIPTION_ISSUED = "PRESCRIPTION_ISSUED", "Prescription Issued"
        ACCOUNT_UPDATE = "ACCOUNT_UPDATE", "Account Update"
        GENERAL = "GENERAL", "General Notification"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
        ]

    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"Notification to {self.recipient.username}: {self.title} ({status})"
