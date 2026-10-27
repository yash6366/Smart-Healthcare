from rest_framework import serializers
from .models import Appointment
from apps.doctors.models import DoctorProfile
from apps.patients.models import PatientProfile
from apps.doctors.serializers import DoctorPublicSerializer
from apps.patients.serializers import PatientProfileSerializer


class AppointmentSerializer(serializers.ModelSerializer):
    """
    Detailed read representation of an appointment.
    """
    doctor = DoctorPublicSerializer(read_only=True)
    patient = PatientProfileSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    cancelled_by_username = serializers.CharField(source="cancelled_by.username", read_only=True, default=None)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "doctor",
            "appointment_date",
            "start_time",
            "end_time",
            "duration_minutes",
            "reason",
            "status",
            "status_display",
            "cancellation_reason",
            "cancelled_by_username",
            "cancelled_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AppointmentBookingSerializer(serializers.Serializer):
    """
    Serializer to validate incoming appointment scheduling requests.
    """
    doctor_id = serializers.IntegerField(required=True)
    patient_id = serializers.IntegerField(required=False, allow_null=True)
    appointment_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True)
    duration_minutes = serializers.IntegerField(default=30, min_value=15, max_value=120)
    reason = serializers.CharField(required=True, min_length=5)

    def validate_doctor_id(self, value):
        try:
            return DoctorProfile.objects.get(pk=value)
        except DoctorProfile.DoesNotExist:
            raise serializers.ValidationError("Doctor with this ID does not exist.")

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        # Determine patient
        if user and user.role == "PATIENT":
            try:
                patient = user.patient_profile
            except PatientProfile.DoesNotExist:
                patient = PatientProfile.objects.create(user=user)
            attrs["patient"] = patient
        elif user and (user.role == "ADMIN" or user.is_superuser):
            patient_id = attrs.get("patient_id")
            if not patient_id:
                raise serializers.ValidationError({"patient_id": "Administrators must specify a patient_id."})
            try:
                attrs["patient"] = PatientProfile.objects.get(pk=patient_id)
            except PatientProfile.DoesNotExist:
                raise serializers.ValidationError({"patient_id": "Specified patient does not exist."})
        else:
            raise serializers.ValidationError("Only patients or administrators can book appointments.")

        attrs["doctor"] = attrs.pop("doctor_id")
        return attrs


class AppointmentCancelSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField(required=False, allow_blank=True, default="")


class AppointmentRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")
