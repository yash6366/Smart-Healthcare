from rest_framework import serializers
from .models import MedicalRecord
from apps.patients.models import PatientProfile


class MedicalRecordSerializer(serializers.ModelSerializer):
    record_type_display = serializers.CharField(source="get_record_type_display", read_only=True)
    doctor_name = serializers.CharField(source="doctor.display_name", read_only=True, default=None)
    patient_name = serializers.CharField(source="patient.user.get_full_name", read_only=True)

    class Meta:
        model = MedicalRecord
        fields = [
            "id",
            "patient",
            "patient_name",
            "doctor",
            "doctor_name",
            "record_type",
            "record_type_display",
            "title",
            "description",
            "clinical_data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "doctor", "created_at", "updated_at"]


class MedicalRecordCreateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(required=True)
    record_type = serializers.ChoiceField(choices=MedicalRecord.RecordType.choices, default=MedicalRecord.RecordType.CONSULTATION_NOTE)
    title = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(required=True)
    clinical_data = serializers.JSONField(required=False, default=dict)

    def validate_patient_id(self, value):
        try:
            return PatientProfile.objects.get(pk=value)
        except PatientProfile.DoesNotExist:
            raise serializers.ValidationError("Patient not found.")
