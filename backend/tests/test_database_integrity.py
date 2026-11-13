import importlib
import os
import sys
from io import StringIO

import pytest
from django.apps import apps
from django.contrib import admin
from django.core.management import call_command
from django.db import models

from apps.accounts.models import User
from apps.ai_assistant.models import Conversation, Message
from apps.appointments.models import Appointment
from apps.audit.models import AuditLog
from apps.doctors.models import DoctorProfile
from apps.medical_records.models import MedicalRecord
from apps.notifications.models import Notification
from apps.patients.models import PatientProfile
from apps.prescriptions.models import Prescription, PrescriptionItem


EXPECTED_LOGICAL_TABLES = {
    "CORE": {
        "accounts.User": "accounts_user",
        "patients.PatientProfile": "patients_patientprofile",
        "doctors.DoctorProfile": "doctors_doctorprofile",
    },
    "HEALTHCARE": {
        "appointments.Appointment": "appointments_appointment",
        "medical_records.MedicalRecord": "medical_records_medicalrecord",
        "prescriptions.Prescription": "prescriptions_prescription",
        "prescriptions.PrescriptionItem": "prescriptions_prescriptionitem",
    },
    "COMMUNICATION": {
        "notifications.Notification": "notifications_notification",
        "ai_assistant.Conversation": "ai_assistant_conversation",
        "ai_assistant.Message": "ai_assistant_message",
    },
    "SECURITY": {
        "audit.AuditLog": "audit_auditlog",
        "token_blacklist.OutstandingToken": "token_blacklist_outstandingtoken",
        "token_blacklist.BlacklistedToken": "token_blacklist_blacklistedtoken",
    },
}


class TestDatabaseStructureAndSync:
    def test_logical_domain_table_names_match_contract(self):
        for _category, mapping in EXPECTED_LOGICAL_TABLES.items():
            for label, expected_table in mapping.items():
                model = apps.get_model(label)
                assert model._meta.db_table == expected_table

    def test_all_domain_models_have_explicit_ordering_and_admin_registration(self):
        domain_models = [
            User,
            PatientProfile,
            DoctorProfile,
            Appointment,
            MedicalRecord,
            Prescription,
            PrescriptionItem,
            Notification,
            Conversation,
            Message,
            AuditLog,
        ]
        for model in domain_models:
            assert model._meta.ordering, f"{model.__name__} must define explicit Meta.ordering"
            assert model in admin.site._registry, f"{model.__name__} must be registered in Django Admin"

        audit_admin = admin.site._registry[AuditLog]
        assert not audit_admin.has_add_permission(None)
        assert not audit_admin.has_change_permission(None)
        assert not audit_admin.has_delete_permission(None)

    def test_redundant_indexes_removed_from_models(self):
        # Single-column db_index must not duplicate unique or leftmost composite index prefixes
        assert User._meta.get_field("email").unique is True
        assert User._meta.get_field("email").db_index is False
        assert not User._meta.indexes

        assert DoctorProfile._meta.get_field("specialization").db_index is False
        assert Appointment._meta.get_field("status").db_index is False
        assert AuditLog._meta.get_field("event_type").db_index is False
        assert not PatientProfile._meta.indexes

    def test_referential_delete_policies_preserve_clinical_and_audit_integrity(self):
        assert Appointment._meta.get_field("patient").remote_field.on_delete is models.PROTECT
        assert Appointment._meta.get_field("doctor").remote_field.on_delete is models.PROTECT
        assert Appointment._meta.get_field("cancelled_by").remote_field.on_delete is models.SET_NULL
        assert MedicalRecord._meta.get_field("patient").remote_field.on_delete is models.CASCADE
        assert MedicalRecord._meta.get_field("doctor").remote_field.on_delete is models.SET_NULL
        assert Prescription._meta.get_field("patient").remote_field.on_delete is models.PROTECT
        assert Prescription._meta.get_field("doctor").remote_field.on_delete is models.PROTECT
        assert Prescription._meta.get_field("appointment").remote_field.on_delete is models.SET_NULL
        assert PrescriptionItem._meta.get_field("prescription").remote_field.on_delete is models.CASCADE
        assert AuditLog._meta.get_field("actor").remote_field.on_delete is models.SET_NULL

    @pytest.mark.django_db
    def test_no_pending_django_migrations_drift(self):
        out = StringIO()
        call_command("makemigrations", check=True, dry_run=True, stdout=out)
        assert "No changes detected" in out.getvalue()


class TestDatabaseEnvironmentPrecedence:
    def _reload_base_settings(self, monkeypatch, env_updates, dotenv_map=None):
        """Reload config.settings.base cleanly with mocked os.environ and dotenv files."""
        import config.settings.base as base_settings

        snapshot = dict(os.environ)
        dotenv_map = dotenv_map or {}

        def fake_exists(path_obj):
            return str(path_obj).replace("\\", "/") in dotenv_map

        def fake_dotenv_values(path_obj):
            return dotenv_map.get(str(path_obj).replace("\\", "/"), {})

        try:
            os.environ.clear()
            os.environ.update(snapshot)
            for key in (
                "DB_ENVIRONMENT",
                "VERCEL",
                "AWS_LAMBDA_FUNCTION_NAME",
                "DATABASE_URL",
                "AIVEN_DATABASE_URL",
                "DB_ENGINE",
                "DB_NAME",
                "DB_USER",
                "DB_PASSWORD",
                "DB_HOST",
                "DB_PORT",
                "DB_SSL_REQUIRE",
                "DB_CONN_MAX_AGE",
                "AIVEN_DB_ENGINE",
                "AIVEN_DB_NAME",
                "AIVEN_DB_USER",
                "AIVEN_DB_PASSWORD",
                "AIVEN_DB_HOST",
                "AIVEN_DB_PORT",
            ):
                os.environ.pop(key, None)

            for k, v in env_updates.items():
                if v is not None:
                    os.environ[k] = v

            from pathlib import Path
            monkeypatch.setattr(Path, "exists", fake_exists)
            monkeypatch.setattr("dotenv.dotenv_values", fake_dotenv_values)

            sys.modules.pop("config.settings.base", None)
            reloaded = importlib.import_module("config.settings.base")
            return reloaded
        finally:
            os.environ.clear()
            os.environ.update(snapshot)
            sys.modules["config.settings.base"] = base_settings

    def test_os_env_db_environment_overrides_dotenv_local(self, monkeypatch):
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parent.parent
        root_dir = backend_dir.parent

        dotenv_map = {
            str(root_dir / ".env").replace("\\", "/"): {
                "DB_ENVIRONMENT": "local",
                "DB_HOST": "127.0.0.1",
                "DB_NAME": "vakcare_db",
            },
            str(root_dir / ".env.aiven").replace("\\", "/"): {
                "DB_ENVIRONMENT": "aiven",
                "DATABASE_URL": "mysql://avnadmin:secret@example-cloud.aivencloud.com:12289/defaultdb?ssl-mode=REQUIRED",
            },
        }
        mod = self._reload_base_settings(monkeypatch, {"DB_ENVIRONMENT": "aiven"}, dotenv_map)
        assert mod.DB_ENVIRONMENT == "aiven"
        assert mod.DATABASES["default"]["HOST"] == "example-cloud.aivencloud.com"
        assert mod.DATABASES["default"]["PORT"] == "12289"
        assert mod.DATABASES["default"]["NAME"] == "defaultdb"
        assert mod.DATABASES["default"]["OPTIONS"] == {"ssl": {"ssl_mode": "REQUIRED"}}

    def test_os_env_database_url_overrides_dotenv_files(self, monkeypatch):
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parent.parent
        root_dir = backend_dir.parent

        dotenv_map = {
            str(backend_dir / ".env").replace("\\", "/"): {
                "DB_ENVIRONMENT": "local",
                "AIVEN_DATABASE_URL": "mysql://fileuser:filepass@file-host.aivencloud.com:12289/defaultdb",
            },
            str(root_dir / ".env.aiven").replace("\\", "/"): {
                "DATABASE_URL": "mysql://fileuser:filepass@file-host.aivencloud.com:12289/defaultdb",
            },
        }
        mod = self._reload_base_settings(
            monkeypatch,
            {
                "DB_ENVIRONMENT": "aiven",
                "DATABASE_URL": "mysql://osuser:ospass@os-override.aivencloud.com:25060/customdb",
            },
            dotenv_map,
        )
        assert mod.DATABASES["default"]["HOST"] == "os-override.aivencloud.com"
        assert mod.DATABASES["default"]["PORT"] == "25060"
        assert mod.DATABASES["default"]["NAME"] == "customdb"
        assert mod.DATABASES["default"]["USER"] == "osuser"

    def test_serverless_vercel_defaults_to_aiven_without_dotenv_override(self, monkeypatch):
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parent.parent
        root_dir = backend_dir.parent

        dotenv_map = {
            str(root_dir / ".env").replace("\\", "/"): {
                "DB_ENVIRONMENT": "local",
                "DB_HOST": "127.0.0.1",
            },
        }
        mod = self._reload_base_settings(
            monkeypatch,
            {
                "VERCEL": "1",
                "DATABASE_URL": "mysql://verceluser:pass@vercel-db.aivencloud.com:12289/defaultdb",
            },
            dotenv_map,
        )
        assert mod.DB_ENVIRONMENT == "aiven"
        assert mod.DATABASES["default"]["HOST"] == "vercel-db.aivencloud.com"
        assert mod.DATABASES["default"]["CONN_MAX_AGE"] == 0

    def test_invalid_db_environment_raises_runtime_error(self, monkeypatch):
        with pytest.raises(RuntimeError, match="Invalid DB_ENVIRONMENT"):
            self._reload_base_settings(monkeypatch, {"DB_ENVIRONMENT": "staging"})

    def test_aiven_rejects_localhost_host(self, monkeypatch):
        with pytest.raises(RuntimeError, match="DATABASE SAFETY VIOLATION"):
            self._reload_base_settings(
                monkeypatch,
                {"DB_ENVIRONMENT": "aiven", "DB_HOST": "127.0.0.1"},
            )

    def test_local_rejects_aiven_host(self, monkeypatch):
        with pytest.raises(RuntimeError, match="DATABASE SAFETY VIOLATION"):
            self._reload_base_settings(
                monkeypatch,
                {"DB_ENVIRONMENT": "local", "DB_HOST": "my-db.aivencloud.com"},
            )


