from datetime import datetime
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.accounts.permissions import IsVerifiedDoctorOrAdmin
from apps.common.serializers import APIErrorResponseSerializer
from apps.doctors.models import DoctorProfile
from .models import Appointment
from .serializers import (
    AppointmentActionResponseSerializer,
    AppointmentBookingSerializer,
    AppointmentCancelSerializer,
    AppointmentRejectSerializer,
    AppointmentSerializer,
    DoctorDailyScheduleResponseSerializer,
)
from .services import (
    cancel_appointment,
    complete_appointment,
    confirm_appointment,
    create_appointment,
    reject_appointment,
)


class AppointmentListCreateView(generics.ListCreateAPIView):
    """
    List appointments or book a new appointment.
    Patients view only their own appointments; Doctors view only their consultations;
    Administrators view all appointments.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN" or user.is_superuser:
            qs = Appointment.objects.all()
        elif user.role == "DOCTOR":
            qs = Appointment.objects.filter(doctor__user=user)
        else:
            qs = Appointment.objects.filter(patient__user=user)

        qs = qs.select_related("doctor", "doctor__user", "patient", "patient__user", "cancelled_by")

        # Filters
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status__iexact=status_param)

        date_param = self.request.query_params.get("date")
        if date_param:
            try:
                parsed_date = datetime.strptime(date_param, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError({"date": "Date format must be YYYY-MM-DD."})
            qs = qs.filter(appointment_date=parsed_date)

        doctor_id = self.request.query_params.get("doctor_id")
        if doctor_id:
            try:
                parsed_doctor_id = int(doctor_id)
            except (TypeError, ValueError):
                raise ValidationError({"doctor_id": "doctor_id must be a valid integer."})
            qs = qs.filter(doctor_id=parsed_doctor_id)

        return qs

    @extend_schema(
        tags=["Appointments"],
        summary="List Appointments",
        parameters=[
            OpenApiParameter(name="status", description="Filter by status (PENDING, CONFIRMED, etc.)", required=False, type=str),
            OpenApiParameter(name="date", description="Filter by appointment date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="doctor_id", description="Filter by doctor ID", required=False, type=int),
        ],
        responses={200: AppointmentSerializer(many=True), 400: APIErrorResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Appointments"],
        summary="Book a New Appointment",
        request=AppointmentBookingSerializer,
        responses={201: AppointmentActionResponseSerializer, 400: APIErrorResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = AppointmentBookingSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            appointment = create_appointment(
                patient=data["patient"],
                doctor=data["doctor"],
                appointment_date=data["appointment_date"],
                start_time=data["start_time"],
                duration_minutes=data["duration_minutes"],
                reason=data["reason"],
                actor=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages if hasattr(exc, "messages") else str(exc))

        return Response(
            {
                "status": "success",
                "message": "Appointment scheduled successfully.",
                "appointment": AppointmentSerializer(appointment).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AppointmentDetailView(generics.RetrieveAPIView):
    """
    Retrieve single appointment details.
    Accessible only to the appointment patient, assigned doctor, or administrator.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN" or user.is_superuser:
            qs = Appointment.objects.all()
        elif user.role == "DOCTOR":
            qs = Appointment.objects.filter(doctor__user=user)
        else:
            qs = Appointment.objects.filter(patient__user=user)
        return qs.select_related("doctor", "doctor__user", "patient", "patient__user", "cancelled_by")

    @extend_schema(tags=["Appointments"], summary="Get Appointment Details")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class _BaseAppointmentTransitionView(APIView):
    """Shared lookup and error handling for appointment lifecycle transitions."""
    permission_classes = [IsAuthenticated]

    def _run_transition(
        self,
        request,
        pk,
        service_fn,
        success_message: str,
        serializer_class=None,
        reason_field: str = "reason",
    ):
        try:
            appointment = Appointment.objects.select_related(
                "doctor", "doctor__user", "patient", "patient__user"
            ).get(pk=pk)
        except Appointment.DoesNotExist:
            return Response(
                {"status": "error", "error": {"code": "RESOURCE_NOT_FOUND", "message": "Appointment not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        service_kwargs = {}
        if serializer_class is not None:
            serializer = serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            service_kwargs["reason"] = serializer.validated_data.get(reason_field, "")

        try:
            updated = service_fn(appointment, actor=request.user, request=request, **service_kwargs)
        except PermissionDenied as e:
            return Response(
                {"status": "error", "error": {"code": "PERMISSION_DENIED", "message": str(e)}},
                status=status.HTTP_403_FORBIDDEN,
            )
        except DjangoValidationError as e:
            return Response(
                {"status": "error", "error": {"code": "INVALID_STATE", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"status": "success", "message": success_message, "appointment": AppointmentSerializer(updated).data},
            status=status.HTTP_200_OK,
        )


class AppointmentConfirmView(_BaseAppointmentTransitionView):
    """
    Doctor or Administrator confirms a PENDING appointment.
    """

    @extend_schema(
        tags=["Appointments"],
        summary="Confirm Appointment",
        request=None,
        responses={
            200: AppointmentActionResponseSerializer,
            400: APIErrorResponseSerializer,
            403: APIErrorResponseSerializer,
            404: APIErrorResponseSerializer,
        },
    )
    def post(self, request, pk):
        return self._run_transition(request, pk, confirm_appointment, "Appointment confirmed.")


class AppointmentRejectView(_BaseAppointmentTransitionView):
    """
    Doctor or Administrator rejects a PENDING appointment.
    """

    @extend_schema(
        tags=["Appointments"],
        summary="Reject Appointment",
        request=AppointmentRejectSerializer,
        responses={
            200: AppointmentActionResponseSerializer,
            400: APIErrorResponseSerializer,
            403: APIErrorResponseSerializer,
            404: APIErrorResponseSerializer,
        },
    )
    def post(self, request, pk):
        return self._run_transition(
            request,
            pk,
            reject_appointment,
            "Appointment rejected.",
            serializer_class=AppointmentRejectSerializer,
            reason_field="reason",
        )


class AppointmentCancelView(_BaseAppointmentTransitionView):
    """
    Patient, Assigned Doctor, or Administrator cancels an appointment.
    """

    @extend_schema(
        tags=["Appointments"],
        summary="Cancel Appointment",
        request=AppointmentCancelSerializer,
        responses={
            200: AppointmentActionResponseSerializer,
            400: APIErrorResponseSerializer,
            403: APIErrorResponseSerializer,
            404: APIErrorResponseSerializer,
        },
    )
    def post(self, request, pk):
        return self._run_transition(
            request,
            pk,
            cancel_appointment,
            "Appointment cancelled.",
            serializer_class=AppointmentCancelSerializer,
            reason_field="cancellation_reason",
        )


class AppointmentCompleteView(_BaseAppointmentTransitionView):
    """
    Assigned Doctor or Administrator marks a CONFIRMED consultation as completed.
    """

    @extend_schema(
        tags=["Appointments"],
        summary="Complete Appointment",
        request=None,
        responses={
            200: AppointmentActionResponseSerializer,
            400: APIErrorResponseSerializer,
            403: APIErrorResponseSerializer,
            404: APIErrorResponseSerializer,
        },
    )
    def post(self, request, pk):
        return self._run_transition(request, pk, complete_appointment, "Appointment marked as completed.")


class DoctorDailyScheduleView(APIView):
    """
    Daily schedule view for healthcare practitioners.
    Groups today's or selected date's consultations by time slot and provides daily KPIs.
    """
    permission_classes = [IsVerifiedDoctorOrAdmin]

    @extend_schema(
        tags=["Appointments"],
        summary="Get Doctor Daily Schedule",
        parameters=[
            OpenApiParameter(name="date", description="Target schedule date (YYYY-MM-DD, defaults to today)", required=False, type=str),
            OpenApiParameter(name="doctor_id", description="Doctor ID (Admin only)", required=False, type=int),
        ],
        responses={
            200: DoctorDailyScheduleResponseSerializer,
            400: APIErrorResponseSerializer,
            403: APIErrorResponseSerializer,
            404: APIErrorResponseSerializer,
        },
    )
    def get(self, request):
        target_date_str = request.query_params.get("date")
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"status": "error", "error": {"code": "INVALID_DATE", "message": "Date format must be YYYY-MM-DD."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = timezone.now().date()

        if request.user.role == "DOCTOR":
            if not hasattr(request.user, "doctor_profile"):
                return Response(
                    {"status": "error", "error": {"code": "PROFILE_MISSING", "message": "Doctor profile not found."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            doctor = request.user.doctor_profile
        else:
            doctor_id = request.query_params.get("doctor_id")
            if doctor_id:
                try:
                    parsed_doctor_id = int(doctor_id)
                except (TypeError, ValueError):
                    return Response(
                        {"status": "error", "error": {"code": "VALIDATION_ERROR", "message": "doctor_id must be a valid integer."}},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                try:
                    doctor = DoctorProfile.objects.get(pk=parsed_doctor_id)
                except DoctorProfile.DoesNotExist:
                    return Response(
                        {"status": "error", "error": {"code": "RESOURCE_NOT_FOUND", "message": "Doctor not found."}},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                return Response(
                    {"status": "error", "error": {"code": "MISSING_PARAM", "message": "doctor_id parameter is required for administrator requests."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=target_date,
        ).select_related("patient", "patient__user").order_by("start_time")

        slot_list = []
        counts = {"PENDING": 0, "CONFIRMED": 0, "COMPLETED": 0, "CANCELLED": 0, "REJECTED": 0}

        for appt in appointments:
            if appt.status in counts:
                counts[appt.status] += 1
            slot_list.append({
                "id": appt.id,
                "start_time": str(appt.start_time),
                "end_time": str(appt.end_time),
                "duration_minutes": appt.duration_minutes,
                "status": appt.status,
                "patient": {
                    "id": appt.patient.id,
                    "name": appt.patient.user.get_full_name() or appt.patient.user.username,
                    "gender": appt.patient.get_gender_display(),
                    "phone": appt.patient.user.phone_number,
                },
                "reason": appt.reason,
                "cancellation_reason": appt.cancellation_reason,
            })

        return Response(
            {
                "status": "success",
                "date": str(target_date),
                "doctor": {
                    "id": doctor.id,
                    "name": doctor.display_name,
                    "working_hours": f"{doctor.working_hours_start} - {doctor.working_hours_end}",
                },
                "kpis": {
                    "total_slots": len(slot_list),
                    **counts,
                },
                "schedule": slot_list,
            },
            status=status.HTTP_200_OK,
        )
