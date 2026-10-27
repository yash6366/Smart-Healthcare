# VakCare — Automated Testing & Quality Assurance Manual

## 1. Test Architecture Overview

VakCare includes a comprehensive automated test suite engineered with **Pytest** and **pytest-django**. The suite rigorously validates business logic, concurrency constraints, role boundaries, security policies, and external provider fallbacks across all 10 domain applications.

### Key Metrics
- **Total Test Cases**: 68 automated unit & integration tests
- **Passing Rate**: 100% (68 / 68 passed)
- **Execution Engine**: `pytest 9.1.1` with `pytest-django 4.14.0`
- **Execution Speed**: $\approx 50$ seconds for full end-to-end execution
- **Database Engine**: In-memory SQLite during testing (`USE_SQLITE_FOR_TESTS=True`) or PostgreSQL/MySQL when configured.

---

## 2. Test Configuration & Fixtures

### 2.1 Configuration Files
- **`backend/pytest.ini`**:
  ```ini
  [pytest]
  DJANGO_SETTINGS_MODULE = config.settings.development
  python_files = tests.py test_*.py *_tests.py
  testpaths = tests apps
  addopts = --strict-markers -ra --tb=short
  filterwarnings =
      ignore::DeprecationWarning
      ignore::PendingDeprecationWarning
  ```
- **`backend/tests/conftest.py`**:
  Provides reusable Pytest fixtures:
  - `api_client`: Unauthenticated REST Framework test client.
  - `authenticated_client(user)`: Client pre-authenticated with JWT Bearer token.
  - `patient_user`, `patient_profile`: Pre-configured patient account.
  - `doctor_user`, `doctor_profile`: Pre-configured, verified medical doctor account.
  - `admin_user`: Pre-configured platform administrator account.

---

## 3. Test Suite Matrix (68 Test Cases)

| Test Module | Test Count | Primary Scenarios Covered |
| :--- | :---: | :--- |
| **`test_authentication.py`** | 13 | Patient registration, username/email uniqueness validation, password complexity, login credential verification, JWT token issuance, rotated refresh token exchange, token blacklist on logout, password change verification, HttpOnly cookie setting. |
| **`test_authorization.py`** | 9 | `IsPatient`, `IsDoctor`, `IsAdministrator`, `IsDoctorOrAdmin`, and `IsOwnerOrAdmin` permission enforcement across protected endpoints. Verification of 403 Forbidden responses for unauthorized cross-role attempts. |
| **`test_appointments.py`** | 9 | Concurrency-safe slot creation, atomic double-booking rejection, past-datetime rejection, doctor working hours boundary checks, state machine transitions (`CONFIRMED`, `REJECTED`, `CANCELLED`, `COMPLETED`), cancellation reason capture, and notification dispatch. |
| **`test_doctors.py`** | 6 | Public directory search, specialization filtering, fee filtering, ordering by consultation fee / experience, administrative doctor account provisioning, and credential verification approval/revocation. |
| **`test_patients.py`** | 4 | Patient profile self-retrieval, partial demographic updates (emergency contact, blood group, address), and user synchronization. |
| **`test_medical_records_and_prescriptions.py`** | 7 | Electronic health record creation by verified doctors, patient isolation (patients view only own records), multi-item prescription creation with dosages, and automated patient notification issuance. |
| **`test_ai_assistant.py`** | 5 | Deterministic mock triage guidance, mandatory clinical disclaimer verification, emergency symptom detection, medical record summarization permissions, multi-turn conversational message persistence, and owner-only isolation. |
| **`test_audit.py`** | 3 | Immutable audit log creation, automated password/token payload sanitization (`[REDACTED]`), and administrator-only audit log querying. |
| **`test_health.py`** | 4 | System liveness probe (`/api/v1/health/`), database readiness probe (`/api/v1/health/ready/`), response structure, and unauthenticated access verification. |
| **`test_phase_f_features.py`** | 8 | End-to-end integration workflows: Doctor daily schedule view (`DoctorDailyScheduleView`), chronological health timeline aggregator (`PatientHealthTimelineView`), doctor-patient consultation relationship check for clinical history (`PatientClinicalHistoryView`), in-app notification center, and automated appointment reminder generator (`generate_appointment_reminders`). |

---

## 4. Running the Test Suite

### 4.1 Running All Tests
```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1    # On Windows
source .venv/bin/activate       # On Linux/macOS

# Execute full test suite
pytest backend/tests
```

### 4.2 Running a Specific Test Module
```bash
# Test appointments state machine & concurrency:
pytest backend/tests/test_appointments.py

# Test AI Assistant guidance and safety disclaimers:
pytest backend/tests/test_ai_assistant.py

# Test authentication and JWT token lifecycle:
pytest backend/tests/test_authentication.py
```

### 4.3 Running with Verbose Output
```bash
pytest backend/tests -v
```

### 4.4 Generating Coverage Reports
```bash
pytest backend/tests --cov=backend/apps --cov-report=term-missing
```

---

## 5. Quality Assurance Checklist

Prior to production releases, confirm that:
1. `pytest backend/tests` exits with code `0` (all 68 tests passing).
2. `python backend/manage.py check --deploy --settings=config.settings.production` reports no critical security warnings.
3. Database migrations apply cleanly (`python backend/manage.py migrate --check`).
4. Frontend assets contain no broken links and execute cleanly across Chromium, Firefox, and WebKit browsers.
