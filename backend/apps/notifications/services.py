import logging
from datetime import datetime, timedelta
from typing import Any
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Notification

logger = logging.getLogger("apps.notifications")
User = get_user_model()


def send_notification(
    recipient,
    notification_type: str,
    title: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> Notification | None:
    """
    Creates an in-app database notification for the recipient.
    Designed for seamless future expansion to email/SMS/push queues.
    """
    try:
        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
        )
        logger.info(
            "Notification %s sent to %s [%s]",
            notification.id,
            recipient.username,
            notification_type,
        )
        return notification
    except Exception as exc:
        logger.error("Failed to send notification: %s", exc)
        return None


def generate_appointment_reminders(lead_hours: int = 48) -> int:
    """
    Scans for confirmed upcoming appointments within the specified window (up to lead_hours)
    and dispatches deduplicated in-app APPOINTMENT_REMINDER notifications to patients.
    Does NOT notify for cancelled, rejected, or completed appointments.
    Returns the count of reminders generated.
    """
    from apps.appointments.models import Appointment

    now = timezone.now()
    window_end = now + timedelta(hours=lead_hours)

    candidate_appts = Appointment.objects.filter(
        status=Appointment.Status.CONFIRMED,
        appointment_date__gte=now.date(),
        appointment_date__lte=window_end.date(),
    ).select_related("doctor", "patient", "patient__user")

    reminders_sent = 0
    for appt in candidate_appts:
        appt_datetime = timezone.make_aware(datetime.combine(appt.appointment_date, appt.start_time))
        # Ensure it is in the future and within the lead window
        if not (now < appt_datetime <= window_end):
            continue

        # Deduplication check: check if a reminder for this appointment has already been dispatched
        already_sent = Notification.objects.filter(
            recipient=appt.patient.user,
            notification_type=Notification.NotificationType.APPOINTMENT_REMINDER,
            data__appointment_id=appt.id,
        ).exists()

        if not already_sent:
            notif = send_notification(
                recipient=appt.patient.user,
                notification_type=Notification.NotificationType.APPOINTMENT_REMINDER,
                title="Upcoming Appointment Reminder",
                message=(
                    f"Reminder: You have an upcoming consultation with Dr. {appt.doctor.display_name} "
                    f"on {appt.appointment_date} at {appt.start_time}."
                ),
                data={
                    "appointment_id": appt.id,
                    "doctor_id": appt.doctor.id,
                    "appointment_date": str(appt.appointment_date),
                    "start_time": str(appt.start_time),
                },
            )
            if notif:
                reminders_sent += 1

    logger.info("Generated %d appointment reminder notifications.", reminders_sent)
    return reminders_sent
