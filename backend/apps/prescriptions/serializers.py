from django.db import transaction
from rest_framework import serializers

from .models import Prescription, PrescriptionItem
from apps.patients.models import PatientProfile
from apps.appointments.models import Appointment
from apps.doctors.serializers import DoctorPublicSerializer
from apps.patients.serializers import PatientProfileSerializer


class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = ["id", "medication_name", "dosage", "frequency", "duration", "instructions"]
        read_only_fields = ["id"]


class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)
    doctor = DoctorPublicSerializer(read_only=True)
    patient = PatientProfileSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Prescription
        fields = [
            "id",
            "patient",
            "doctor",
            "appointment",
            "diagnosis",
            "notes",
            "status",
            "status_display",
            "items",
            "issued_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PrescriptionItemCreateSerializer(serializers.Serializer):
    medication_name = serializers.CharField(max_length=255, required=True)
    dosage = serializers.CharField(max_length=100, required=True)
    frequency = serializers.CharField(max_length=100, required=True)
    duration = serializers.CharField(max_length=100, required=True)
    instructions = serializers.CharField(required=False, allow_blank=True, default="")


class PrescriptionCreateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(required=True)
    appointment_id = serializers.IntegerField(required=False, allow_null=True)
    diagnosis = serializers.CharField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = PrescriptionItemCreateSerializer(many=True, required=True)

    def validate_patient_id(self, value):
        try:
            return PatientProfile.objects.get(pk=value)
        except PatientProfile.DoesNotExist:
            raise serializers.ValidationError("Patient not found.")

    def validate_appointment_id(self, value):
        if not value:
            return None
        try:
            return Appointment.objects.get(pk=value)
        except Appointment.DoesNotExist:
            raise serializers.ValidationError("Appointment not found.")

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one medication item must be specified in the prescription.")
        return value

    def validate(self, attrs):
        patient = attrs.get("patient_id")
        appointment = attrs.get("appointment_id")
        doctor = self.context.get("doctor")

        if appointment:
            if patient and appointment.patient_id != patient.id:
                raise serializers.ValidationError({"appointment_id": "Appointment does not belong to the specified patient."})
            if doctor and appointment.doctor_id != doctor.id:
                raise serializers.ValidationError({"appointment_id": "Appointment does not belong to the acting doctor."})
        return attrs

    def create(self, validated_data):
        patient = validated_data["patient_id"]
        appointment = validated_data.get("appointment_id")
        diagnosis = validated_data["diagnosis"]
        notes = validated_data.get("notes", "")
        items_data = validated_data["items"]
        doctor = self.context["doctor"]

        with transaction.atomic():
            prescription = Prescription.objects.create(
                patient=patient,
                doctor=doctor,
                appointment=appointment,
                diagnosis=diagnosis,
                notes=notes,
                status=Prescription.Status.ACTIVE,
            )

            prescription_items = [
                PrescriptionItem(
                    prescription=prescription,
                    medication_name=item["medication_name"],
                    dosage=item["dosage"],
                    frequency=item["frequency"],
                    duration=item["duration"],
                    instructions=item.get("instructions", ""),
                )
                for item in items_data
            ]
            PrescriptionItem.objects.bulk_create(prescription_items)

        return prescription
