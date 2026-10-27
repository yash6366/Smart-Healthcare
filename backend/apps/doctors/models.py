from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from apps.common.models import TimeStampedModel


class DoctorProfile(TimeStampedModel):
    """
    Healthcare practitioner profile managing qualifications, specialization,
    consultation fee, working hours, and verification status.
    """

    class Specialization(models.TextChoices):
        GENERAL_MEDICINE = "GENERAL_MEDICINE", "General Medicine"
        CARDIOLOGY = "CARDIOLOGY", "Cardiology"
        DERMATOLOGY = "DERMATOLOGY", "Dermatology"
        PEDIATRICS = "PEDIATRICS", "Pediatrics"
        ORTHOPEDICS = "ORTHOPEDICS", "Orthopedics"
        NEUROLOGY = "NEUROLOGY", "Neurology"
        PSYCHIATRY = "PSYCHIATRY", "Psychiatry"
        GYNECOLOGY = "GYNECOLOGY", "Gynecology & Obstetrics"
        OPHTHALMOLOGY = "OPHTHALMOLOGY", "Ophthalmology"
        ENT = "ENT", "Ear, Nose & Throat"
        ONCOLOGY = "ONCOLOGY", "Oncology"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
    )
    display_name = models.CharField(max_length=150)
    specialization = models.CharField(
        max_length=50,
        choices=Specialization.choices,
        default=Specialization.GENERAL_MEDICINE,
        db_index=True,
    )
    qualifications = models.CharField(max_length=255, help_text="e.g. MBBS, MD, MS")
    years_of_experience = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("500.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    biography = models.TextField(blank=True, default="")
    license_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="State medical council registration / license number",
    )
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Designates whether the doctor's license and credentials have been verified by an administrator.",
    )
    is_available = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Designates whether the doctor is currently accepting appointment bookings.",
    )
    working_hours_start = models.TimeField(default="09:00:00")
    working_hours_end = models.TimeField(default="17:00:00")

    class Meta:
        verbose_name = "Doctor Profile"
        verbose_name_plural = "Doctor Profiles"
        ordering = ["-is_verified", "display_name"]
        indexes = [
            models.Index(fields=["specialization", "is_verified", "is_available"]),
        ]

    def __str__(self):
        status = "Verified" if self.is_verified else "Pending Verification"
        return f"Dr. {self.display_name} ({self.get_specialization_display()}) - {status}"
