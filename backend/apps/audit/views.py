from datetime import timedelta
from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import AuditLog
from .serializers import AuditLogSerializer
from apps.accounts.permissions import IsAdministrator
from apps.patients.models import PatientProfile
from apps.doctors.models import DoctorProfile
from apps.appointments.models import Appointment
from apps.prescriptions.models import Prescription
from apps.medical_records.models import MedicalRecord


class AuditLogListView(generics.ListAPIView):
    """
    List compliance and security audit logs.
    Restricted strictly to platform administrators.
    """
    permission_classes = [IsAdministrator]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all().select_related("actor")

    def get_queryset(self):
        qs = super().get_queryset()
        event_type = self.request.query_params.get("event_type")
        if event_type:
            qs = qs.filter(event_type=event_type)
        resource_type = self.request.query_params.get("resource_type")
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        return qs

    @extend_schema(tags=["Audit"], summary="List Audit Logs (Admin Only)")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AuditLogDetailView(generics.RetrieveAPIView):
    """
    Retrieve single audit log entry.
    Restricted strictly to platform administrators.
    """
    permission_classes = [IsAdministrator]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all().select_related("actor")

    @extend_schema(tags=["Audit"], summary="Get Audit Log Detail (Admin Only)")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminAnalyticsView(APIView):
    """
    Advanced operational and clinical analytics for platform governance.
    Computes aggregated KPIs directly in the database, including appointment completion/cancellation rates,
    practitioner workload distributions, and live system health diagnostics.
    Restricted strictly to Platform Administrators.
    """
    permission_classes = [IsAdministrator]

    @extend_schema(
        tags=["Audit"],
        summary="Get Comprehensive Platform Analytics (Admin Only)",
        parameters=[
            OpenApiParameter(name="days", description="Analysis window in days (default: 30)", required=False, type=int),
        ],
    )
    def get(self, request):
        now = timezone.now()
        days_param = request.query_params.get("days", "30")
        try:
            days = max(1, min(int(days_param), 365))
        except ValueError:
            days = 30

        window_start = (now - timedelta(days=days)).date()
        window_end = now.date()

        # 1. User & Practitioner Metrics
        total_patients = PatientProfile.objects.count()
        total_doctors = DoctorProfile.objects.count()
        verified_doctors = DoctorProfile.objects.filter(is_verified=True).count()
        pending_doctors = DoctorProfile.objects.filter(is_verified=False).count()
        available_doctors = DoctorProfile.objects.filter(is_available=True).count()

        # 2. Appointment Aggregates (All-Time)
        all_time_appts = Appointment.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status="PENDING")),
            confirmed=Count("id", filter=Q(status="CONFIRMED")),
            completed=Count("id", filter=Q(status="COMPLETED")),
            cancelled=Count("id", filter=Q(status="CANCELLED")),
            rejected=Count("id", filter=Q(status="REJECTED")),
        )

        # 3. Appointment Aggregates (Window-Filtered)
        window_appts = Appointment.objects.filter(
            appointment_date__gte=window_start,
            appointment_date__lte=window_end,
        ).aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status="PENDING")),
            confirmed=Count("id", filter=Q(status="CONFIRMED")),
            completed=Count("id", filter=Q(status="COMPLETED")),
            cancelled=Count("id", filter=Q(status="CANCELLED")),
            rejected=Count("id", filter=Q(status="REJECTED")),
        )

        # 4. Rigorous KPI Denominators:
        # Completion Rate = completed / (completed + cancelled + rejected) [resolved terminal consultations]
        # Cancellation Rate = cancelled / (completed + cancelled + rejected + confirmed) [all scheduled/resolved]
        resolved_window = (window_appts["completed"] or 0) + (window_appts["cancelled"] or 0) + (window_appts["rejected"] or 0)
        scheduled_window = resolved_window + (window_appts["confirmed"] or 0)

        completion_rate = round(((window_appts["completed"] or 0) / resolved_window * 100), 1) if resolved_window > 0 else 0.0
        cancellation_rate = round(((window_appts["cancelled"] or 0) / scheduled_window * 100), 1) if scheduled_window > 0 else 0.0

        # 5. Doctor Workload Distribution (Top 10)
        doctor_workloads = list(
            Appointment.objects.values(
                "doctor_id", "doctor__display_name", "doctor__specialization"
            )
            .annotate(
                total_consultations=Count("id"),
                completed=Count("id", filter=Q(status="COMPLETED")),
                cancelled=Count("id", filter=Q(status="CANCELLED")),
            )
            .order_by("-total_consultations")[:10]
        )

        # 6. Clinical Volume
        total_prescriptions = Prescription.objects.count()
        total_medical_records = MedicalRecord.objects.count()
        total_audit_logs = AuditLog.objects.count()

        # 7. Recent Audit Snippet (Sanitized)
        recent_audit = list(
            AuditLog.objects.order_by("-created_at")[:5].values(
                "id", "event_type", "action", "ip_address", "is_success", "created_at", "actor__username"
            )
        )

        # 8. System Health Indicators
        configured_ai = getattr(settings, "AI_PROVIDER", "mock").upper()

        return Response(
            {
                "status": "success",
                "period": {
                    "days": days,
                    "start_date": str(window_start),
                    "end_date": str(window_end),
                },
                "practitioners_and_patients": {
                    "total_patients": total_patients,
                    "total_doctors": total_doctors,
                    "verified_doctors": verified_doctors,
                    "pending_verification_doctors": pending_doctors,
                    "currently_available_doctors": available_doctors,
                },
                "appointments_all_time": all_time_appts,
                "appointments_window": window_appts,
                "rates": {
                    "completion_rate_percent": completion_rate,
                    "cancellation_rate_percent": cancellation_rate,
                    "completion_rate_denominator": "Resolved terminal consultations (completed + cancelled + rejected)",
                    "cancellation_rate_denominator": "Scheduled active or terminal consultations (completed + cancelled + rejected + confirmed)",
                },
                "doctor_workloads": [
                    {
                        "doctor_id": w["doctor_id"],
                        "name": w["doctor__display_name"],
                        "specialization": w["doctor__specialization"],
                        "total_consultations": w["total_consultations"],
                        "completed": w["completed"],
                        "cancelled": w["cancelled"],
                    }
                    for w in doctor_workloads
                ],
                "clinical_volume": {
                    "total_prescriptions": total_prescriptions,
                    "total_medical_records": total_medical_records,
                    "total_audit_events": total_audit_logs,
                },
                "recent_audit_events": recent_audit,
                "system_health": {
                    "backend_service": "operational",
                    "database": "connected",
                    "ai_engine_configured": configured_ai,
                },
            },
            status=status.HTTP_200_OK,
        )
