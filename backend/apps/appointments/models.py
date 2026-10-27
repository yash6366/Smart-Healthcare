from django.conf import settings
from django.db import models
from apps.common.models import TimeStampedModel


class Appointment(TimeStampedModel):
    """
    Appointment model capturing patient-doctor consultations,
    time slots, reasons, statuses, and cancellation tracking.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Confirmation"
        CONFIRMED = "CONFIRMED", "Confirmed"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    ACTIVE_STATUSES = [Status.PENDING, Status.CONFIRMED]

    patient = models.ForeignKey(
        "patients.PatientProfile",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    doctor = models.ForeignKey(
        "doctors.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    appointment_date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    reason = models.TextField(help_text="Primary symptoms or reason for medical consultation")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    cancellation_reason = models.TextField(blank=True, default="")
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cancelled_appointments",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        ordering = ["-appointment_date", "-start_time"]
        indexes = [
            models.Index(fields=["doctor", "appointment_date", "status"]),
            models.Index(fields=["patient", "appointment_date", "status"]),
            models.Index(fields=["status", "appointment_date"]),
        ]

    def __str__(self):
        return (
            f"Appointment #{self.id} with Dr. {self.doctor.display_name} "
            f"for {self.patient.user.get_full_name() or self.patient.user.username} "
            f"on {self.appointment_date} at {self.start_time} [{self.get_status_display()}]"
        )
