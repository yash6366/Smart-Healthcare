import pytest
from datetime import date, timedelta
from django.utils import timezone
from rest_framework import status
from apps.accounts.models import User
from apps.ai_assistant.models import Conversation, Message
from apps.appointments.models import Appointment
from apps.medical_records.models import MedicalRecord
from apps.prescriptions.models import Prescription, PrescriptionItem
from apps.notifications.models import Notification
from apps.notifications.services import generate_appointment_reminders
from apps.patients.models import PatientProfile
from apps.doctors.models import DoctorProfile


@pytest.fixture
def unrelated_doctor_user(db):
    user = User.objects.create_user(
        username="dr_unrelated",
        email="unrelated@vakcare.com",
        password="SecureDoctorPass123!",
        first_name="Priya",
        last_name="Nair",
        role=User.Role.DOCTOR,
        is_verified=True,
    )
    DoctorProfile.objects.create(
        user=user,
        display_name="Priya Nair",
        specialization=DoctorProfile.Specialization.PEDIATRICS,
        license_number="KMC-PED-99887",
        is_verified=True,
        is_available=True,
    )
    return user


@pytest.mark.django_db
class TestPhaseFAIAssistant:
    def test_conversation_lifecycle_and_owner_isolation(
        self, auth_client, patient_user, second_patient_user, doctor_user, admin_user
    ):
        client = auth_client(patient_user)

        # 1. Create a new conversation
        create_res = client.post(
            "/api/v1/ai/conversations/",
            {"query": "I have had a mild headache and fever since morning."},
        )
        assert create_res.status_code == status.HTTP_201_CREATED
        conv_data = create_res.json()["conversation"]
        conv_id = conv_data["id"]
        assert conv_data["title"] is not None
        assert len(conv_data["messages"]) == 2  # user + assistant

        user_msg = conv_data["messages"][0]
        asst_msg = conv_data["messages"][1]
        assert user_msg["role"] == "USER"
        assert asst_msg["role"] == "ASSISTANT"
        assert len(asst_msg["content"]) > 10
        assert "DISCLAIMER" in asst_msg["metadata"]["disclaimer"]

        # 2. Add a follow-up message
        msg_res = client.post(
            f"/api/v1/ai/conversations/{conv_id}/messages/",
            {"query": "Should I take paracetamol or see a doctor immediately?"},
        )
        assert msg_res.status_code == status.HTTP_201_CREATED
        asst_reply = msg_res.json()["assistant_message"]
        assert asst_reply["role"] == "ASSISTANT"
        assert len(asst_reply["content"]) > 10

        # Check total messages in conversation
        detail_res = client.get(f"/api/v1/ai/conversations/{conv_id}/")
        assert detail_res.status_code == status.HTTP_200_OK
        messages = detail_res.json()["conversation"]["messages"]
        assert len(messages) == 4  # 2 original + 1 user follow-up + 1 assistant reply

        # 3. Isolation: second_patient_user cannot access patient_user's conversation
        other_client = auth_client(second_patient_user)
        assert other_client.get(f"/api/v1/ai/conversations/{conv_id}/").status_code == status.HTTP_404_NOT_FOUND
        assert other_client.post(
            f"/api/v1/ai/conversations/{conv_id}/messages/", {"query": "Hack attempt"}
        ).status_code == status.HTTP_404_NOT_FOUND

        # 4. Doctor and Admin cannot view private patient conversations
        doc_client = auth_client(doctor_user)
        assert doc_client.get(f"/api/v1/ai/conversations/{conv_id}/").status_code == status.HTTP_404_NOT_FOUND

        adm_client = auth_client(admin_user)
        assert adm_client.get(f"/api/v1/ai/conversations/{conv_id}/").status_code == status.HTTP_404_NOT_FOUND

        # 5. Delete conversation
        del_res = client.delete(f"/api/v1/ai/conversations/{conv_id}/")
        assert del_res.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT)
        assert not Conversation.objects.filter(id=conv_id).exists()
        assert not Message.objects.filter(conversation_id=conv_id).exists()

    def test_record_summarization_separates_facts_and_guidance(
        self, auth_client, patient_user, doctor_user
    ):
        record = MedicalRecord.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            record_type="LAB_RESULT",
            title="Comprehensive Metabolic Panel",
            description="Serum creatinine 0.9 mg/dL. Fasting blood glucose 98 mg/dL. Normal renal and metabolic findings.",
            clinical_data={"creatinine": 0.9, "fasting_glucose": 98},
        )

        client = auth_client(patient_user)
        res = client.post("/api/v1/ai/summarize-record/", {"record_id": record.id})
        assert res.status_code == status.HTTP_200_OK
        data = res.json()["data"]

        summary = data["summary"]
        assert "DOCUMENTED CLINICAL FACTS" in summary
        assert "PATIENT-FRIENDLY EXPLANATION & GUIDANCE" in summary
        assert "DISCLAIMER" in data["disclaimer"]


@pytest.mark.django_db
class TestPhaseFPatientTimeline:
    def test_timeline_aggregates_events_chronologically(
        self, auth_client, patient_user, doctor_user
    ):
        # Create an appointment
        appt = Appointment.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            appointment_date=date.today() + timedelta(days=2),
            start_time="10:00:00",
            end_time="10:30:00",
            status=Appointment.Status.CONFIRMED,
            reason="Routine cardiac check",
        )

        # Create a medical record
        rec = MedicalRecord.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            record_type="CONSULTATION_NOTE",
            title="Blood Pressure Review",
            description="Blood pressure normal at 120/80 mmHg.",
        )

        # Create a prescription
        rx = Prescription.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            appointment=appt,
            diagnosis="Essential Hypertension",
            notes="Take after breakfast.",
        )
        PrescriptionItem.objects.create(
            prescription=rx,
            medication_name="Amlodipine",
            dosage="5mg",
            frequency="Once daily",
            duration="30 days",
        )

        client = auth_client(patient_user)
        res = client.get("/api/v1/patients/me/timeline/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()

        events = data["results"]
        assert len(events) >= 3
        event_types = {e["event_type"] for e in events}
        assert "APPOINTMENT" in event_types
        assert "MEDICAL_RECORD" in event_types
        assert "PRESCRIPTION" in event_types

        # Test filtering by event_type
        rx_res = client.get("/api/v1/patients/me/timeline/?event_type=PRESCRIPTION")
        assert rx_res.status_code == status.HTTP_200_OK
        rx_events = rx_res.json()["results"]
        assert all(e["event_type"] == "PRESCRIPTION" for e in rx_events)

    def test_timeline_user_isolation_and_empty_state(
        self, auth_client, second_patient_user
    ):
        client = auth_client(second_patient_user)
        res = client.get("/api/v1/patients/me/timeline/")
        assert res.status_code == status.HTTP_200_OK
        events = res.json()["results"]
        assert len(events) == 0


@pytest.mark.django_db
class TestPhaseFAppointmentReminders:
    def test_reminder_generation_and_deduplication(
        self, patient_user, doctor_user, admin_user, auth_client
    ):
        target_date = date.today() + timedelta(days=1)
        appt = Appointment.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            appointment_date=target_date,
            start_time="14:30:00",
            end_time="15:00:00",
            status=Appointment.Status.CONFIRMED,
            reason="Follow-up consultation",
        )

        # 1. Generate reminders
        created_count = generate_appointment_reminders(lead_hours=48)
        assert created_count == 1

        notif = Notification.objects.filter(
            recipient=patient_user,
            notification_type=Notification.NotificationType.APPOINTMENT_REMINDER,
        ).first()
        assert notif is not None
        assert "Appointment Reminder" in notif.title
        assert notif.data.get("appointment_id") == appt.id

        # 2. Deduplication check: Running again creates 0 new notifications
        second_run_count = generate_appointment_reminders(lead_hours=48)
        assert second_run_count == 0

        # 3. Cancelled appointments should NOT receive reminders
        appt.status = Appointment.Status.CANCELLED
        appt.save()
        third_run_count = generate_appointment_reminders(lead_hours=48)
        assert third_run_count == 0

        # 4. Trigger endpoint permission check: Admin can trigger, Patient/Doctor cannot
        adm_client = auth_client(admin_user)
        trig_res = adm_client.post("/api/v1/notifications/trigger-reminders/", {"lead_hours": 48})
        assert trig_res.status_code == status.HTTP_200_OK

        pat_client = auth_client(patient_user)
        assert pat_client.post("/api/v1/notifications/trigger-reminders/").status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestPhaseFDoctorWorkflows:
    def test_doctor_daily_schedule_view(self, auth_client, doctor_user, patient_user):
        today = date.today()
        Appointment.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            appointment_date=today,
            start_time="11:00:00",
            end_time="11:30:00",
            status=Appointment.Status.CONFIRMED,
            reason="Chest tightness evaluation",
        )

        client = auth_client(doctor_user)
        res = client.get(f"/api/v1/appointments/daily-schedule/?date={today.isoformat()}")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()

        assert data["date"] == today.isoformat()
        assert data["kpis"]["total_slots"] >= 1
        assert len(data["schedule"]) >= 1
        slot = data["schedule"][0]
        assert slot["patient"]["name"] == patient_user.get_full_name()
        assert slot["start_time"] == "11:00:00"

    def test_doctor_patient_clinical_history_relationship_boundary(
        self, auth_client, doctor_user, unrelated_doctor_user, patient_user
    ):
        # Create an appointment between doctor_user and patient_user
        Appointment.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            appointment_date=date.today(),
            start_time="09:30:00",
            end_time="10:00:00",
            status=Appointment.Status.CONFIRMED,
            reason="General consultation",
        )

        # Create record for patient
        MedicalRecord.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            record_type="CONSULTATION_NOTE",
            title="Initial Consultation",
            description="Patient reports good general wellbeing.",
        )

        patient_profile_id = patient_user.patient_profile.id

        # 1. Attending doctor CAN access clinical history
        attending_client = auth_client(doctor_user)
        res = attending_client.get(f"/api/v1/patients/{patient_profile_id}/clinical-history/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert len(data["medical_records"]) >= 1

        # 2. Unrelated doctor CANNOT access clinical history (403 Forbidden)
        unrelated_client = auth_client(unrelated_doctor_user)
        res_unrelated = unrelated_client.get(f"/api/v1/patients/{patient_profile_id}/clinical-history/")
        assert res_unrelated.status_code == status.HTTP_403_FORBIDDEN
        assert "no consultations exist" in res_unrelated.json()["error"]["message"]


@pytest.mark.django_db
class TestPhaseFAdminAnalytics:
    def test_admin_analytics_metrics_and_permissions(
        self, auth_client, admin_user, patient_user, doctor_user
    ):
        # Create completed appointment
        Appointment.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            appointment_date=date.today() - timedelta(days=2),
            start_time="10:00:00",
            end_time="10:30:00",
            status=Appointment.Status.COMPLETED,
            reason="Routine wellness check",
        )
        # Create cancelled appointment
        Appointment.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            appointment_date=date.today() - timedelta(days=1),
            start_time="11:00:00",
            end_time="11:30:00",
            status=Appointment.Status.CANCELLED,
            reason="Conflict in personal schedule",
        )

        # 1. Admin access
        adm_client = auth_client(admin_user)
        res = adm_client.get("/api/v1/audit/analytics/?days=30")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()

        assert "period" in data
        assert "rates" in data
        rates = data["rates"]
        assert rates["completion_rate_percent"] >= 0
        assert rates["cancellation_rate_percent"] >= 0
        assert "completion_rate_denominator" in rates
        assert "cancellation_rate_denominator" in rates

        assert "practitioners_and_patients" in data
        assert data["practitioners_and_patients"]["total_patients"] >= 1
        assert data["practitioners_and_patients"]["total_doctors"] >= 1

        assert "appointments_window" in data
        assert data["appointments_window"]["completed"] >= 1
        assert data["appointments_window"]["cancelled"] >= 1

        assert "system_health" in data
        assert "database" in data["system_health"]

        # 2. Non-admin forbidden
        pat_client = auth_client(patient_user)
        assert pat_client.get("/api/v1/audit/analytics/").status_code == status.HTTP_403_FORBIDDEN

        doc_client = auth_client(doctor_user)
        assert doc_client.get("/api/v1/audit/analytics/").status_code == status.HTTP_403_FORBIDDEN
