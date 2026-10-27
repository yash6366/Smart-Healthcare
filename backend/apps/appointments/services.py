from datetime import datetime, timedelta
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone

from .models import Appointment
from apps.doctors.models import DoctorProfile
from apps.patients.models import PatientProfile
from apps.notifications.services import send_notification
from apps.notifications.models import Notification
from apps.audit.services import log_audit_event


def create_appointment(
    patient: PatientProfile,
    doctor: DoctorProfile,
    appointment_date,
    start_time,
    duration_minutes: int,
    reason: str,
    actor=None,
    request=None,
) -> Appointment:
    """
    Atomically creates a new appointment with strict concurrency protection,
    working hours validation, past-date rejection, and slot conflict checks.
    """
    # 1. Reject past appointments
    current_time = timezone.now()
    appointment_datetime = timezone.make_aware(datetime.combine(appointment_date, start_time))
    if appointment_datetime <= current_time:
        raise ValidationError("Appointments cannot be scheduled for past dates or times.")

    # 2. Calculate end_time
    start_datetime = datetime.combine(appointment_date, start_time)
    end_datetime = start_datetime + timedelta(minutes=duration_minutes)
    end_time = end_datetime.time()

    # 3. Atomic transaction with locking for race-condition prevention
    with transaction.atomic():
        # Lock the doctor and patient rows to prevent concurrent double-booking
        locked_doctor = DoctorProfile.objects.select_for_update().get(id=doctor.id)
        locked_patient = PatientProfile.objects.select_for_update().get(id=patient.id)

        # 4. Validate doctor status & availability
        if not locked_doctor.is_verified:
            raise ValidationError("Appointments can only be booked with verified medical doctors.")
        if not locked_doctor.is_available:
            raise ValidationError("Doctor is currently not accepting new appointments.")

        # 5. Validate within working hours
        if start_time < locked_doctor.working_hours_start or end_time > locked_doctor.working_hours_end:
            raise ValidationError(
                f"Requested slot ({start_time} - {end_time}) falls outside doctor's working hours "
                f"({locked_doctor.working_hours_start} - {locked_doctor.working_hours_end})."
            )

        # 6. Check doctor schedule overlap
        doctor_conflicts = Appointment.objects.filter(
            doctor=locked_doctor,
            appointment_date=appointment_date,
            status__in=Appointment.ACTIVE_STATUSES,
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        if doctor_conflicts.exists():
            raise ValidationError("Doctor already has an active appointment scheduled during this time slot.")

        # 7. Check patient schedule overlap
        patient_conflicts = Appointment.objects.filter(
            patient=locked_patient,
            appointment_date=appointment_date,
            status__in=Appointment.ACTIVE_STATUSES,
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        if patient_conflicts.exists():
            raise ValidationError("Patient already has an active appointment scheduled during this time slot.")

        # 8. Create Appointment
        appointment = Appointment.objects.create(
            patient=locked_patient,
            doctor=locked_doctor,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            reason=reason,
            status=Appointment.Status.PENDING,
        )

        # 9. Send Notification to Doctor
        send_notification(
            recipient=locked_doctor.user,
            notification_type=Notification.NotificationType.APPOINTMENT_REQUESTED,
            title="New Appointment Requested",
            message=(
                f"Patient {locked_patient.user.get_full_name() or locked_patient.user.username} "
                f"has requested an appointment on {appointment_date} at {start_time}."
            ),
            data={"appointment_id": appointment.id},
        )

        # 10. Audit Log
        log_audit_event(
            event_type="APPOINTMENT_CREATED",
            actor=actor or locked_patient.user,
            resource_type="Appointment",
            resource_id=str(appointment.id),
            action="BOOK_APPOINTMENT",
            details={
                "doctor_id": locked_doctor.id,
                "patient_id": locked_patient.id,
                "date": str(appointment_date),
                "start_time": str(start_time),
            },
            is_success=True,
            request=request,
        )

        return appointment


def confirm_appointment(appointment: Appointment, actor, request=None) -> Appointment:
    """Doctor or Administrator confirms a pending appointment."""
    if appointment.status != Appointment.Status.PENDING:
        raise ValidationError(f"Cannot confirm an appointment with status '{appointment.status}'. Must be PENDING.")

    # Authorization
    is_assigned_doctor = hasattr(actor, "doctor_profile") and appointment.doctor_id == actor.doctor_profile.id
    is_admin = actor.role == "ADMIN" or actor.is_superuser
    if not (is_assigned_doctor or is_admin):
        raise PermissionDenied("Only the assigned doctor or an administrator can confirm this appointment.")

    with transaction.atomic():
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save(update_fields=["status", "updated_at"])

        send_notification(
            recipient=appointment.patient.user,
            notification_type=Notification.NotificationType.APPOINTMENT_CONFIRMED,
            title="Appointment Confirmed",
            message=f"Your appointment with Dr. {appointment.doctor.display_name} on {appointment.appointment_date} at {appointment.start_time} has been confirmed.",
            data={"appointment_id": appointment.id},
        )

        log_audit_event(
            event_type="APPOINTMENT_STATUS_CHANGE",
            actor=actor,
            resource_type="Appointment",
            resource_id=str(appointment.id),
            action="CONFIRM_APPOINTMENT",
            details={"new_status": Appointment.Status.CONFIRMED},
            is_success=True,
            request=request,
        )

    return appointment


def reject_appointment(appointment: Appointment, actor, reason: str = "", request=None) -> Appointment:
    """Doctor or Administrator rejects a pending appointment."""
    if appointment.status != Appointment.Status.PENDING:
        raise ValidationError(f"Cannot reject an appointment with status '{appointment.status}'. Must be PENDING.")

    is_assigned_doctor = hasattr(actor, "doctor_profile") and appointment.doctor_id == actor.doctor_profile.id
    is_admin = actor.role == "ADMIN" or actor.is_superuser
    if not (is_assigned_doctor or is_admin):
        raise PermissionDenied("Only the assigned doctor or an administrator can reject this appointment.")

    with transaction.atomic():
        appointment.status = Appointment.Status.REJECTED
        appointment.cancellation_reason = reason
        appointment.cancelled_by = actor
        appointment.cancelled_at = timezone.now()
        appointment.save(update_fields=["status", "cancellation_reason", "cancelled_by", "cancelled_at", "updated_at"])

        send_notification(
            recipient=appointment.patient.user,
            notification_type=Notification.NotificationType.APPOINTMENT_REJECTED,
            title="Appointment Rejected",
            message=f"Your appointment with Dr. {appointment.doctor.display_name} on {appointment.appointment_date} was rejected. Reason: {reason or 'Doctor unavailable.'}",
            data={"appointment_id": appointment.id},
        )

        log_audit_event(
            event_type="APPOINTMENT_STATUS_CHANGE",
            actor=actor,
            resource_type="Appointment",
            resource_id=str(appointment.id),
            action="REJECT_APPOINTMENT",
            details={"reason": reason},
            is_success=True,
            request=request,
        )

    return appointment


def cancel_appointment(appointment: Appointment, actor, reason: str = "", request=None) -> Appointment:
    """Patient, Assigned Doctor, or Administrator cancels a PENDING or CONFIRMED appointment."""
    if appointment.status not in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED):
        raise ValidationError(f"Cannot cancel an appointment with terminal status '{appointment.status}'.")

    is_patient_owner = hasattr(actor, "patient_profile") and appointment.patient_id == actor.patient_profile.id
    is_assigned_doctor = hasattr(actor, "doctor_profile") and appointment.doctor_id == actor.doctor_profile.id
    is_admin = actor.role == "ADMIN" or actor.is_superuser

    if not (is_patient_owner or is_assigned_doctor or is_admin):
        raise PermissionDenied("You do not have permission to cancel this appointment.")

    with transaction.atomic():
        appointment.status = Appointment.Status.CANCELLED
        appointment.cancellation_reason = reason
        appointment.cancelled_by = actor
        appointment.cancelled_at = timezone.now()
        appointment.save(update_fields=["status", "cancellation_reason", "cancelled_by", "cancelled_at", "updated_at"])

        # Notify the counterparty
        recipient = appointment.doctor.user if is_patient_owner else appointment.patient.user
        send_notification(
            recipient=recipient,
            notification_type=Notification.NotificationType.APPOINTMENT_CANCELLED,
            title="Appointment Cancelled",
            message=f"Appointment on {appointment.appointment_date} at {appointment.start_time} has been cancelled. Reason: {reason or 'Not specified.'}",
            data={"appointment_id": appointment.id},
        )

        log_audit_event(
            event_type="APPOINTMENT_CANCELLED",
            actor=actor,
            resource_type="Appointment",
            resource_id=str(appointment.id),
            action="CANCEL_APPOINTMENT",
            details={"reason": reason, "cancelled_by": actor.username},
            is_success=True,
            request=request,
        )

    return appointment


def complete_appointment(appointment: Appointment, actor, request=None) -> Appointment:
    """Assigned Doctor or Administrator completes a confirmed consultation."""
    if appointment.status != Appointment.Status.CONFIRMED:
        raise ValidationError(f"Cannot complete appointment with status '{appointment.status}'. Must be CONFIRMED.")

    is_assigned_doctor = hasattr(actor, "doctor_profile") and appointment.doctor_id == actor.doctor_profile.id
    is_admin = actor.role == "ADMIN" or actor.is_superuser
    if not (is_assigned_doctor or is_admin):
        raise PermissionDenied("Only the assigned doctor or an administrator can mark an appointment as completed.")

    with transaction.atomic():
        appointment.status = Appointment.Status.COMPLETED
        appointment.save(update_fields=["status", "updated_at"])

        send_notification(
            recipient=appointment.patient.user,
            notification_type=Notification.NotificationType.APPOINTMENT_COMPLETED,
            title="Consultation Completed",
            message=f"Your consultation with Dr. {appointment.doctor.display_name} has been marked as completed. Prescriptions and medical notes are available in your portal.",
            data={"appointment_id": appointment.id},
        )

        log_audit_event(
            event_type="APPOINTMENT_STATUS_CHANGE",
            actor=actor,
            resource_type="Appointment",
            resource_id=str(appointment.id),
            action="COMPLETE_APPOINTMENT",
            details={"new_status": Appointment.Status.COMPLETED},
            is_success=True,
            request=request,
        )

    return appointment
