from django.db.models import Exists, OuterRef, Q
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer

from .models import MedicalRecord
from .serializers import MedicalRecordCreateSerializer, MedicalRecordSerializer
from apps.appointments.models import Appointment
from apps.audit.services import log_audit_event
from apps.common.serializers import APIErrorResponseSerializer


class MedicalRecordListCreateView(generics.ListCreateAPIView):
    """
    List medical records for authorized users or create a new clinical note (Doctors/Admins).
    Patients can strictly see only their own medical history.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return MedicalRecordCreateSerializer
        return MedicalRecordSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN" or user.is_superuser:
            qs = MedicalRecord.objects.all()
        elif user.role == "DOCTOR":
            doctor = getattr(user, "doctor_profile", None)
            if not doctor or not doctor.is_verified:
                raise PermissionDenied("Only verified doctors can access medical records.")
            # Doctor can see records they authored or for patients who booked with them
            treating_patient = Appointment.objects.filter(
                patient_id=OuterRef("patient_id"),
                doctor__user=user,
            )
            qs = MedicalRecord.objects.filter(
                Q(doctor__user=user) | Exists(treating_patient)
            )
        else:
            qs = MedicalRecord.objects.filter(patient__user=user)

        qs = qs.select_related("patient", "patient__user", "doctor")

        record_type = self.request.query_params.get("record_type")
        if record_type:
            qs = qs.filter(record_type=record_type)

        patient_id = self.request.query_params.get("patient_id")
        if patient_id and (user.role in ("DOCTOR", "ADMIN") or user.is_superuser):
            try:
                parsed_patient_id = int(patient_id)
            except (TypeError, ValueError):
                raise ValidationError({"patient_id": "patient_id must be a valid integer."})
            qs = qs.filter(patient_id=parsed_patient_id)

        return qs

    @extend_schema(
        tags=["Medical Records"],
        summary="List Medical Records",
        parameters=[
            OpenApiParameter(name="record_type", description="Filter by record type", required=False, type=str),
            OpenApiParameter(name="patient_id", description="Filter by patient ID (Doctors/Admins)", required=False, type=int),
        ],
        responses={200: MedicalRecordSerializer(many=True), 400: APIErrorResponseSerializer, 403: APIErrorResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Medical Records"],
        summary="Create Medical Record (Doctor or Admin Only)",
        request=MedicalRecordCreateSerializer,
        responses={
            201: inline_serializer(
                name="MedicalRecordCreateEnvelopeResponse",
                fields={
                    "status": serializers.CharField(default="success"),
                    "message": serializers.CharField(),
                    "record": MedicalRecordSerializer(),
                },
            ),
            400: APIErrorResponseSerializer,
            403: APIErrorResponseSerializer,
        },
    )
    def post(self, request, *args, **kwargs):
        if not (request.user.role in ("DOCTOR", "ADMIN") or request.user.is_superuser):
            raise PermissionDenied("Only doctors or platform administrators can create medical records.")

        serializer = MedicalRecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        doctor = getattr(request.user, "doctor_profile", None)
        if request.user.role == "DOCTOR":
            if not doctor or not doctor.is_verified:
                raise PermissionDenied("Only verified doctors can record medical notes.")

        record = MedicalRecord.objects.create(
            patient=data["patient_id"],
            doctor=doctor,
            record_type=data["record_type"],
            title=data["title"],
            description=data["description"],
            clinical_data=data.get("clinical_data", {}),
        )

        log_audit_event(
            event_type="MEDICAL_RECORD_CREATED",
            actor=request.user,
            resource_type="MedicalRecord",
            resource_id=str(record.id),
            action="CREATE_RECORD",
            details={"patient_id": record.patient_id, "record_type": record.record_type},
            is_success=True,
            request=request,
        )

        return Response(
            {
                "status": "success",
                "message": "Medical record recorded successfully.",
                "record": MedicalRecordSerializer(record).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MedicalRecordDetailView(generics.RetrieveAPIView):
    """
    Retrieve single medical record.
    Access is audited for compliance and restricted to the patient, authoring doctor, treating doctor, or admin.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MedicalRecordSerializer
    queryset = MedicalRecord.objects.all().select_related("patient", "patient__user", "doctor")

    def get_object(self):
        record = super().get_object()
        user = self.request.user

        # Access check
        is_patient_owner = hasattr(user, "patient_profile") and record.patient_id == user.patient_profile.id
        is_doctor_author = hasattr(user, "doctor_profile") and record.doctor_id == user.doctor_profile.id
        is_treating_doctor = (
            hasattr(user, "doctor_profile")
            and record.patient.appointments.filter(doctor=user.doctor_profile).exists()
        )
        is_admin = user.role == "ADMIN" or user.is_superuser

        if not (is_patient_owner or is_doctor_author or is_treating_doctor or is_admin):
            # Avoid leaking whether record exists
            raise NotFound("Medical record not found.")

        # Log sensitive access event
        log_audit_event(
            event_type="MEDICAL_RECORD_ACCESSED",
            actor=user,
            resource_type="MedicalRecord",
            resource_id=str(record.id),
            action="VIEW_RECORD",
            details={"patient_id": record.patient_id},
            is_success=True,
            request=self.request,
        )

        return record

    @extend_schema(tags=["Medical Records"], summary="Get Medical Record Detail (Audited)")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
