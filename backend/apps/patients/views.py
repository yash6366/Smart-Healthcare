from datetime import datetime
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, NotFound
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import PatientProfile
from .serializers import PatientProfileSerializer
from apps.accounts.permissions import IsDoctorOrAdmin, IsPatient, IsOwnerOrAdmin
from apps.appointments.models import Appointment
from apps.medical_records.models import MedicalRecord
from apps.prescriptions.models import Prescription


class PatientMeView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update the currently authenticated patient's profile.
    """
    permission_classes = [IsPatient]
    serializer_class = PatientProfileSerializer

    def get_object(self):
        # Automatically get or create profile if user is a patient
        profile, _ = PatientProfile.objects.get_or_create(user=self.request.user)
        return profile

    @extend_schema(tags=["Patients"], summary="Get Current Patient Profile")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["Patients"], summary="Update Current Patient Profile")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class PatientListView(generics.ListAPIView):
    """
    List patient profiles. Accessible by authorized healthcare staff and platform administrators.
    """
    permission_classes = [IsDoctorOrAdmin]
    serializer_class = PatientProfileSerializer
    queryset = PatientProfile.objects.all().select_related("user")

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                user__first_name__icontains=search
            ) | qs.filter(
                user__last_name__icontains=search
            ) | qs.filter(
                user__email__icontains=search
            )
        return qs

    @extend_schema(tags=["Patients"], summary="List Patients (Staff/Admin Only)")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PatientDetailView(generics.RetrieveAPIView):
    """
    Retrieve patient profile details.
    Accessible to the patient themselves, authorized healthcare practitioners, and administrators.
    """
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = PatientProfileSerializer
    queryset = PatientProfile.objects.all().select_related("user")

    @extend_schema(tags=["Patients"], summary="Get Patient Detail")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PatientHealthTimelineView(APIView):
    """
    Aggregated chronological health timeline for the authenticated patient.
    Unifies consultations, electronic medical records, and prescribed medications.
    """
    permission_classes = [IsPatient]

    @extend_schema(
        tags=["Patients"],
        summary="Get Patient Health Timeline",
        parameters=[
            OpenApiParameter(name="start_date", description="Filter events on or after YYYY-MM-DD", required=False, type=str),
            OpenApiParameter(name="end_date", description="Filter events on or before YYYY-MM-DD", required=False, type=str),
            OpenApiParameter(name="event_type", description="Filter by event type (APPOINTMENT, MEDICAL_RECORD, PRESCRIPTION, or ALL)", required=False, type=str),
            OpenApiParameter(name="limit", description="Max events to return (default: 50)", required=False, type=int),
        ],
    )
    def get(self, request):
        patient, _ = PatientProfile.objects.get_or_create(user=request.user)
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        event_filter = request.query_params.get("event_type", "ALL").upper()
        limit = min(int(request.query_params.get("limit", 50)), 200)

        events = []

        # 1. Appointments
        if event_filter in ("ALL", "APPOINTMENT"):
            appt_qs = Appointment.objects.filter(patient=patient).select_related("doctor", "doctor__user")
            if start_date:
                appt_qs = appt_qs.filter(appointment_date__gte=start_date)
            if end_date:
                appt_qs = appt_qs.filter(appointment_date__lte=end_date)

            for appt in appt_qs:
                appt_dt = timezone.make_aware(datetime.combine(appt.appointment_date, appt.start_time))
                events.append({
                    "event_type": "APPOINTMENT",
                    "event_id": appt.id,
                    "timestamp": appt_dt.isoformat(),
                    "title": f"Consultation with Dr. {appt.doctor.display_name}",
                    "subtitle": appt.doctor.get_specialization_display(),
                    "status": appt.status,
                    "doctor_name": appt.doctor.display_name,
                    "details": {
                        "date": str(appt.appointment_date),
                        "time": str(appt.start_time),
                        "duration_minutes": appt.duration_minutes,
                        "reason": appt.reason,
                        "status": appt.status,
                        "cancellation_reason": appt.cancellation_reason,
                    },
                })

        # 2. Medical Records
        if event_filter in ("ALL", "MEDICAL_RECORD"):
            rec_qs = MedicalRecord.objects.filter(patient=patient).select_related("doctor")
            if start_date:
                rec_qs = rec_qs.filter(created_at__date__gte=start_date)
            if end_date:
                rec_qs = rec_qs.filter(created_at__date__lte=end_date)

            for rec in rec_qs:
                events.append({
                    "event_type": "MEDICAL_RECORD",
                    "event_id": rec.id,
                    "timestamp": rec.created_at.isoformat(),
                    "title": rec.title,
                    "subtitle": rec.get_record_type_display(),
                    "status": "RECORDED",
                    "doctor_name": rec.doctor.display_name if rec.doctor else "Hospital Clinical Staff",
                    "details": {
                        "record_type": rec.record_type,
                        "description": rec.description,
                        "clinical_data": rec.clinical_data,
                    },
                })

        # 3. Prescriptions
        if event_filter in ("ALL", "PRESCRIPTION"):
            rx_qs = Prescription.objects.filter(patient=patient).select_related("doctor").prefetch_related("items")
            if start_date:
                rx_qs = rx_qs.filter(issued_at__date__gte=start_date)
            if end_date:
                rx_qs = rx_qs.filter(issued_at__date__lte=end_date)

            for rx in rx_qs:
                events.append({
                    "event_type": "PRESCRIPTION",
                    "event_id": rx.id,
                    "timestamp": rx.issued_at.isoformat(),
                    "title": f"Prescription: {rx.diagnosis}",
                    "subtitle": f"{rx.items.count()} medication(s) prescribed",
                    "status": rx.status,
                    "doctor_name": rx.doctor.display_name,
                    "details": {
                        "diagnosis": rx.diagnosis,
                        "status": rx.status,
                        "notes": rx.notes,
                        "medications": [
                            {
                                "name": item.medication_name,
                                "dosage": item.dosage,
                                "frequency": item.frequency,
                                "duration": item.duration,
                                "instructions": item.instructions,
                            }
                            for item in rx.items.all()
                        ],
                    },
                })

        # Sort descending by timestamp
        events.sort(key=lambda x: x["timestamp"], reverse=True)

        return Response(
            {
                "status": "success",
                "patient_id": patient.id,
                "total_events": len(events),
                "results": events[:limit],
            },
            status=status.HTTP_200_OK,
        )


class PatientClinicalHistoryView(APIView):
    """
    Authorized clinical history for a patient.
    Accessible only to doctors with a consultation relationship with this patient, or platform administrators.
    """
    permission_classes = [IsDoctorOrAdmin]

    @extend_schema(
        tags=["Patients"],
        summary="Get Patient Clinical History (Authorized Doctors/Admins)",
    )
    def get(self, request, pk):
        try:
            patient = PatientProfile.objects.select_related("user").get(pk=pk)
        except PatientProfile.DoesNotExist:
            raise NotFound("Patient profile not found.")

        # Relationship check for Doctors
        if request.user.role == "DOCTOR":
            doctor_profile = getattr(request.user, "doctor_profile", None)
            if not doctor_profile:
                raise PermissionDenied("Doctor profile not found.")

            has_relationship = Appointment.objects.filter(
                doctor=doctor_profile,
                patient=patient,
            ).exists()
            if not has_relationship:
                raise PermissionDenied(
                    "You are not authorized to view this patient's clinical history as no consultations exist between you and this patient."
                )

        records = MedicalRecord.objects.filter(patient=patient).select_related("doctor").order_by("-created_at")
        prescriptions = Prescription.objects.filter(patient=patient).select_related("doctor").prefetch_related("items").order_by("-issued_at")
        appointments = Appointment.objects.filter(patient=patient).select_related("doctor").order_by("-appointment_date", "-start_time")[:10]

        return Response(
            {
                "status": "success",
                "patient": {
                    "id": patient.id,
                    "full_name": patient.user.get_full_name() or patient.user.username,
                    "gender": patient.get_gender_display(),
                    "blood_group": patient.blood_group,
                    "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else None,
                    "emergency_contact": {
                        "name": patient.emergency_contact_name,
                        "phone": patient.emergency_contact_phone,
                        "relation": patient.emergency_contact_relation,
                    },
                },
                "medical_records": [
                    {
                        "id": r.id,
                        "record_type": r.record_type,
                        "title": r.title,
                        "description": r.description,
                        "clinical_data": r.clinical_data,
                        "doctor_name": r.doctor.display_name if r.doctor else "Hospital Staff",
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in records
                ],
                "prescriptions": [
                    {
                        "id": p.id,
                        "diagnosis": p.diagnosis,
                        "status": p.status,
                        "notes": p.notes,
                        "issued_at": p.issued_at.isoformat(),
                        "doctor_name": p.doctor.display_name,
                        "items": [
                            {
                                "name": item.medication_name,
                                "dosage": item.dosage,
                                "frequency": item.frequency,
                                "duration": item.duration,
                                "instructions": item.instructions,
                            }
                            for item in p.items.all()
                        ],
                    }
                    for p in prescriptions
                ],
                "recent_consultations": [
                    {
                        "id": a.id,
                        "date": str(a.appointment_date),
                        "start_time": str(a.start_time),
                        "status": a.status,
                        "reason": a.reason,
                        "doctor_name": a.doctor.display_name,
                    }
                    for a in appointments
                ],
            },
            status=status.HTTP_200_OK,
        )
