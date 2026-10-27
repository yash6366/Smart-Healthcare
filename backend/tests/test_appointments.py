from datetime import date, timedelta
import pytest
from rest_framework import status
from django.utils import timezone
from apps.appointments.models import Appointment
from apps.notifications.models import Notification


@pytest.fixture
def future_date():
    return date.today() + timedelta(days=2)


@pytest.mark.django_db
class TestAppointments:
    def test_successful_appointment_booking(
        self, auth_client, patient_user, doctor_user, future_date
    ):
        client = auth_client(patient_user)
        payload = {
            "doctor_id": doctor_user.doctor_profile.id,
            "appointment_date": str(future_date),
            "start_time": "10:00:00",
            "duration_minutes": 30,
            "reason": "Routine cardiac checkup and consultation.",
        }
        response = client.post("/api/v1/appointments/", payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "success"
        appt = data["appointment"]
        assert appt["status"] == "PENDING"
        assert appt["start_time"] == "10:00:00"
        assert appt["end_time"] == "10:30:00"

        # Verify doctor notification was generated
        assert Notification.objects.filter(
            recipient=doctor_user,
            notification_type=Notification.NotificationType.APPOINTMENT_REQUESTED,
        ).exists()

    def test_past_appointment_booking_rejection(
        self, auth_client, patient_user, doctor_user
    ):
        client = auth_client(patient_user)
        past_date = date.today() - timedelta(days=1)
        payload = {
            "doctor_id": doctor_user.doctor_profile.id,
            "appointment_date": str(past_date),
            "start_time": "10:00:00",
            "reason": "Past date consultation attempt.",
        }
        response = client.post("/api/v1/appointments/", payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_booking_with_unverified_doctor_rejection(
        self, auth_client, patient_user, unverified_doctor_user, future_date
    ):
        client = auth_client(patient_user)
        payload = {
            "doctor_id": unverified_doctor_user.doctor_profile.id,
            "appointment_date": str(future_date),
            "start_time": "10:00:00",
            "reason": "Attempt booking with unverified doctor.",
        }
        response = client.post("/api/v1/appointments/", payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_booking_outside_working_hours_rejection(
        self, auth_client, patient_user, doctor_user, future_date
    ):
        client = auth_client(patient_user)
        # Doctor works 09:00:00 to 18:00:00
        payload = {
            "doctor_id": doctor_user.doctor_profile.id,
            "appointment_date": str(future_date),
            "start_time": "21:00:00",
            "reason": "Night consultation attempt.",
        }
        response = client.post("/api/v1/appointments/", payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_conflicting_doctor_appointment_rejection(
        self, auth_client, patient_user, second_patient_user, doctor_user, future_date
    ):
        client1 = auth_client(patient_user)
        client2 = auth_client(second_patient_user)

        # First booking: 11:00 to 11:30
        payload1 = {
            "doctor_id": doctor_user.doctor_profile.id,
            "appointment_date": str(future_date),
            "start_time": "11:00:00",
            "duration_minutes": 30,
            "reason": "Patient 1 consultation.",
        }
        resp1 = client1.post("/api/v1/appointments/", payload1)
        assert resp1.status_code == status.HTTP_201_CREATED

        # Second booking by different patient for overlapping slot: 11:15 to 11:45
        payload2 = {
            "doctor_id": doctor_user.doctor_profile.id,
            "appointment_date": str(future_date),
            "start_time": "11:15:00",
            "duration_minutes": 30,
            "reason": "Patient 2 overlapping consultation.",
        }
        resp2 = client2.post("/api/v1/appointments/", payload2)
        assert resp2.status_code == status.HTTP_400_BAD_REQUEST
        assert "Doctor already has an active appointment" in str(resp2.json())

    def test_conflicting_patient_appointment_rejection(
        self, auth_client, patient_user, doctor_user, admin_user, future_date
    ):
        # Create second doctor
        user2 = apps_user = admin_user  # temporary user
        from apps.accounts.models import User
        from apps.doctors.models import DoctorProfile

        doc2_user = User.objects.create_user(
            username="dr_verma",
            email="verma@vakcare.com",
            password="DocPassword123!",
            role=User.Role.DOCTOR,
            is_verified=True,
        )
        doc2 = DoctorProfile.objects.create(
            user=doc2_user,
            display_name="Anita Verma",
            specialization="DERMATOLOGY",
            qualifications="MBBS, MD",
            is_verified=True,
            is_available=True,
            working_hours_start="09:00:00",
            working_hours_end="18:00:00",
        )

        client = auth_client(patient_user)

        # Book with Doctor 1 at 14:00 to 14:30
        resp1 = client.post(
            "/api/v1/appointments/",
            {
                "doctor_id": doctor_user.doctor_profile.id,
                "appointment_date": str(future_date),
                "start_time": "14:00:00",
                "duration_minutes": 30,
                "reason": "Heart consultation.",
            },
        )
        assert resp1.status_code == status.HTTP_201_CREATED

        # Attempt to book with Doctor 2 at same time 14:00 to 14:30 for same patient
        resp2 = client.post(
            "/api/v1/appointments/",
            {
                "doctor_id": doc2.id,
                "appointment_date": str(future_date),
                "start_time": "14:00:00",
                "duration_minutes": 30,
                "reason": "Skin consultation at same time.",
            },
        )
        assert resp2.status_code == status.HTTP_400_BAD_REQUEST
        assert "Patient already has an active appointment" in str(resp2.json())

    def test_appointment_lifecycle_and_state_transitions(
        self, auth_client, patient_user, doctor_user, future_date
    ):
        patient_client = auth_client(patient_user)
        doctor_client = auth_client(doctor_user)

        # 1. Book appointment (PENDING)
        resp = patient_client.post(
            "/api/v1/appointments/",
            {
                "doctor_id": doctor_user.doctor_profile.id,
                "appointment_date": str(future_date),
                "start_time": "15:00:00",
                "reason": "Followup consultation.",
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED
        appt_id = resp.json()["appointment"]["id"]

        # 2. Doctor confirms appointment (PENDING -> CONFIRMED)
        confirm_resp = doctor_client.post(f"/api/v1/appointments/{appt_id}/confirm/")
        assert confirm_resp.status_code == status.HTTP_200_OK
        assert confirm_resp.json()["appointment"]["status"] == "CONFIRMED"

        # 3. Doctor completes consultation (CONFIRMED -> COMPLETED)
        complete_resp = doctor_client.post(f"/api/v1/appointments/{appt_id}/complete/")
        assert complete_resp.status_code == status.HTTP_200_OK
        assert complete_resp.json()["appointment"]["status"] == "COMPLETED"

        # 4. Attempting to cancel an already completed appointment must fail
        cancel_resp = patient_client.post(
            f"/api/v1/appointments/{appt_id}/cancel/",
            {"cancellation_reason": "No longer needed."},
        )
        assert cancel_resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_appointment_cancellation(
        self, auth_client, patient_user, doctor_user, future_date
    ):
        patient_client = auth_client(patient_user)

        resp = patient_client.post(
            "/api/v1/appointments/",
            {
                "doctor_id": doctor_user.doctor_profile.id,
                "appointment_date": str(future_date),
                "start_time": "16:00:00",
                "reason": "General checkup.",
            },
        )
        appt_id = resp.json()["appointment"]["id"]

        # Cancel
        cancel_resp = patient_client.post(
            f"/api/v1/appointments/{appt_id}/cancel/",
            {"cancellation_reason": "Personal emergency."},
        )
        assert cancel_resp.status_code == status.HTTP_200_OK
        assert cancel_resp.json()["appointment"]["status"] == "CANCELLED"

    def test_unauthorized_user_cannot_cancel_appointment(
        self, auth_client, patient_user, second_patient_user, doctor_user, future_date
    ):
        patient_client = auth_client(patient_user)
        second_client = auth_client(second_patient_user)

        resp = patient_client.post(
            "/api/v1/appointments/",
            {
                "doctor_id": doctor_user.doctor_profile.id,
                "appointment_date": str(future_date),
                "start_time": "17:00:00",
                "reason": "Confidential consultation.",
            },
        )
        appt_id = resp.json()["appointment"]["id"]

        # Second patient attempts to cancel first patient's appointment
        bad_cancel = second_client.post(f"/api/v1/appointments/{appt_id}/cancel/")
        # Should be forbidden or not found
        assert bad_cancel.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
