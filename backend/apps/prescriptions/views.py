from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import Prescription
from .serializers import PrescriptionCreateSerializer, PrescriptionSerializer
from apps.notifications.services import send_notification
from apps.notifications.models import Notification
from apps.audit.services import log_audit_event


class PrescriptionListCreateView(generics.ListCreateAPIView):
    """
    List prescriptions or issue a new prescription.
    Only authorized medical doctors can issue prescriptions.
    Patients cannot create or modify prescriptions.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PrescriptionCreateSerializer
        return PrescriptionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN" or user.is_superuser:
            qs = Prescription.objects.all()
        elif user.role == "DOCTOR":
            qs = Prescription.objects.filter(doctor__user=user)
        else:
            qs = Prescription.objects.filter(patient__user=user)

        qs = qs.select_related("patient", "patient__user", "doctor", "doctor__user", "appointment").prefetch_related("items")

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status__iexact=status_param)

        return qs

    @extend_schema(
        tags=["Prescriptions"],
        summary="List Prescriptions",
        parameters=[
            OpenApiParameter(name="status", description="Filter by status (ACTIVE, COMPLETED, CANCELLED)", required=False, type=str),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Prescriptions"],
        summary="Issue New Prescription (Doctor Only)",
        request=PrescriptionCreateSerializer,
        responses={201: PrescriptionSerializer},
    )
    def post(self, request, *args, **kwargs):
        if request.user.role != "DOCTOR" or not hasattr(request.user, "doctor_profile"):
            raise PermissionDenied("Only registered and verified medical doctors can issue prescriptions.")

        doctor = request.user.doctor_profile
        if not doctor.is_verified:
            raise PermissionDenied("Unverified doctors are not permitted to issue prescriptions.")

        serializer = PrescriptionCreateSerializer(data=request.data, context={"doctor": doctor, "request": request})
        serializer.is_valid(raise_exception=True)
        prescription = serializer.save()

        # Notify Patient
        send_notification(
            recipient=prescription.patient.user,
            notification_type=Notification.NotificationType.PRESCRIPTION_ISSUED,
            title="New Prescription Issued",
            message=f"Dr. {doctor.display_name} has issued a new prescription for your consultation.",
            data={"prescription_id": prescription.id},
        )

        # Audit Log
        log_audit_event(
            event_type="PRESCRIPTION_ISSUED",
            actor=request.user,
            resource_type="Prescription",
            resource_id=str(prescription.id),
            action="ISSUE_PRESCRIPTION",
            details={"patient_id": prescription.patient_id, "items_count": prescription.items.count()},
            is_success=True,
            request=request,
        )

        return Response(
            {
                "status": "success",
                "message": "Prescription issued successfully.",
                "prescription": PrescriptionSerializer(prescription).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PrescriptionDetailView(generics.RetrieveAPIView):
    """
    Retrieve single prescription details with items.
    Accessible to patient owner, issuing doctor, or administrator.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PrescriptionSerializer
    queryset = Prescription.objects.all().select_related(
        "patient", "patient__user", "doctor", "doctor__user", "appointment"
    ).prefetch_related("items")

    def get_object(self):
        prescription = super().get_object()
        user = self.request.user

        is_patient_owner = hasattr(user, "patient_profile") and prescription.patient_id == user.patient_profile.id
        is_issuing_doctor = hasattr(user, "doctor_profile") and prescription.doctor_id == user.doctor_profile.id
        is_admin = user.role == "ADMIN" or user.is_superuser

        if not (is_patient_owner or is_issuing_doctor or is_admin):
            raise NotFound("Prescription not found.")

        return prescription

    @extend_schema(tags=["Prescriptions"], summary="Get Prescription Detail")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
