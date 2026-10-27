from django.db import models
from apps.common.models import TimeStampedModel


class Prescription(TimeStampedModel):
    """
    Formal medical prescription issued by a licensed healthcare professional.
    Contains diagnosis, advice, and linked medication items.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    patient = models.ForeignKey(
        "patients.PatientProfile",
        on_delete=models.PROTECT,
        related_name="prescriptions",
    )
    doctor = models.ForeignKey(
        "doctors.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="issued_prescriptions",
    )
    appointment = models.ForeignKey(
        "appointments.Appointment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prescriptions",
    )
    diagnosis = models.TextField(help_text="Clinical diagnosis necessitating this prescription")
    notes = models.TextField(blank=True, default="", help_text="Special dietary advice or instructions")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    issued_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Prescription"
        verbose_name_plural = "Prescriptions"
        ordering = ["-issued_at"]
        indexes = [
            models.Index(fields=["patient", "status", "issued_at"]),
            models.Index(fields=["doctor", "issued_at"]),
        ]

    def __str__(self):
        return f"Prescription #{self.id} for {self.patient.user.username} by Dr. {self.doctor.display_name}"


class PrescriptionItem(models.Model):
    """
    Individual medication item within a prescription with explicit dosage, frequency, and duration.
    """
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name="items",
    )
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100, help_text="e.g. 500mg, 10ml")
    frequency = models.CharField(max_length=100, help_text="e.g. Twice daily after food")
    duration = models.CharField(max_length=100, help_text="e.g. 5 days, 1 month")
    instructions = models.TextField(blank=True, default="", help_text="e.g. Take with warm water")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.medication_name} - {self.dosage} ({self.frequency})"
