import pytest
from rest_framework import status
from apps.audit.services import log_audit_event, sanitize_details
from apps.audit.models import AuditLog


@pytest.mark.django_db
class TestAuditSystem:
    def test_sanitize_details_strips_sensitive_credentials(self):
        raw = {
            "username": "test_user",
            "password": "SuperSecretPassword123!",
            "password_confirm": "SuperSecretPassword123!",
            "access_token": "secret_jwt_token",
            "api_key": "secret_key_123",
            "clinical_notes": "Patient feeling well",
        }
        cleaned = sanitize_details(raw)
        assert cleaned["username"] == "test_user"
        assert cleaned["password"] == "[REDACTED]"
        assert cleaned["password_confirm"] == "[REDACTED]"
        assert cleaned["access_token"] == "[REDACTED]"
        assert cleaned["api_key"] == "[REDACTED]"
        assert cleaned["clinical_notes"] == "Patient feeling well"

    def test_admin_can_view_and_filter_audit_logs(self, auth_client, admin_user, patient_user):
        log_audit_event(
            event_type="AUTH_LOGIN",
            actor=patient_user,
            resource_type="User",
            resource_id=str(patient_user.id),
            action="USER_LOGIN_SUCCESS",
            details={"email": patient_user.email},
            is_success=True,
        )
        log_audit_event(
            event_type="ADMIN_ACTION",
            actor=admin_user,
            resource_type="System",
            action="GLOBAL_CONFIG_UPDATE",
            is_success=True,
        )

        client = auth_client(admin_user)
        response = client.get("/api/v1/audit/logs/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] >= 2

        # Filter by event_type
        filtered_resp = client.get("/api/v1/audit/logs/?event_type=ADMIN_ACTION")
        assert filtered_resp.status_code == status.HTTP_200_OK
        results = filtered_resp.json()["results"]
        assert all(log["event_type"] == "ADMIN_ACTION" for log in results)

    def test_ordinary_users_cannot_access_audit_logs(self, auth_client, patient_user, doctor_user):
        pat_client = auth_client(patient_user)
        doc_client = auth_client(doctor_user)

        assert pat_client.get("/api/v1/audit/logs/").status_code == status.HTTP_403_FORBIDDEN
        assert doc_client.get("/api/v1/audit/logs/").status_code == status.HTTP_403_FORBIDDEN
