"""
URL configuration for VakCare project.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # API Documentation (drf-spectacular)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # API v1 routes
    path("api/v1/health/", include("apps.common.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/patients/", include("apps.patients.urls")),
    path("api/v1/doctors/", include("apps.doctors.urls")),
    path("api/v1/appointments/", include("apps.appointments.urls")),
    path("api/v1/medical-records/", include("apps.medical_records.urls")),
    path("api/v1/prescriptions/", include("apps.prescriptions.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/ai/", include("apps.ai_assistant.urls")),
    path("api/v1/audit/", include("apps.audit.urls")),
]
