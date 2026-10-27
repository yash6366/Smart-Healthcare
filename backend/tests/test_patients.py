import pytest
from rest_framework import status


@pytest.mark.django_db
class TestPatients:
    def test_get_patient_me(self, auth_client, patient_user):
        client = auth_client(patient_user)
        response = client.get("/api/v1/patients/me/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["city"] == "Bengaluru"
        assert data["blood_group"] == "O+"
        assert data["user"]["email"] == patient_user.email

    def test_update_patient_me(self, auth_client, patient_user):
        client = auth_client(patient_user)
        payload = {
            "city": "Mysuru",
            "emergency_contact_name": "Mary Doe",
            "emergency_contact_phone": "+919876500000",
            "first_name": "Johnny",
        }
        response = client.patch("/api/v1/patients/me/", payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["city"] == "Mysuru"
        assert data["emergency_contact_name"] == "Mary Doe"

        patient_user.refresh_from_db()
        assert patient_user.first_name == "Johnny"

    def test_patient_cannot_view_another_patient_detail(
        self, auth_client, patient_user, second_patient_user
    ):
        client = auth_client(patient_user)
        # Attempt to access second patient's ID
        response = client.get(f"/api/v1/patients/{second_patient_user.patient_profile.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_view_any_patient_detail(
        self, auth_client, admin_user, patient_user
    ):
        client = auth_client(admin_user)
        response = client.get(f"/api/v1/patients/{patient_user.patient_profile.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["user"]["email"] == patient_user.email
