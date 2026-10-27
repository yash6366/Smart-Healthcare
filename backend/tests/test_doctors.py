import pytest
from rest_framework import status
from apps.doctors.models import DoctorProfile


@pytest.mark.django_db
class TestDoctors:
    def test_public_doctor_listing_shows_only_verified_doctors(
        self, api_client, doctor_user, unverified_doctor_user
    ):
        response = api_client.get("/api/v1/doctors/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        results = data["results"]
        # Only verified doctor should appear
        doctor_ids = [doc["id"] for doc in results]
        assert doctor_user.doctor_profile.id in doctor_ids
        assert unverified_doctor_user.doctor_profile.id not in doctor_ids

    def test_filter_by_specialization(self, api_client, doctor_user):
        response = api_client.get("/api/v1/doctors/?specialization=CARDIOLOGY")
        assert response.status_code == status.HTTP_200_OK
        results = response.json()["results"]
        assert len(results) >= 1
        assert all(doc["specialization"] == "CARDIOLOGY" for doc in results)

        # Non-matching specialization
        response_empty = api_client.get("/api/v1/doctors/?specialization=PSYCHIATRY")
        assert len(response_empty.json()["results"]) == 0

    def test_search_by_doctor_name(self, api_client, doctor_user):
        response = api_client.get("/api/v1/doctors/?search=Ramesh")
        assert response.status_code == status.HTTP_200_OK
        results = response.json()["results"]
        assert len(results) >= 1
        assert results[0]["display_name"] == "Ramesh Sharma"

    def test_doctor_can_update_own_availability_and_fee(self, auth_client, doctor_user):
        client = auth_client(doctor_user)
        payload = {
            "is_available": False,
            "consultation_fee": "950.00",
            "biography": "Updated senior consultation profile",
        }
        response = client.patch("/api/v1/doctors/me/", payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_available"] is False
        assert data["consultation_fee"] == "950.00"

    def test_doctor_cannot_modify_own_verification_status(self, auth_client, unverified_doctor_user):
        client = auth_client(unverified_doctor_user)
        response = client.patch("/api/v1/doctors/me/", {"is_verified": True})
        assert response.status_code == status.HTTP_200_OK
        unverified_doctor_user.doctor_profile.refresh_from_db()
        # is_verified must remain False
        assert unverified_doctor_user.doctor_profile.is_verified is False

    def test_admin_can_provision_doctor_account(self, auth_client, admin_user):
        client = auth_client(admin_user)
        payload = {
            "username": "dr_priya",
            "email": "priya@vakcare.com",
            "password": "DoctorPassSecure123!",
            "first_name": "Priya",
            "last_name": "Nair",
            "phone_number": "+919988776655",
            "display_name": "Priya Nair",
            "specialization": "PEDIATRICS",
            "qualifications": "MBBS, DCH, MD (Pediatrics)",
            "years_of_experience": 8,
            "consultation_fee": "700.00",
            "license_number": "DMC-PED-9876",
            "is_verified": True,
            "is_available": True,
        }
        response = client.post("/api/v1/doctors/", payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert DoctorProfile.objects.filter(display_name="Priya Nair").exists()
