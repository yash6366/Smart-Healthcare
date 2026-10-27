from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import DoctorProfile
from .serializers import (
    DoctorAdminCreateSerializer,
    DoctorDetailSerializer,
    DoctorPublicSerializer,
    DoctorVerifySerializer,
)
from apps.accounts.permissions import IsAdministrator, IsDoctor
from apps.audit.services import log_audit_event


class DoctorListView(generics.ListCreateAPIView):
    """
    List verified and active doctors for public directory search.
    Administrators can POST to provision new doctor accounts.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdministrator()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DoctorAdminCreateSerializer
        return DoctorPublicSerializer

    def get_queryset(self):
        # Admins can see all doctors (including unverified)
        user = self.request.user
        if user.is_authenticated and (user.role == "ADMIN" or user.is_superuser):
            qs = DoctorProfile.objects.all().select_related("user")
        else:
            # Public and patients only see verified and active doctors
            qs = DoctorProfile.objects.filter(is_verified=True, is_available=True).select_related("user")

        # Filters
        specialization = self.request.query_params.get("specialization")
        if specialization:
            qs = qs.filter(specialization__iexact=specialization)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(display_name__icontains=search) | qs.filter(qualifications__icontains=search)

        max_fee = self.request.query_params.get("max_fee")
        if max_fee:
            try:
                qs = qs.filter(consultation_fee__lte=float(max_fee))
            except ValueError:
                pass

        ordering = self.request.query_params.get("ordering")
        if ordering in ["consultation_fee", "-consultation_fee", "years_of_experience", "-years_of_experience"]:
            qs = qs.order_by(ordering)

        return qs

    @extend_schema(
        tags=["Doctors"],
        summary="List Verified Doctors with Search & Specialization Filters",
        parameters=[
            OpenApiParameter(name="specialization", description="Filter by doctor specialization", required=False, type=str),
            OpenApiParameter(name="search", description="Search by doctor name or qualification", required=False, type=str),
            OpenApiParameter(name="max_fee", description="Filter by maximum consultation fee", required=False, type=float),
            OpenApiParameter(name="ordering", description="Order by consultation_fee or years_of_experience", required=False, type=str),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Doctors"],
        summary="Provision New Doctor Account (Admin Only)",
        request=DoctorAdminCreateSerializer,
        responses={201: DoctorDetailSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = DoctorAdminCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()

        log_audit_event(
            event_type="ADMIN_ACTION",
            actor=request.user,
            resource_type="DoctorProfile",
            resource_id=str(doctor.id),
            action="PROVISION_DOCTOR",
            details={"username": doctor.user.username, "specialization": doctor.specialization},
            is_success=True,
            request=request,
        )

        return Response(
            {
                "status": "success",
                "message": "Doctor account provisioned successfully.",
                "doctor": DoctorDetailSerializer(doctor).data,
            },
            status=status.HTTP_201_CREATED,
        )


class DoctorDetailView(generics.RetrieveAPIView):
    """
    Retrieve single doctor profile details.
    """
    permission_classes = [AllowAny]
    queryset = DoctorProfile.objects.all().select_related("user")

    def get_serializer_class(self):
        user = self.request.user
        # Admins or doctor viewing their own profile see full detail
        if user.is_authenticated and (user.role == "ADMIN" or user.is_superuser or (hasattr(user, "doctor_profile") and user.doctor_profile.id == self.kwargs.get("pk"))):
            return DoctorDetailSerializer
        return DoctorPublicSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and (user.role == "ADMIN" or user.is_superuser or (hasattr(user, "doctor_profile") and user.doctor_profile.id == self.kwargs.get("pk"))):
            return DoctorProfile.objects.all().select_related("user")
        return DoctorProfile.objects.filter(is_verified=True).select_related("user")

    @extend_schema(tags=["Doctors"], summary="Get Doctor Profile Details")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DoctorMeView(generics.RetrieveUpdateAPIView):
    """
    Doctor's own profile self-management.
    Allows updating biography, consultation fee, working hours, and active availability.
    Doctors cannot modify their own verification status.
    """
    permission_classes = [IsDoctor]
    serializer_class = DoctorDetailSerializer

    def get_object(self):
        return self.request.user.doctor_profile

    @extend_schema(tags=["Doctors"], summary="Get Current Doctor Profile")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["Doctors"], summary="Update Current Doctor Profile")
    def patch(self, request, *args, **kwargs):
        response = super().patch(request, *args, **kwargs)
        log_audit_event(
            event_type="DOCTOR_AVAILABILITY",
            actor=request.user,
            resource_type="DoctorProfile",
            resource_id=str(self.request.user.doctor_profile.id),
            action="UPDATE_PROFILE",
            details={"is_available": self.request.user.doctor_profile.is_available},
            is_success=True,
            request=request,
        )
        return response


class DoctorVerifyView(APIView):
    """
    Administrative endpoint to approve or revoke doctor verification.
    """
    permission_classes = [IsAdministrator]

    @extend_schema(
        tags=["Doctors"],
        summary="Verify or Revoke Doctor Status (Admin Only)",
        request=DoctorVerifySerializer,
        responses={200: DoctorDetailSerializer},
    )
    def post(self, request, pk):
        try:
            doctor = DoctorProfile.objects.select_related("user").get(pk=pk)
        except DoctorProfile.DoesNotExist:
            return Response(
                {"status": "error", "error": {"code": "RESOURCE_NOT_FOUND", "message": "Doctor not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DoctorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_verified = serializer.validated_data["is_verified"]
        notes = serializer.validated_data.get("notes", "")

        doctor.is_verified = is_verified
        doctor.user.is_verified = is_verified
        doctor.save()
        doctor.user.save()

        log_audit_event(
            event_type="DOCTOR_VERIFIED",
            actor=request.user,
            resource_type="DoctorProfile",
            resource_id=str(doctor.id),
            action="VERIFY_DOCTOR" if is_verified else "REVOKE_DOCTOR",
            details={"is_verified": is_verified, "notes": notes},
            is_success=True,
            request=request,
        )

        return Response(
            {
                "status": "success",
                "message": f"Doctor verification status updated to {is_verified}.",
                "doctor": DoctorDetailSerializer(doctor).data,
            },
            status=status.HTTP_200_OK,
        )
