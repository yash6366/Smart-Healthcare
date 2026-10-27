
import pytest
from rest_framework import status


@pytest.mark.django_db
class TestAuthorizationAndRBAC:
    def test_anonymous_access_to_patients_me_rejected(self, api_client):
        response = api_client.get("/api/v1/patients/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patient_cannot_access_doctor_me_endpoint(self, auth_client, patient_user):
        client = auth_client(patient_user)
        response = client.get("/api/v1/doctors/me/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_doctor_cannot_access_patient_me_endpoint(self, auth_client, doctor_user):
        client = auth_client(doctor_user)
        response = client.get("/api/v1/patients/me/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_patient_cannot_access_audit_logs(self, auth_client, patient_user):
        client = auth_client(patient_user)
        response = client.get("/api/v1/audit/logs/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_doctor_cannot_access_audit_logs(self, auth_client, doctor_user):
        client = auth_client(doctor_user)
        response = client.get("/api/v1/audit/logs/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_access_audit_logs(self, auth_client, admin_user):
        client = auth_client(admin_user)
        response = client.get("/api/v1/audit/logs/")
        assert response.status_code == status.HTTP_200_OK

    def test_patient_cannot_verify_doctor(self, auth_client, patient_user, unverified_doctor_user):
        client = auth_client(patient_user)
        response = client.post(
            f"/api/v1/doctors/{unverified_doctor_user.doctor_profile.id}/verify/",
            {"is_verified": True},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_doctor_cannot_verify_themselves(self, auth_client, unverified_doctor_user):
        client = auth_client(unverified_doctor_user)
        response = client.post(
            f"/api/v1/doctors/{unverified_doctor_user.doctor_profile.id}/verify/",
            {"is_verified": True},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_verify_doctor(self, auth_client, admin_user, unverified_doctor_user):
        client = auth_client(admin_user)
        response = client.post(
            f"/api/v1/doctors/{unverified_doctor_user.doctor_profile.id}/verify/",
            {"is_verified": True, "notes": "Medical license verified against state council."},
        )
        assert response.status_code == status.HTTP_200_OK
        unverified_doctor_user.doctor_profile.refresh_from_db()
        assert unverified_doctor_user.doctor_profile.is_verified is True
