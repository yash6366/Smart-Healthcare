import pytest
from rest_framework import status


@pytest.mark.django_db
class TestHealthChecks:
    def test_liveness_check(self, api_client):
        response = api_client.get("/api/v1/health/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "vakcare-backend"
        # Verify no sensitive credentials leaked
        assert "password" not in str(data).lower()
        assert "secret" not in str(data).lower()

    def test_readiness_check(self, api_client):
        response = api_client.get("/api/v1/health/ready/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"

    def test_openapi_schema_endpoint(self, api_client):
        response = api_client.get("/api/schema/")
        assert response.status_code == status.HTTP_200_OK

    def test_swagger_ui_endpoint(self, api_client):
        response = api_client.get("/api/docs/")
        assert response.status_code == status.HTTP_200_OK
