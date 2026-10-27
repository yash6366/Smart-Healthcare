from django.db import models
from apps.common.models import TimeStampedModel


class MedicalRecord(TimeStampedModel):
    """
    Patient electronic health records (EHR) preserving clinical consultations,
    diagnostic summaries, and lab reports.
    """

    class RecordType(models.TextChoices):
        CONSULTATION_NOTE = "CONSULTATION_NOTE", "Consultation Note"
        DIAGNOSIS = "DIAGNOSIS", "Clinical Diagnosis"
        LAB_RESULT = "LAB_RESULT", "Laboratory Result"
        DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY", "Discharge Summary"
        VACCINATION = "VACCINATION", "Vaccination Record"
        OTHER = "OTHER", "Other Clinical Note"

    patient = models.ForeignKey(
        "patients.PatientProfile",
        on_delete=models.CASCADE,
        related_name="medical_records",
    )
    doctor = models.ForeignKey(
        "doctors.DoctorProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recorded_medical_records",
    )
    record_type = models.CharField(
        max_length=50,
        choices=RecordType.choices,
        default=RecordType.CONSULTATION_NOTE,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(help_text="Clinical findings, notes, or patient condition summary")
    clinical_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured clinical observations (vitals, test metrics, etc.)",
    )

    class Meta:
        verbose_name = "Medical Record"
        verbose_name_plural = "Medical Records"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient", "record_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_record_type_display()}: {self.title} for {self.patient.user.username}"
