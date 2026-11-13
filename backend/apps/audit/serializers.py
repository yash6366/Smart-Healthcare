from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True, default="Anonymous")

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "event_type",
            "actor",
            "actor_username",
            "ip_address",
            "user_agent",
            "resource_type",
            "resource_id",
            "action",
            "details",
            "is_success",
            "created_at",
        ]
        read_only_fields = fields


class AnalyticsPeriodSerializer(serializers.Serializer):
    days = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class PractitionersAndPatientsStatsSerializer(serializers.Serializer):
    total_patients = serializers.IntegerField()
    total_doctors = serializers.IntegerField()
    verified_doctors = serializers.IntegerField()
    pending_verification_doctors = serializers.IntegerField()
    currently_available_doctors = serializers.IntegerField()


class AppointmentCountsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    confirmed = serializers.IntegerField()
    completed = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    rejected = serializers.IntegerField()


class AnalyticsRatesSerializer(serializers.Serializer):
    completion_rate_percent = serializers.FloatField()
    cancellation_rate_percent = serializers.FloatField()
    completion_rate_denominator = serializers.CharField()
    cancellation_rate_denominator = serializers.CharField()


class DoctorWorkloadSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField()
    name = serializers.CharField()
    specialization = serializers.CharField()
    total_consultations = serializers.IntegerField()
    completed = serializers.IntegerField()
    cancelled = serializers.IntegerField()


class ClinicalVolumeSerializer(serializers.Serializer):
    total_prescriptions = serializers.IntegerField()
    total_medical_records = serializers.IntegerField()
    total_audit_events = serializers.IntegerField()


class RecentAuditSnippetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    event_type = serializers.CharField()
    action = serializers.CharField()
    ip_address = serializers.CharField(allow_null=True)
    is_success = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    actor__username = serializers.CharField(allow_null=True)


class SystemHealthSummarySerializer(serializers.Serializer):
    backend_service = serializers.CharField()
    database = serializers.CharField()
    ai_engine_configured = serializers.CharField()


class AdminAnalyticsResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    period = AnalyticsPeriodSerializer()
    practitioners_and_patients = PractitionersAndPatientsStatsSerializer()
    appointments_all_time = AppointmentCountsSerializer()
    appointments_window = AppointmentCountsSerializer()
    rates = AnalyticsRatesSerializer()
    doctor_workloads = DoctorWorkloadSerializer(many=True)
    clinical_volume = ClinicalVolumeSerializer()
    recent_audit_events = RecentAuditSnippetSerializer(many=True)
    system_health = SystemHealthSummarySerializer()
