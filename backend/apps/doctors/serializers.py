from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import DoctorProfile
from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer


class DoctorPublicSerializer(serializers.ModelSerializer):
    """
    Publicly visible directory listing for verified, active doctors.
    Hides internal credentials and sensitive license details.
    """
    specialization_display = serializers.CharField(source="get_specialization_display", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = DoctorProfile
        fields = [
            "id",
            "user_id",
            "display_name",
            "specialization",
            "specialization_display",
            "qualifications",
            "years_of_experience",
            "consultation_fee",
            "biography",
            "is_available",
            "working_hours_start",
            "working_hours_end",
        ]
        read_only_fields = fields


class DoctorDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive doctor serializer used for doctor self-profile management and administrative audits.
    """
    user = UserSerializer(read_only=True)
    specialization_display = serializers.CharField(source="get_specialization_display", read_only=True)

    class Meta:
        model = DoctorProfile
        fields = [
            "id",
            "user",
            "display_name",
            "specialization",
            "specialization_display",
            "qualifications",
            "years_of_experience",
            "consultation_fee",
            "biography",
            "license_number",
            "is_verified",
            "is_available",
            "working_hours_start",
            "working_hours_end",
            "created_at",
            "updated_at",
        ]
        # is_verified and user are read_only so doctors cannot verify themselves
        read_only_fields = ["id", "user", "is_verified", "created_at", "updated_at"]


class DoctorAdminCreateSerializer(serializers.Serializer):
    """
    Administrator serializer to provision and invite a doctor.
    """
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")
    phone_number = serializers.CharField(max_length=20, required=False, default="")

    display_name = serializers.CharField(max_length=150)
    specialization = serializers.ChoiceField(choices=DoctorProfile.Specialization.choices)
    qualifications = serializers.CharField(max_length=255)
    years_of_experience = serializers.IntegerField(min_value=0, default=0)
    consultation_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=500.00)
    biography = serializers.CharField(required=False, allow_blank=True, default="")
    license_number = serializers.CharField(max_length=100)
    is_verified = serializers.BooleanField(default=False)
    is_available = serializers.BooleanField(default=True)

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return normalized

    def validate_username(self, value):
        cleaned = value.strip()
        if User.objects.filter(username__iexact=cleaned).exists():
            raise serializers.ValidationError("An account with this username already exists.")
        return cleaned

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        username = validated_data.pop("username")
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        first_name = validated_data.pop("first_name", "")
        last_name = validated_data.pop("last_name", "")
        phone_number = validated_data.pop("phone_number", "")

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role=User.Role.DOCTOR,
                is_verified=validated_data.get("is_verified", False),
            )
            doctor_profile = DoctorProfile.objects.create(user=user, **validated_data)
        return doctor_profile


class DoctorVerifySerializer(serializers.Serializer):
    """
    Serializer for admin approval or rejection of doctor verification.
    """
    is_verified = serializers.BooleanField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
