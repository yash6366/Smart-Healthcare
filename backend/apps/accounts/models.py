from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """
    Custom user manager supporting email-based and username-based authentication,
    email normalization, and explicit role provisioning.
    """

    def create_user(self, email: str, username: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set.")
        if not username:
            raise ValueError("The Username field must be set.")

        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        # Default role for standard users is PATIENT unless explicitly specified
        extra_fields.setdefault("role", User.Role.PATIENT)

        user = self.model(email=email, username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, username: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model for VakCare platform with explicit role-based access.
    The ADMIN application role does NOT automatically grant Django superuser privileges.
    """

    class Role(models.TextChoices):
        PATIENT = "PATIENT", "Patient"
        DOCTOR = "DOCTOR", "Doctor"
        ADMIN = "ADMIN", "Administrator"

    email = models.EmailField(unique=True, db_index=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PATIENT,
        db_index=True,
        help_text="User platform role for access control",
    )
    phone_number = models.CharField(max_length=20, blank=True, default="")
    is_verified = models.BooleanField(
        default=False,
        help_text="Designates whether the user's role/credentials have been verified.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "role"]),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_patient(self) -> bool:
        return self.role == self.Role.PATIENT

    @property
    def is_doctor(self) -> bool:
        return self.role == self.Role.DOCTOR

    @property
    def is_administrator(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser
