import pytest
from rest_framework import status
from apps.audit.models import AuditLog
from apps.medical_records.models import MedicalRecord


@pytest.mark.django_db
class TestAIAssistant:
    def test_ai_guidance_successful_response(self, auth_client, patient_user):
        client = auth_client(patient_user)
        payload = {"query": "I have had a mild fever and headache since yesterday morning."}
        response = client.post("/api/v1/ai/guidance/", payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        ai_data = data["data"]
        assert "guidance" in ai_data
        assert "disclaimer" in ai_data
        assert "DISCLAIMER" in ai_data["disclaimer"]
        assert ai_data["suggested_specialization"] == "GENERAL_MEDICINE"

        # Verify query was audited
        assert AuditLog.objects.filter(event_type="AI_QUERY", actor=patient_user).exists()

    def test_ai_guidance_validation_too_short(self, auth_client, patient_user):
        client = auth_client(patient_user)
        payload = {"query": "hi"}  # < 5 chars
        response = client.post("/api/v1/ai/guidance/", payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_ai_summarize_authorized_record(
        self, auth_client, patient_user, doctor_user
    ):
        record = MedicalRecord.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            record_type="CONSULTATION_NOTE",
            title="Cardiology Assessment",
            description="Resting heart rate 72 bpm. Normal rhythm, no murmurs detected. Advised continued light aerobic exercise.",
            clinical_data={"heart_rate": 72, "rhythm": "regular"},
        )

        client = auth_client(patient_user)
        response = client.post("/api/v1/ai/summarize-record/", {"record_id": record.id})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert "summary" in data
        assert "disclaimer" in data

    def test_ai_summarize_unauthorized_record_rejection(
        self, auth_client, patient_user, second_patient_user, doctor_user
    ):
        # Record belongs to patient_user
        record = MedicalRecord.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            record_type="CONSULTATION_NOTE",
            title="Confidential Patient A Record",
            description="Confidential medical notes.",
        )

        # second_patient_user tries to summarize it
        client = auth_client(second_patient_user)
        response = client.post("/api/v1/ai/summarize-record/", {"record_id": record.id})
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_openai_provider_fallback_and_factory(self, settings):
        settings.AI_PROVIDER = "openai"
        settings.AI_PROVIDER_API_KEY = ""  # No key supplied
        from apps.ai_assistant.providers.factory import get_ai_provider
        from apps.ai_assistant.providers.openai_provider import OpenAIProvider

        provider = get_ai_provider()
        assert isinstance(provider, OpenAIProvider)

        # Guidance falls back to safe deterministic mock without errors
        guidance = provider.generate_guidance("fever and body ache")
        assert "guidance" in guidance
        assert "disclaimer" in guidance
        assert "MockAIProvider" in guidance["provider"]

        # Summarization falls back cleanly
        summary = provider.summarize_medical_record(
            title="Blood Test", description="Normal ranges observed.", clinical_data={"wbc": 6500}
        )
        assert "summary" in summary
        assert "MockAIProvider" in summary["provider"]

