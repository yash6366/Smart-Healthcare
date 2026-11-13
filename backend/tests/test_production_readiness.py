import io
import json
import logging
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time, timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management import call_command
from django.db import connection
from django.db.models.deletion import ProtectedError
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework import status

from apps.accounts.models import User
from apps.ai_assistant.providers.base import DISCLAIMER_TEXT, redact_secret
from apps.ai_assistant.providers.factory import get_ai_provider
from apps.ai_assistant.providers.gemini_provider import GeminiAIProvider
from apps.ai_assistant.providers.mock_provider import MockAIProvider
from apps.ai_assistant.providers.openai_provider import OpenAIProvider
from apps.appointments.models import Appointment
from apps.appointments.services import confirm_appointment, create_appointment
from apps.doctors.models import DoctorProfile
from apps.medical_records.models import MedicalRecord
from apps.notifications.models import Notification
from apps.prescriptions.models import Prescription, PrescriptionItem


@pytest.mark.django_db
class TestOpenAPISchemaReadiness:
    def test_spectacular_schema_generates_zero_warnings_and_errors(self):
        import os
        from drf_spectacular.generators import SchemaGenerator

        out = io.StringIO()
        err = io.StringIO()
        call_command(
            "spectacular",
            validate=True,
            fail_on_warn=True,
            file=os.devnull,
            stdout=out,
            stderr=err,
        )
        schema = SchemaGenerator().get_schema(request=None, public=True)

        assert "paths" in schema
        assert schema["info"]["version"] == "1.0.0"

        expected_paths = [
            "/api/v1/auth/register/",
            "/api/v1/auth/login/",
            "/api/v1/auth/refresh/",
            "/api/v1/patients/me/timeline/",
            "/api/v1/patients/{id}/clinical-history/",
            "/api/v1/appointments/daily-schedule/",
            "/api/v1/notifications/{id}/read/",
            "/api/v1/notifications/trigger-reminders/",
            "/api/v1/ai/conversations/",
            "/api/v1/ai/conversations/{id}/",
            "/api/v1/audit/analytics/",
            "/api/v1/health/",
            "/api/v1/health/ready/",
        ]
        for path in expected_paths:
            assert path in schema["paths"], f"Missing documented API path: {path}"

        # Ensure POST alias on notification mark-read is cleanly documented
        mark_read_ops = schema["paths"]["/api/v1/notifications/{id}/read/"]
        assert "patch" in mark_read_ops
        assert "post" in mark_read_ops

        # Ensure JWT security scheme exists
        security_schemes = schema.get("components", {}).get("securitySchemes", {})
        assert "jwtAuth" in security_schemes

    def test_production_swagger_gates_to_admin_when_disabled(self):
        # Verify production settings specify IsAdminUser for SERVE_PERMISSIONS
        import importlib
        prod_settings = importlib.import_module("config.settings.production")
        assert prod_settings.SPECTACULAR_SETTINGS.get("SERVE_PERMISSIONS") == [
            "rest_framework.permissions.IsAdminUser"
        ]


@pytest.mark.django_db
class TestSecurityHardening:
    def test_base_settings_disallow_wildcard_hosts_and_vercel_cors_by_default(self, monkeypatch):
        import importlib
        import os
        import sys
        from pathlib import Path

        import config.settings.base as original_base

        snapshot = dict(os.environ)
        try:
            monkeypatch.setattr(Path, "exists", lambda _self: False)
            monkeypatch.setattr("dotenv.dotenv_values", lambda _path: {})

            for k in (
                "DJANGO_ALLOWED_HOSTS",
                "VERCEL_URL",
                "VERCEL_PROJECT_PRODUCTION_URL",
                "VERCEL_BRANCH_URL",
                "ALLOW_ALL_VERCEL_HOSTS",
                "CORS_ALLOW_VERCEL_PREVIEWS",
                "CSRF_TRUSTED_ORIGINS",
                "CORS_ALLOWED_ORIGINS",
            ):
                os.environ.pop(k, None)
            os.environ["DB_ENVIRONMENT"] = "local"
            os.environ["VERCEL_URL"] = "vakcare-app-123.vercel.app"
            os.environ["VERCEL_PROJECT_PRODUCTION_URL"] = "vakcare.vercel.app"

            sys.modules.pop("config.settings.base", None)
            mod = importlib.import_module("config.settings.base")

            assert "*" not in mod.ALLOWED_HOSTS
            assert ".vercel.app" not in mod.ALLOWED_HOSTS
            assert "vakcare-app-123.vercel.app" in mod.ALLOWED_HOSTS
            assert "vakcare.vercel.app" in mod.ALLOWED_HOSTS
            assert not getattr(mod, "CORS_ALLOWED_ORIGIN_REGEXES", [])
            assert "https://*.vercel.app" not in mod.CSRF_TRUSTED_ORIGINS
            assert "https://vakcare-app-123.vercel.app" in mod.CORS_ALLOWED_ORIGINS
            assert "https://vakcare.vercel.app" in mod.CSRF_TRUSTED_ORIGINS
        finally:
            os.environ.clear()
            os.environ.update(snapshot)
            sys.modules["config.settings.base"] = original_base

    def test_csp_connect_src_restricted_to_self_in_production_debug_false(self, api_client, settings):
        settings.DEBUG = False
        res = api_client.get("/api/v1/health/")
        assert res.status_code == status.HTTP_200_OK
        csp = res.headers.get("Content-Security-Policy", "")
        assert "connect-src 'self';" in csp
        assert "http://127.0.0.1:8000" not in csp
        assert "ws://" not in csp
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_cookie_refresh_view_has_auth_throttle_and_samesite_delete(self, api_client, patient_user):
        from apps.accounts.views import CookieTokenRefreshView, REFRESH_COOKIE_NAME

        assert CookieTokenRefreshView.throttle_scope == "auth"

        login_res = api_client.post(
            "/api/v1/auth/login/",
            {"email_or_username": patient_user.email, "password": "SecurePassword123!"},
        )
        assert login_res.status_code == status.HTTP_200_OK
        access = login_res.json()["tokens"]["access"]
        refresh = login_res.json()["tokens"]["refresh"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        logout_res = api_client.post("/api/v1/auth/logout/", {"refresh": refresh})
        assert logout_res.status_code == status.HTTP_200_OK
        assert logout_res.cookies[REFRESH_COOKIE_NAME]["samesite"] == "Lax"

    def test_unverified_doctor_cannot_access_patient_phi_endpoints(
        self, auth_client, unverified_doctor_user, patient_user
    ):
        client = auth_client(unverified_doctor_user)
        patient_id = patient_user.patient_profile.id

        assert client.get("/api/v1/patients/").status_code == status.HTTP_403_FORBIDDEN
        assert client.get(f"/api/v1/patients/{patient_id}/clinical-history/").status_code == status.HTTP_403_FORBIDDEN
        assert client.get("/api/v1/medical-records/").status_code == status.HTTP_403_FORBIDDEN
        assert client.get("/api/v1/appointments/daily-schedule/").status_code == status.HTTP_403_FORBIDDEN

    def test_malformed_query_parameters_return_400_instead_of_500(
        self, auth_client, patient_user, doctor_user, admin_user
    ):
        pat_client = auth_client(patient_user)
        assert pat_client.get("/api/v1/appointments/?date=not-a-date").status_code == status.HTTP_400_BAD_REQUEST
        assert pat_client.get("/api/v1/appointments/?doctor_id=abc").status_code == status.HTTP_400_BAD_REQUEST
        assert pat_client.get("/api/v1/patients/me/timeline/?start_date=bad").status_code == status.HTTP_400_BAD_REQUEST
        assert pat_client.get("/api/v1/patients/me/timeline/?end_date=bad").status_code == status.HTTP_400_BAD_REQUEST
        assert pat_client.get("/api/v1/patients/me/timeline/?event_type=INVALID").status_code == status.HTTP_400_BAD_REQUEST
        assert pat_client.get("/api/v1/doctors/?max_fee=abc").status_code == status.HTTP_400_BAD_REQUEST
        assert pat_client.get("/api/v1/doctors/?max_fee=-10").status_code == status.HTTP_400_BAD_REQUEST

        doc_client = auth_client(doctor_user)
        assert doc_client.get("/api/v1/medical-records/?patient_id=abc").status_code == status.HTTP_400_BAD_REQUEST

        adm_client = auth_client(admin_user)
        assert adm_client.get("/api/v1/appointments/daily-schedule/?doctor_id=abc").status_code == status.HTTP_400_BAD_REQUEST
        assert adm_client.get("/api/v1/doctors/?is_verified=maybe").status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_can_filter_unverified_doctors_while_public_cannot_see_them(
        self, api_client, auth_client, admin_user, doctor_user, unverified_doctor_user
    ):
        # Public / anonymous cannot bypass verification with is_verified=false
        pub_res = api_client.get("/api/v1/doctors/?is_verified=false")
        assert pub_res.status_code == status.HTTP_200_OK
        pub_ids = [d["id"] for d in pub_res.json()["results"]]
        assert unverified_doctor_user.doctor_profile.id not in pub_ids

        # Admin explicitly filters verification queue
        adm_client = auth_client(admin_user)
        adm_res = adm_client.get("/api/v1/doctors/?is_verified=false")
        assert adm_res.status_code == status.HTTP_200_OK
        adm_ids = [d["id"] for d in adm_res.json()["results"]]
        assert unverified_doctor_user.doctor_profile.id in adm_ids
        assert doctor_user.doctor_profile.id not in adm_ids


@pytest.mark.django_db
class TestDatabaseTransactionsAndPerformance:
    def test_appointment_creation_rolls_back_atomically_on_notification_failure(
        self, patient_user, doctor_user
    ):
        target_date = date.today() + timedelta(days=5)
        with patch("apps.appointments.services.send_notification", side_effect=RuntimeError("Simulated broker outage")):
            with pytest.raises(RuntimeError, match="Simulated broker outage"):
                create_appointment(
                    patient=patient_user.patient_profile,
                    doctor=doctor_user.doctor_profile,
                    appointment_date=target_date,
                    start_time=time(10, 0),
                    duration_minutes=30,
                    reason="Atomic rollback test",
                )

        assert not Appointment.objects.filter(
            patient=patient_user.patient_profile,
            appointment_date=target_date,
            start_time=time(10, 0),
        ).exists()

    def test_protected_foreign_keys_prevent_clinical_history_orphan(
        self, patient_user, doctor_user
    ):
        Appointment.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            appointment_date=date.today() + timedelta(days=6),
            start_time=time(11, 0),
            end_time=time(11, 30),
            reason="Protect policy verification",
        )
        with pytest.raises(ProtectedError):
            doctor_user.doctor_profile.delete()
        with pytest.raises(ProtectedError):
            patient_user.patient_profile.delete()

    def test_appointment_booking_race_conditions_and_slot_overlap_prevention(
        self, patient_user, second_patient_user, doctor_user, db
    ):
        target_date = date.today() + timedelta(days=7)

        # Create a second verified doctor for testing cross-doctor simultaneous booking
        second_doc_u = User.objects.create_user(
            username="dr_unrelated_pr",
            email="unrelated_pr@vakcare.com",
            password="SecurePass123!",
            role=User.Role.DOCTOR,
            is_verified=True,
        )
        second_doc = DoctorProfile.objects.create(
            user=second_doc_u,
            display_name="Dr. Unrelated",
            specialization=DoctorProfile.Specialization.DERMATOLOGY,
            is_verified=True,
            is_available=True,
        )

        # 1. Initial valid booking succeeds
        first_appt = create_appointment(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            appointment_date=target_date,
            start_time=time(15, 0),
            duration_minutes=30,
            reason="Primary slot booking",
        )
        assert first_appt.status == Appointment.Status.PENDING

        # 2. Competing patient attempting exact same doctor slot is rejected
        with pytest.raises(DjangoValidationError, match="Doctor already has an active appointment"):
            create_appointment(
                patient=second_patient_user.patient_profile,
                doctor=doctor_user.doctor_profile,
                appointment_date=target_date,
                start_time=time(15, 0),
                duration_minutes=30,
                reason="Competing booking for occupied slot",
            )

        # 3. Competing patient attempting partially overlapping slot (e.g. 15:15 - 15:45) is rejected
        with pytest.raises(DjangoValidationError, match="Doctor already has an active appointment"):
            create_appointment(
                patient=second_patient_user.patient_profile,
                doctor=doctor_user.doctor_profile,
                appointment_date=target_date,
                start_time=time(15, 15),
                duration_minutes=30,
                reason="Partial overlap booking",
            )

        # 4. Same patient attempting simultaneous booking with another doctor is rejected
        with pytest.raises(DjangoValidationError, match="Patient already has an active appointment"):
            create_appointment(
                patient=patient_user.patient_profile,
                doctor=second_doc,
                appointment_date=target_date,
                start_time=time(15, 0),
                duration_minutes=30,
                reason="Patient double-booking across doctors",
            )

        # 5. After cancellation, slot becomes available again
        from apps.appointments.services import cancel_appointment
        cancel_appointment(first_appt, actor=patient_user, reason="Need to reschedule")
        first_appt.refresh_from_db()
        assert first_appt.status == Appointment.Status.CANCELLED

        second_appt = create_appointment(
            patient=second_patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            appointment_date=target_date,
            start_time=time(15, 0),
            duration_minutes=30,
            reason="Booking freed-up slot",
        )
        assert second_appt.status == Appointment.Status.PENDING

    def test_list_endpoints_avoid_n_plus_1_queries(
        self, auth_client, patient_user, doctor_user
    ):
        base_date = date.today() + timedelta(days=10)
        for i in range(6):
            appt = Appointment.objects.create(
                patient=patient_user.patient_profile,
                doctor=doctor_user.doctor_profile,
                appointment_date=base_date + timedelta(days=i),
                start_time=time(10, 0),
                end_time=time(10, 30),
                reason=f"Query check {i}",
            )
            MedicalRecord.objects.create(
                patient=patient_user.patient_profile,
                doctor=doctor_user.doctor_profile,
                record_type="CONSULTATION_NOTE",
                title=f"Record {i}",
                description="Notes",
            )
            rx = Prescription.objects.create(
                patient=patient_user.patient_profile,
                doctor=doctor_user.doctor_profile,
                appointment=appt,
                diagnosis=f"Diag {i}",
            )
            PrescriptionItem.objects.create(
                prescription=rx,
                medication_name="Vitamin D3",
                dosage="1000 IU",
                frequency="Once daily",
                duration="30 days",
            )

        pat_client = auth_client(patient_user)
        with CaptureQueriesContext(connection) as appts_ctx:
            res_appts = pat_client.get("/api/v1/appointments/")
        assert res_appts.status_code == status.HTTP_200_OK
        assert len(appts_ctx) <= 6

        with CaptureQueriesContext(connection) as rx_ctx:
            res_rx = pat_client.get("/api/v1/prescriptions/")
        assert res_rx.status_code == status.HTTP_200_OK
        assert len(rx_ctx) <= 7

        with CaptureQueriesContext(connection) as tl_ctx:
            res_tl = pat_client.get("/api/v1/patients/me/timeline/")
        assert res_tl.status_code == status.HTTP_200_OK
        assert len(tl_ctx) <= 10


@pytest.mark.django_db
class TestAIProviderResilience:
    def test_factory_and_openai_model_resolution(self, settings):
        settings.AI_PROVIDER = "gemini"
        assert isinstance(get_ai_provider(), GeminiAIProvider)

        settings.AI_PROVIDER = "openai"
        settings.AI_PROVIDER_MODEL = "gemini-2.5-flash"  # Simulate default from base.py
        provider = get_ai_provider()
        assert isinstance(provider, OpenAIProvider)
        assert provider.model == "gpt-4o-mini"

        settings.AI_PROVIDER = "mock"
        assert isinstance(get_ai_provider(), MockAIProvider)

    def test_gemini_provider_propagates_history_context_and_triage_metadata(self, settings):
        settings.AI_PROVIDER = "gemini"
        settings.AI_PROVIDER_API_KEY = "test-secret-gemini-key"
        settings.AI_PROVIDER_MODEL = "gemini-2.5-flash"

        captured = {}

        def fake_post(url, payload, headers, timeout=10):
            captured["url"] = url
            captured["payload"] = payload
            captured["headers"] = headers
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "Mild seasonal itching rash can improve with gentle cleansing."}]
                        }
                    }
                ]
            }

        provider = GeminiAIProvider()
        with patch("apps.ai_assistant.providers.gemini_provider.post_json", side_effect=fake_post):
            res = provider.generate_guidance(
                "My skin rash is still itchy today",
                context={"history": [{"role": "USER", "content": "I noticed a red rash yesterday."}]},
            )

        assert res["provider"] == "Gemini (gemini-2.5-flash)"
        assert res["suggested_specialization"] == "DERMATOLOGY"
        assert res["is_emergency_alert"] is False
        assert res["disclaimer"] == DISCLAIMER_TEXT
        assert captured["headers"]["x-goog-api-key"] == "test-secret-gemini-key"
        assert "key=" not in captured["url"]
        sent_prompt = captured["payload"]["contents"][0]["parts"][0]["text"]
        assert "noticed a red rash yesterday" in sent_prompt

    def test_gemini_fallback_and_secret_redaction_on_http_or_bad_payload(self, settings, caplog):
        settings.AI_PROVIDER_API_KEY = "AIzaVerySecretKeyValue999"
        provider = GeminiAIProvider()

        err = urllib.error.HTTPError(
            url="https://generativelanguage.googleapis.com/v1beta/models/x?key=AIzaVerySecretKeyValue999",
            code=503,
            msg="Service Unavailable Bearer topsecret-token-value",
            hdrs=None,
            fp=None,
        )
        with caplog.at_level(logging.WARNING, logger="apps.ai_assistant"):
            with patch("apps.ai_assistant.providers.gemini_provider.post_json", side_effect=err):
                fallback = provider.generate_guidance("chest tightness after stairs")

        assert "MockAIProvider" in fallback["provider"]
        assert fallback["is_emergency_alert"] is True
        assert "AIzaVerySecretKeyValue999" not in caplog.text
        assert "topsecret-token-value" not in caplog.text
        assert "[REDACTED]" in caplog.text

        # Empty / malformed API payload also falls back cleanly
        with patch("apps.ai_assistant.providers.gemini_provider.post_json", return_value={"candidates": []}):
            summary_fallback = provider.summarize_medical_record("CBC", "Normal white cell count", {"wbc": 6200})
        assert "MockAIProvider" in summary_fallback["provider"]
        assert "DOCUMENTED CLINICAL FACTS" in summary_fallback["summary"]

    def test_redact_secret_helper_strips_keys_and_bearer_tokens(self):
        exc = RuntimeError("Error calling ?key=secret123 with Bearer tok_abc_999 and raw my_key")
        sanitized = redact_secret(exc, "my_key")
        assert "my_key" not in sanitized
        assert "secret123" not in sanitized
        assert "tok_abc_999" not in sanitized


@pytest.mark.django_db
class TestEndToEndClinicalWorkflows:
    def test_full_patient_doctor_admin_workflow_and_audit_trail(
        self, auth_client, doctor_user, admin_user, settings
    ):
        from rest_framework.test import APIClient

        settings.AI_PROVIDER = "mock"
        anon = APIClient()
        # 1. Patient registers & logs in
        reg_res = anon.post(
            "/api/v1/auth/register/",
            {
                "username": "e2e_patient",
                "email": "e2e_patient@example.com",
                "password": "StrongPatientPassword123!",
                "password_confirm": "StrongPatientPassword123!",
                "first_name": "Anita",
                "last_name": "Verma",
            },
        )
        assert reg_res.status_code == status.HTTP_201_CREATED
        assert reg_res.json()["user"]["role"] == "PATIENT"

        login_res = anon.post(
            "/api/v1/auth/login/",
            {"email_or_username": "e2e_patient@example.com", "password": "StrongPatientPassword123!"},
        )
        assert login_res.status_code == status.HTTP_200_OK
        patient_access = login_res.json()["tokens"]["access"]
        pat_client = APIClient()
        pat_client.credentials(HTTP_AUTHORIZATION=f"Bearer {patient_access}")

        # 2. Patient discovers verified doctor and books appointment
        docs_res = pat_client.get("/api/v1/doctors/?specialization=CARDIOLOGY")
        assert docs_res.status_code == status.HTTP_200_OK
        target_doc_id = doctor_user.doctor_profile.id

        appt_date = (date.today() + timedelta(days=3)).isoformat()
        book_res = pat_client.post(
            "/api/v1/appointments/",
            {
                "doctor_id": target_doc_id,
                "appointment_date": appt_date,
                "start_time": "10:00:00",
                "duration_minutes": 30,
                "reason": "Annual cardiac wellness evaluation",
            },
        )
        assert book_res.status_code == status.HTTP_201_CREATED
        appt_id = book_res.json()["appointment"]["id"]

        # 3. Doctor sees daily schedule, confirms, completes, creates record, and prescribes
        doc_client = auth_client(doctor_user)
        sched_res = doc_client.get(f"/api/v1/appointments/daily-schedule/?date={appt_date}")
        assert sched_res.status_code == status.HTTP_200_OK
        assert sched_res.json()["kpis"]["PENDING"] >= 1

        assert doc_client.post(f"/api/v1/appointments/{appt_id}/confirm/").status_code == status.HTTP_200_OK
        assert doc_client.post(f"/api/v1/appointments/{appt_id}/complete/").status_code == status.HTTP_200_OK

        patient_profile_id = reg_res.json()["user"]["id"]
        from apps.patients.models import PatientProfile

        pat_profile = PatientProfile.objects.get(user_id=patient_profile_id)

        rec_res = doc_client.post(
            "/api/v1/medical-records/",
            {
                "patient_id": pat_profile.id,
                "record_type": "CONSULTATION_NOTE",
                "title": "Cardiac Wellness Check",
                "description": "Normal sinus rhythm, resting BP 118/78.",
                "clinical_data": {"bp": "118/78", "hr": 70},
            },
            format="json",
        )
        assert rec_res.status_code == status.HTTP_201_CREATED
        rec_id = rec_res.json()["record"]["id"]

        rx_res = doc_client.post(
            "/api/v1/prescriptions/",
            {
                "patient_id": pat_profile.id,
                "appointment_id": appt_id,
                "diagnosis": "Routine Cardiovascular Prevention",
                "items": [
                    {
                        "medication_name": "Omega-3 Fish Oil",
                        "dosage": "1000 mg",
                        "frequency": "Once daily",
                        "duration": "30 days",
                    }
                ],
            },
            format="json",
        )
        assert rx_res.status_code == status.HTTP_201_CREATED

        # 4. Patient reads timeline, summarizes record via AI, and marks notifications read
        tl_res = pat_client.get("/api/v1/patients/me/timeline/")
        assert tl_res.status_code == status.HTTP_200_OK
        assert tl_res.json()["total_events"] >= 3

        sum_res = pat_client.post("/api/v1/ai/summarize-record/", {"record_id": rec_id})
        assert sum_res.status_code == status.HTTP_200_OK
        assert "DISCLAIMER" in sum_res.json()["data"]["disclaimer"]

        notif_res = pat_client.get("/api/v1/notifications/?unread=true")
        assert notif_res.status_code == status.HTTP_200_OK
        assert len(notif_res.json()["results"]) >= 1
        notif_id = notif_res.json()["results"][0]["id"]
        mark_res = pat_client.post(f"/api/v1/notifications/{notif_id}/read/")
        assert mark_res.status_code == status.HTTP_200_OK
        assert mark_res.json()["notification"]["is_read"] is True

        # 5. Admin inspects analytics & audit trail
        adm_client = auth_client(admin_user)
        analytics_res = adm_client.get("/api/v1/audit/analytics/")
        assert analytics_res.status_code == status.HTTP_200_OK
        assert analytics_res.json()["clinical_volume"]["total_audit_events"] >= 5

