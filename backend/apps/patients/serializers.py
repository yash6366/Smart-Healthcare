from rest_framework import serializers
from .models import PatientProfile
from apps.accounts.serializers import UserSerializer


class PatientProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for Patient Profile management.
    Includes user details and handles safe updates.
    """
    user = UserSerializer(read_only=True)
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    phone_number = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = PatientProfile
        fields = [
            "id",
            "user",
            "date_of_birth",
            "gender",
            "blood_group",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
            "address",
            "city",
            "state",
            "postal_code",
            "created_at",
            "updated_at",
            "first_name",
            "last_name",
            "phone_number",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        # Extract user fields if provided
        first_name = validated_data.pop("first_name", None)
        last_name = validated_data.pop("last_name", None)
        phone_number = validated_data.pop("phone_number", None)

        user = instance.user
        user_updated = False
        if first_name is not None:
            user.first_name = first_name
            user_updated = True
        if last_name is not None:
            user.last_name = last_name
            user_updated = True
        if phone_number is not None:
            user.phone_number = phone_number
            user_updated = True
        if user_updated:
            user.save()

        return super().update(instance, validated_data)


class TimelineEventSerializer(serializers.Serializer):
    event_type = serializers.ChoiceField(choices=["APPOINTMENT", "MEDICAL_RECORD", "PRESCRIPTION"])
    event_id = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
    title = serializers.CharField()
    subtitle = serializers.CharField()
    status = serializers.CharField()
    doctor_name = serializers.CharField()
    details = serializers.DictField()


class PatientHealthTimelineResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    patient_id = serializers.IntegerField()
    total_events = serializers.IntegerField()
    results = TimelineEventSerializer(many=True)


class ClinicalHistoryEmergencyContactSerializer(serializers.Serializer):
    name = serializers.CharField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)
    relation = serializers.CharField(allow_blank=True)


class ClinicalHistoryPatientSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    gender = serializers.CharField()
    blood_group = serializers.CharField()
    date_of_birth = serializers.DateField(allow_null=True)
    emergency_contact = ClinicalHistoryEmergencyContactSerializer()


class ClinicalHistoryRecordItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    record_type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    clinical_data = serializers.DictField()
    doctor_name = serializers.CharField()
    created_at = serializers.DateTimeField()


class ClinicalHistoryMedicationItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    dosage = serializers.CharField()
    frequency = serializers.CharField()
    duration = serializers.CharField()
    instructions = serializers.CharField(allow_blank=True)


class ClinicalHistoryPrescriptionItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    diagnosis = serializers.CharField()
    status = serializers.CharField()
    notes = serializers.CharField(allow_blank=True)
    issued_at = serializers.DateTimeField()
    doctor_name = serializers.CharField()
    items = ClinicalHistoryMedicationItemSerializer(many=True)


class ClinicalHistoryConsultationItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField()
    start_time = serializers.CharField()
    status = serializers.CharField()
    reason = serializers.CharField()
    doctor_name = serializers.CharField()


class PatientClinicalHistoryResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    patient = ClinicalHistoryPatientSummarySerializer()
    medical_records = ClinicalHistoryRecordItemSerializer(many=True)
    prescriptions = ClinicalHistoryPrescriptionItemSerializer(many=True)
    recent_consultations = ClinicalHistoryConsultationItemSerializer(many=True)
