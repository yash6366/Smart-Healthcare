from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import Appointment
from .serializers import (
    AppointmentBookingSerializer,
    AppointmentCancelSerializer,
    AppointmentRejectSerializer,
    AppointmentSerializer,
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
            qs = qs.filter(appointment_date=date_param)

        doctor_id = self.request.query_params.get("doctor_id")
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)

        return qs

    @extend_schema(
        tags=["Appointments"],
        summary="List Appointments",
        parameters=[
            OpenApiParameter(name="status", description="Filter by status (PENDING, CONFIRMED, etc.)", required=False, type=str),
            OpenApiParameter(name="date", description="Filter by appointment date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="doctor_id", description="Filter by doctor ID", required=False, type=int),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Appointments"],
        summary="Book a New Appointment",
        request=AppointmentBookingSerializer,
        responses={201: AppointmentSerializer},
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
            return Appointment.objects.all()
        if user.role == "DOCTOR":
            return Appointment.objects.filter(doctor__user=user)
        return Appointment.objects.filter(patient__user=user)

    @extend_schema(tags=["Appointments"], summary="Get Appointment Details")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AppointmentConfirmView(APIView):
    """
    Doctor or Administrator confirms a PENDING appointment.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Appointments"],
        summary="Confirm Appointment",
        request=None,
        responses={200: AppointmentSerializer},
    )
    def post(self, request, pk):
        try:
            appointment = Appointment.objects.select_related("doctor", "patient", "patient__user").get(pk=pk)
        except Appointment.DoesNotExist:
            return Response(
                {"status": "error", "error": {"code": "RESOURCE_NOT_FOUND", "message": "Appointment not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            confirmed = confirm_appointment(appointment, actor=request.user, request=request)
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
            {"status": "success", "message": "Appointment confirmed.", "appointment": AppointmentSerializer(confirmed).data},
            status=status.HTTP_200_OK,
        )


class AppointmentRejectView(APIView):
    """
    Doctor or Administrator rejects a PENDING appointment.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Appointments"],
        summary="Reject Appointment",
        request=AppointmentRejectSerializer,
        responses={200: AppointmentSerializer},
    )
    def post(self, request, pk):
        try:
            appointment = Appointment.objects.select_related("doctor", "patient", "patient__user").get(pk=pk)
        except Appointment.DoesNotExist:
            return Response(
                {"status": "error", "error": {"code": "RESOURCE_NOT_FOUND", "message": "Appointment not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AppointmentRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        try:
            rejected = reject_appointment(appointment, actor=request.user, reason=reason, request=request)
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
            {"status": "success", "message": "Appointment rejected.", "appointment": AppointmentSerializer(rejected).data},
            status=status.HTTP_200_OK,
        )


class AppointmentCancelView(APIView):
    """
    Patient, Assigned Doctor, or Administrator cancels an appointment.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Appointments"],
        summary="Cancel Appointment",
        request=AppointmentCancelSerializer,
        responses={200: AppointmentSerializer},
    )
    def post(self, request, pk):
        try:
            appointment = Appointment.objects.select_related("doctor", "patient", "patient__user", "doctor__user").get(pk=pk)
        except Appointment.DoesNotExist:
            return Response(
                {"status": "error", "error": {"code": "RESOURCE_NOT_FOUND", "message": "Appointment not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AppointmentCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("cancellation_reason", "")

        try:
            cancelled = cancel_appointment(appointment, actor=request.user, reason=reason, request=request)
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
            {"status": "success", "message": "Appointment cancelled.", "appointment": AppointmentSerializer(cancelled).data},
            status=status.HTTP_200_OK,
        )


class AppointmentCompleteView(APIView):
    """
    Assigned Doctor or Administrator marks a CONFIRMED consultation as completed.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Appointments"],
        summary="Complete Appointment",
        request=None,
        responses={200: AppointmentSerializer},
    )
    def post(self, request, pk):
        try:
            appointment = Appointment.objects.select_related("doctor", "patient", "patient__user").get(pk=pk)
        except Appointment.DoesNotExist:
            return Response(
                {"status": "error", "error": {"code": "RESOURCE_NOT_FOUND", "message": "Appointment not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            completed = complete_appointment(appointment, actor=request.user, request=request)
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
            {"status": "success", "message": "Appointment marked as completed.", "appointment": AppointmentSerializer(completed).data},
            status=status.HTTP_200_OK,
        )


class DoctorDailyScheduleView(APIView):
    """
    Daily schedule view for healthcare practitioners.
    Groups today's or selected date's consultations by time slot and provides daily KPIs.
    """
    from apps.accounts.permissions import IsDoctorOrAdmin
    permission_classes = [IsDoctorOrAdmin]

    @extend_schema(
        tags=["Appointments"],
        summary="Get Doctor Daily Schedule",
        parameters=[
            OpenApiParameter(name="date", description="Target schedule date (YYYY-MM-DD, defaults to today)", required=False, type=str),
            OpenApiParameter(name="doctor_id", description="Doctor ID (Admin only)", required=False, type=int),
        ],
    )
    def get(self, request):
        from django.utils import timezone
        target_date_str = request.query_params.get("date")
        if target_date_str:
            try:
                from datetime import datetime
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
                    from apps.doctors.models import DoctorProfile
                    doctor = DoctorProfile.objects.get(pk=doctor_id)
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
