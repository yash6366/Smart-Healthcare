import pytest
from rest_framework import status
from apps.accounts.models import User
from apps.patients.models import PatientProfile
from tests.conftest import get_tokens_for_user


@pytest.mark.django_db
class TestAuthentication:
    def test_successful_patient_registration(self, api_client):
        payload = {
            "username": "new_patient",
            "email": "new_patient@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "first_name": "Test",
            "last_name": "Patient",
            "phone_number": "+919123456789",
        }
        response = api_client.post("/api/v1/auth/register/", payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "success"
        assert data["user"]["email"] == "new_patient@example.com"
        assert data["user"]["role"] == "PATIENT"

        # Verify database record
        user = User.objects.get(username="new_patient")
        assert user.role == User.Role.PATIENT
        assert user.check_password("StrongPassword123!")
        # Verify PatientProfile was auto-created
        assert PatientProfile.objects.filter(user=user).exists()

    def test_registration_prevents_role_escalation(self, api_client):
        # Attempting to supply role="ADMIN" in registration body
        payload = {
            "username": "hacker_user",
            "email": "hacker@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "role": "ADMIN",
        }
        response = api_client.post("/api/v1/auth/register/", payload)
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(username="hacker_user")
        # Enforce that role was forced to PATIENT
        assert user.role == User.Role.PATIENT
        assert not user.is_staff
        assert not user.is_superuser

    def test_duplicate_email_registration_rejection(self, api_client, patient_user):
        payload = {
            "username": "distinct_username",
            "email": patient_user.email,  # duplicate
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }
        response = api_client.post("/api/v1/auth/register/", payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_mismatch_rejection(self, api_client):
        payload = {
            "username": "mismatch_user",
            "email": "mismatch@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "DifferentPassword123!",
        }
        response = api_client.post("/api/v1/auth/register/", payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_successful_login_with_email(self, api_client, patient_user):
        payload = {
            "email_or_username": patient_user.email,
            "password": "SecurePassword123!",
        }
        response = api_client.post("/api/v1/auth/login/", payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "tokens" in data
        assert "access" in data["tokens"]
        assert "refresh" in data["tokens"]
        assert data["user"]["email"] == patient_user.email

    def test_successful_login_with_username(self, api_client, patient_user):
        payload = {
            "email_or_username": patient_user.username,
            "password": "SecurePassword123!",
        }
        response = api_client.post("/api/v1/auth/login/", payload)
        assert response.status_code == status.HTTP_200_OK

    def test_login_incorrect_password(self, api_client, patient_user):
        payload = {
            "email_or_username": patient_user.email,
            "password": "WrongPassword!",
        }
        response = api_client.post("/api/v1/auth/login/", payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["status"] == "error"

    def test_disabled_account_login_rejection(self, api_client, patient_user):
        patient_user.is_active = False
        patient_user.save()

        payload = {
            "email_or_username": patient_user.email,
            "password": "SecurePassword123!",
        }
        response = api_client.post("/api/v1/auth/login/", payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_jwt_access_to_protected_me_endpoint(self, auth_client, patient_user):
        client = auth_client(patient_user)
        response = client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["username"] == patient_user.username

    def test_anonymous_access_to_protected_endpoint_rejected(self, api_client):
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh(self, api_client, patient_user):
        _, refresh = get_tokens_for_user(patient_user)
        response = api_client.post("/api/v1/auth/token/refresh/", {"refresh": refresh})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.json()

    def test_logout_blacklists_refresh_token(self, auth_client, api_client, patient_user):
        client = auth_client(patient_user)
        _, refresh = get_tokens_for_user(patient_user)

        # Logout
        response = client.post("/api/v1/auth/logout/", {"refresh": refresh})
        assert response.status_code == status.HTTP_200_OK

        # Trying to use blacklisted refresh token must fail
        refresh_response = api_client.post("/api/v1/auth/token/refresh/", {"refresh": refresh})
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_change_password(self, auth_client, patient_user):
        client = auth_client(patient_user)
        payload = {
            "old_password": "SecurePassword123!",
            "new_password": "BrandNewPassword123!",
            "new_password_confirm": "BrandNewPassword123!",
        }
        response = client.post("/api/v1/auth/change-password/", payload)
        assert response.status_code == status.HTTP_200_OK

        # Verify old password no longer works and new password works
        patient_user.refresh_from_db()
        assert not patient_user.check_password("SecurePassword123!")
        assert patient_user.check_password("BrandNewPassword123!")
