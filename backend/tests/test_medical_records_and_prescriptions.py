import pytest
from rest_framework import status
from apps.audit.models import AuditLog
from apps.prescriptions.models import Prescription


@pytest.mark.django_db
class TestMedicalRecordsAndPrescriptions:
    def test_doctor_creates_medical_record(self, auth_client, doctor_user, patient_user):
        client = auth_client(doctor_user)
        payload = {
            "patient_id": patient_user.patient_profile.id,
            "record_type": "DIAGNOSIS",
            "title": "Stage 1 Essential Hypertension",
            "description": "Patient presented with persistent elevated BP 142/92 mmHg over 3 readings.",
            "clinical_data": {"systolic_bp": 142, "diastolic_bp": 92, "pulse": 78},
        }
        response = client.post("/api/v1/medical-records/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()["record"]
        assert data["title"] == "Stage 1 Essential Hypertension"
        assert data["clinical_data"]["systolic_bp"] == 142

    def test_patient_can_view_own_medical_record(self, auth_client, doctor_user, patient_user):
        # Create record first
        doc_client = auth_client(doctor_user)
        create_resp = doc_client.post(
            "/api/v1/medical-records/",
            {
                "patient_id": patient_user.patient_profile.id,
                "record_type": "CONSULTATION_NOTE",
                "title": "Cardiology Consultation Summary",
                "description": "Normal heart sounds. Advised low sodium diet.",
            },
            format="json",
        )
        record_id = create_resp.json()["record"]["id"]

        # Patient reads own record
        pat_client = auth_client(patient_user)
        get_resp = pat_client.get(f"/api/v1/medical-records/{record_id}/")
        assert get_resp.status_code == status.HTTP_200_OK
        assert get_resp.json()["title"] == "Cardiology Consultation Summary"

        # Verify access was audited
        assert AuditLog.objects.filter(
            event_type="MEDICAL_RECORD_ACCESSED",
            actor=patient_user,
            resource_id=str(record_id),
        ).exists()

    def test_patient_cannot_view_another_patients_medical_record(
        self, auth_client, doctor_user, patient_user, second_patient_user
    ):
        doc_client = auth_client(doctor_user)
        create_resp = doc_client.post(
            "/api/v1/medical-records/",
            {
                "patient_id": patient_user.patient_profile.id,
                "record_type": "CONSULTATION_NOTE",
                "title": "Confidential Cardiac Evaluation",
                "description": "Strictly confidential medical findings.",
            },
            format="json",
        )
        record_id = create_resp.json()["record"]["id"]

        # Second patient tries to read first patient's record
        second_client = auth_client(second_patient_user)
        get_resp = second_client.get(f"/api/v1/medical-records/{record_id}/")
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND

    def test_patient_cannot_create_medical_records(self, auth_client, patient_user):
        client = auth_client(patient_user)
        payload = {
            "patient_id": patient_user.patient_profile.id,
            "record_type": "CONSULTATION_NOTE",
            "title": "Self Diagnosis",
            "description": "Should be rejected.",
        }
        response = client.post("/api/v1/medical-records/", payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_doctor_issues_prescription(self, auth_client, doctor_user, patient_user):
        client = auth_client(doctor_user)
        payload = {
            "patient_id": patient_user.patient_profile.id,
            "diagnosis": "Mild allergic rhinitis",
            "notes": "Drink warm fluids and avoid cold dust exposures.",
            "items": [
                {
                    "medication_name": "Cetirizine Hydrochloride",
                    "dosage": "10 mg",
                    "frequency": "Once daily at bedtime",
                    "duration": "5 days",
                    "instructions": "Take with water.",
                },
                {
                    "medication_name": "Saline Nasal Spray",
                    "dosage": "2 sprays",
                    "frequency": "Twice daily",
                    "duration": "7 days",
                    "instructions": "Administer before bedtime.",
                },
            ],
        }
        response = client.post("/api/v1/prescriptions/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "success"
        rx = data["prescription"]
        assert len(rx["items"]) == 2
        assert rx["items"][0]["medication_name"] == "Cetirizine Hydrochloride"

        # Verify database
        assert Prescription.objects.filter(diagnosis="Mild allergic rhinitis").exists()

    def test_patient_cannot_issue_prescription(self, auth_client, patient_user):
        client = auth_client(patient_user)
        payload = {
            "patient_id": patient_user.patient_profile.id,
            "diagnosis": "Self Prescribing",
            "items": [
                {
                    "medication_name": "Antibiotic",
                    "dosage": "500 mg",
                    "frequency": "Once",
                    "duration": "1 day",
                }
            ],
        }
        response = client.post("/api/v1/prescriptions/", payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unverified_doctor_cannot_issue_prescription(
        self, auth_client, unverified_doctor_user, patient_user
    ):
        client = auth_client(unverified_doctor_user)
        payload = {
            "patient_id": patient_user.patient_profile.id,
            "diagnosis": "Unverified Doctor Prescription",
            "items": [
                {
                    "medication_name": "Paracetamol",
                    "dosage": "500 mg",
                    "frequency": "Once",
                    "duration": "1 day",
                }
            ],
        }
        response = client.post("/api/v1/prescriptions/", payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
