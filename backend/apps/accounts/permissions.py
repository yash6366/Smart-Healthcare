from rest_framework.permissions import BasePermission
from .models import User


class IsPatient(BasePermission):
    """
    Allows access only to authenticated patients.
    """
    message = "Access restricted to registered patients."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == User.Role.PATIENT
        )


class IsDoctor(BasePermission):
    """
    Allows access only to authenticated doctors.
    """
    message = "Access restricted to authorized healthcare practitioners."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == User.Role.DOCTOR
        )


class IsAdministrator(BasePermission):
    """
    Allows access only to platform administrators.
    """
    message = "Access restricted to platform administrators."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and (
                request.user.role == User.Role.ADMIN
                or request.user.is_staff
                or request.user.is_superuser
            )
        )


class IsDoctorOrAdmin(BasePermission):
    """
    Allows access to doctors or administrators.
    """
    message = "Access restricted to healthcare professionals and administrators."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and (
                request.user.role in (User.Role.DOCTOR, User.Role.ADMIN)
                or request.user.is_staff
                or request.user.is_superuser
            )
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission allowing access to object owner or administrator.
    """
    message = "You do not have permission to access or modify this resource."

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False

        if request.user.role == User.Role.ADMIN or request.user.is_superuser:
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "recipient"):
            return obj.recipient == request.user
        if hasattr(obj, "patient") and hasattr(obj.patient, "user"):
            return obj.patient.user == request.user

        return obj == request.user
