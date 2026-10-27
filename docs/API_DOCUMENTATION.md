# VakCare — RESTful API Reference Specification

## 1. Overview & Conventions

The VakCare API is built using **Django REST Framework** with token-based **JSON Web Token (JWT)** authentication, automated **OpenAPI 3.0** documentation (via `drf-spectacular`), and unified JSON response envelopes.

### Base URLs
- **Development**: `http://127.0.0.1:8000/api/v1/`
- **Production**: `https://<your-domain>/api/v1/`

### Interactive OpenAPI Documentation
- **Swagger UI**: `/api/docs/`
- **ReDoc UI**: `/api/redoc/`
- **OpenAPI Schema (JSON)**: `/api/schema/`

### Standard Response Envelope (Success)
```json
{
  "status": "success",
  "data": { ... }
}
```
*(Or the direct serialized object/list, depending on the endpoint)*

### Standard Error Envelope (Failures)
All client (4xx) and server (5xx) errors strictly conform to:
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human readable summary.",
    "details": {
      "field_name": ["Specific validation error"]
    }
  }
}
```

### Standard Error Codes
| Code | HTTP Status | Description |
| :--- | :---: | :--- |
| `VALIDATION_ERROR` | 400 | Request body or query parameters failed validation |
| `AUTHENTICATION_FAILED` | 401 | Missing, malformed, or expired Bearer token |
| `PERMISSION_DENIED` | 403 | Authenticated user lacks permission for this role/object |
| `RESOURCE_NOT_FOUND` | 404 | Target entity does not exist or belongs to another user |
| `CONFLICT` | 409 | State conflict (e.g., slot overlap or duplicate entry) |
| `RATE_LIMIT_EXCEEDED` | 429 | Throttling rate limit reached |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected uncaught exception |

### Authentication Header
Protected endpoints require:
```http
Authorization: Bearer <access_token>
```

---

## 2. API Endpoints by Domain

---

### Module 1: Authentication & Account Management (`/api/v1/auth/`)

#### 1. Register Patient
- **Method / Path**: `POST /api/v1/auth/register/`
- **Access**: Public (`AllowAny`)
- **Rate Limit**: Auth Throttle (`15/min` in prod, `300/min` in dev)
- **Request Body**:
```json
{
  "username": "johndoe",
  "email": "johndoe@example.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+919876543210"
}
```
- **Response (201 Created)**:
```json
{
  "status": "success",
  "message": "Account registered successfully. You can now log in.",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "johndoe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "PATIENT",
    "phone_number": "+919876543210",
    "is_verified": false
  }
}
```

#### 2. User Login
- **Method / Path**: `POST /api/v1/auth/login/`
- **Access**: Public (`AllowAny`)
- **Request Body**:
```json
{
  "email_or_username": "johndoe@example.com",
  "password": "SecurePassword123!"
}
```
- **Response (200 OK)**:
```json
{
  "status": "success",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "johndoe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "PATIENT",
    "phone_number": "+919876543210",
    "is_verified": false
  },
  "tokens": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```
*Sets HttpOnly cookie `vakcare_refresh_token`.*

#### 3. Refresh Access Token
- **Method / Path**: `POST /api/v1/auth/token/refresh/` (or `/api/v1/auth/refresh/`)
- **Access**: Public (accepts refresh token from body or HttpOnly cookie)
- **Request Body** *(Optional if cookie is present)*:
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
- **Response (200 OK)**:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### 4. Logout & Blacklist Token
- **Method / Path**: `POST /api/v1/auth/logout/`
- **Access**: Authenticated (`IsAuthenticated`)
- **Request Body** *(Optional if cookie is present)*:
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
- **Response (200 OK)**:
```json
{
  "status": "success",
  "message": "Successfully logged out."
}
```

#### 5. Get Current User Profile
- **Method / Path**: `GET /api/v1/auth/me/`
- **Access**: Authenticated (`IsAuthenticated`)
- **Response (200 OK)**:
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "johndoe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "PATIENT",
  "phone_number": "+919876543210",
  "is_verified": false
}
```

#### 6. Update User Profile
- **Method / Path**: `PATCH /api/v1/auth/me/`
- **Access**: Authenticated (`IsAuthenticated`)
- **Request Body**:
```json
{
  "first_name": "Jonathan",
  "last_name": "Doe",
  "phone_number": "+919876543299"
}
```

#### 7. Change Password
- **Method / Path**: `POST /api/v1/auth/change-password/`
- **Access**: Authenticated (`IsAuthenticated`)
- **Request Body**:
```json
{
  "old_password": "OldPassword123!",
  "new_password": "NewSecurePassword456!",
  "new_password_confirm": "NewSecurePassword456!"
}
```
- **Response (200 OK)**:
```json
{
  "status": "success",
  "message": "Password changed successfully."
}
```

#### 8. Retrieve CSRF Token
- **Method / Path**: `GET /api/v1/auth/csrf/`
- **Access**: Public
- **Response (200 OK)**:
```json
{
  "status": "success",
  "csrfToken": "qGj0W8F7G..."
}
```

---

### Module 2: Patients (`/api/v1/patients/`)

#### 1. Get Current Patient Demographics
- **Method / Path**: `GET /api/v1/patients/me/`
- **Access**: Patient (`IsPatient`)
- **Response (200 OK)**:
```json
{
  "id": 1,
  "user": { ... },
  "date_of_birth": "1992-05-14",
  "gender": "MALE",
  "blood_group": "O+",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "+919876543211",
  "emergency_contact_relation": "Spouse",
  "address": "123 Healthcare Ave",
  "city": "Bengaluru",
  "state": "Karnataka",
  "postal_code": "560001"
}
```

#### 2. Update Current Patient Demographics
- **Method / Path**: `PATCH /api/v1/patients/me/`
- **Access**: Patient (`IsPatient`)
- **Request Body**:
```json
{
  "date_of_birth": "1992-05-14",
  "gender": "MALE",
  "blood_group": "O+",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "+919876543211",
  "emergency_contact_relation": "Spouse",
  "address": "123 Healthcare Ave, Flat 4B",
  "city": "Bengaluru",
  "state": "Karnataka",
  "postal_code": "560001",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+919876543210"
}
```

#### 3. Patient Health Timeline
- **Method / Path**: `GET /api/v1/patients/me/timeline/`
- **Access**: Patient (`IsPatient`)
- **Query Parameters**:
  - `start_date` (optional): Filter events on or after `YYYY-MM-DD`
  - `end_date` (optional): Filter events on or before `YYYY-MM-DD`
  - `event_type` (optional): `ALL` (default), `APPOINTMENT`, `MEDICAL_RECORD`, `PRESCRIPTION`
  - `limit` (optional): Max events (default: `50`, max: `200`)
- **Response (200 OK)**:
```json
{
  "status": "success",
  "patient_id": 1,
  "total_events": 12,
  "results": [
    {
      "event_type": "APPOINTMENT",
      "event_id": 14,
      "timestamp": "2026-11-01T10:30:00+05:30",
      "title": "Consultation with Dr. Ramesh Sharma",
      "subtitle": "Cardiology",
      "status": "CONFIRMED",
      "doctor_name": "Ramesh Sharma",
      "details": {
        "date": "2026-11-01",
        "time": "10:30:00",
        "duration_minutes": 30,
        "reason": "Chest tightness and palpitations",
        "status": "CONFIRMED"
      }
    }
  ]
}
```

#### 4. Patient Clinical History (Authorized Doctor/Admin Access)
- **Method / Path**: `GET /api/v1/patients/<int:pk>/clinical-history/`
- **Access**: Doctor with active appointment relationship OR Administrator (`IsDoctorOrAdmin`)
- **Response (200 OK)**:
```json
{
  "status": "success",
  "patient": {
    "id": 1,
    "full_name": "John Doe",
    "gender": "Male",
    "blood_group": "O+",
    "date_of_birth": "1992-05-14",
    "emergency_contact": {
      "name": "Jane Doe",
      "phone": "+919876543211",
      "relation": "Spouse"
    }
  },
  "medical_records": [ ... ],
  "prescriptions": [ ... ],
  "recent_consultations": [ ... ]
}
```

#### 5. List Patients
- **Method / Path**: `GET /api/v1/patients/`
- **Access**: Doctor or Admin (`IsDoctorOrAdmin`)
- **Query Parameters**: `search` (name, email)

---

### Module 3: Doctors (`/api/v1/doctors/`)

#### 1. Search & List Doctors
- **Method / Path**: `GET /api/v1/doctors/`
- **Access**: Public (`AllowAny`)
- **Query Parameters**:
  - `specialization` (e.g., `CARDIOLOGY`, `DERMATOLOGY`, `GENERAL_MEDICINE`)
  - `search` (Doctor name or qualification)
  - `max_fee` (Max consultation fee)
  - `ordering` (`consultation_fee`, `-consultation_fee`, `years_of_experience`, `-years_of_experience`)
- **Response (200 OK - Paginated)**:
```json
{
  "status": "success",
  "count": 5,
  "total_pages": 1,
  "current_page": 1,
  "results": [
    {
      "id": 2,
      "user_id": 5,
      "display_name": "Ramesh Sharma",
      "specialization": "CARDIOLOGY",
      "specialization_display": "Cardiology",
      "qualifications": "MBBS, MD (Cardiology), FACC",
      "years_of_experience": 14,
      "consultation_fee": "800.00",
      "biography": "Senior interventional cardiologist with 14+ years experience...",
      "is_available": true,
      "working_hours_start": "09:00:00",
      "working_hours_end": "17:00:00"
    }
  ]
}
```

#### 2. Provision Doctor Account (Admin Only)
- **Method / Path**: `POST /api/v1/doctors/`
- **Access**: Administrator (`IsAdministrator`)
- **Request Body**:
```json
{
  "username": "dr_ramesh",
  "email": "dr.ramesh@vakcare.com",
  "password": "DocSecurePassword123!",
  "first_name": "Ramesh",
  "last_name": "Sharma",
  "phone_number": "+919812345678",
  "display_name": "Ramesh Sharma",
  "specialization": "CARDIOLOGY",
  "qualifications": "MBBS, MD, DM (Cardiology)",
  "years_of_experience": 14,
  "consultation_fee": 800.00,
  "license_number": "MCI-CAR-987654",
  "is_verified": true,
  "is_available": true
}
```

#### 3. Doctor Self-Profile
- **Method / Path**: `GET /api/v1/doctors/me/` and `PATCH /api/v1/doctors/me/`
- **Access**: Doctor (`IsDoctor`)
- **Updateable Fields**: `display_name`, `biography`, `consultation_fee`, `is_available`, `working_hours_start`, `working_hours_end`

#### 4. Verify / Revoke Doctor Status
- **Method / Path**: `POST /api/v1/doctors/<int:pk>/verify/`
- **Access**: Administrator (`IsAdministrator`)
- **Request Body**:
```json
{
  "is_verified": true,
  "notes": "Medical council license verified with state board."
}
```

---

### Module 4: Appointments (`/api/v1/appointments/`)

#### 1. List Appointments
- **Method / Path**: `GET /api/v1/appointments/`
- **Access**: Authenticated (`IsAuthenticated`)
- **Filters**: `status`, `date`, `doctor_id`
- *Patients view own bookings; Doctors view own consultations; Admins view all.*

#### 2. Book New Appointment (Atomic & Concurrency-Safe)
- **Method / Path**: `POST /api/v1/appointments/`
- **Access**: Patient or Admin
- **Request Body**:
```json
{
  "doctor_id": 2,
  "appointment_date": "2026-11-05",
  "start_time": "10:30:00",
  "duration_minutes": 30,
  "reason": "Persistent chest heaviness during evening walks."
}
```
- **Response (201 Created)**:
```json
{
  "status": "success",
  "message": "Appointment scheduled successfully.",
  "appointment": {
    "id": 10,
    "patient": { ... },
    "doctor": { ... },
    "appointment_date": "2026-11-05",
    "start_time": "10:30:00",
    "end_time": "11:00:00",
    "duration_minutes": 30,
    "reason": "Persistent chest heaviness during evening walks.",
    "status": "PENDING",
    "status_display": "Pending Confirmation"
  }
}
```

#### 3. State Transition Endpoints
- `POST /api/v1/appointments/<id>/confirm/` — Assigned Doctor or Admin confirms a `PENDING` booking.
- `POST /api/v1/appointments/<id>/reject/` — Assigned Doctor or Admin rejects (`{"reason": "Doctor in surgery"}`).
- `POST /api/v1/appointments/<id>/cancel/` — Patient, Doctor, or Admin cancels (`{"cancellation_reason": "Rescheduling needed"}`).
- `POST /api/v1/appointments/<id>/complete/` — Assigned Doctor or Admin marks a confirmed consultation `COMPLETED`.

#### 4. Doctor Daily Schedule
- **Method / Path**: `GET /api/v1/appointments/daily-schedule/`
- **Access**: Doctor or Admin (`IsDoctorOrAdmin`)
- **Query Parameters**: `date` (`YYYY-MM-DD`, defaults to today), `doctor_id` (Admin only)
- **Response (200 OK)**:
```json
{
  "status": "success",
  "date": "2026-11-05",
  "doctor": {
    "id": 2,
    "display_name": "Ramesh Sharma",
    "specialization": "Cardiology"
  },
  "metrics": {
    "total": 6,
    "pending": 1,
    "confirmed": 4,
    "completed": 1,
    "cancelled": 0
  },
  "schedule": [
    {
      "id": 10,
      "start_time": "10:30:00",
      "end_time": "11:00:00",
      "patient_name": "John Doe",
      "status": "CONFIRMED",
      "reason": "Persistent chest heaviness"
    }
  ]
}
```

---

### Module 5: Medical Records (`/api/v1/medical-records/`)

#### 1. List Records
- **Method / Path**: `GET /api/v1/medical-records/`
- **Access**: Authenticated (`IsAuthenticated`)
- **Query Parameters**: `record_type`, `patient_id` (Doctors/Admins only)

#### 2. Create Record
- **Method / Path**: `POST /api/v1/medical-records/`
- **Access**: Verified Doctor or Administrator
- **Request Body**:
```json
{
  "patient_id": 1,
  "record_type": "CONSULTATION_NOTE",
  "title": "Cardiology Consultation Note",
  "description": "Patient presents with mild chest heaviness on exertion. Resting ECG normal.",
  "clinical_data": {
    "blood_pressure": "125/82 mmHg",
    "heart_rate_bpm": 74,
    "oxygen_saturation": "98%",
    "temperature_f": 98.4
  }
}
```

---

### Module 6: Prescriptions (`/api/v1/prescriptions/`)

#### 1. List Prescriptions
- **Method / Path**: `GET /api/v1/prescriptions/`
- **Access**: Authenticated (`IsAuthenticated`)
- **Query Parameters**: `status` (`ACTIVE`, `COMPLETED`, `CANCELLED`)

#### 2. Issue Prescription
- **Method / Path**: `POST /api/v1/prescriptions/`
- **Access**: Verified Doctor (`IsDoctor`)
- **Request Body**:
```json
{
  "patient_id": 1,
  "appointment_id": 10,
  "diagnosis": "Mild exertional angina / Pre-hypertension",
  "notes": "Low sodium diet. Avoid strenuous exertion until TMT results.",
  "items": [
    {
      "medication_name": "Aspirin",
      "dosage": "75mg",
      "frequency": "Once daily after lunch",
      "duration": "30 days",
      "instructions": "Take with water"
    },
    {
      "medication_name": "Atorvastatin",
      "dosage": "10mg",
      "frequency": "Once daily at bedtime",
      "duration": "30 days",
      "instructions": "Avoid grapefruit juice"
    }
  ]
}
```

---

### Module 7: Notifications (`/api/v1/notifications/`)

#### 1. List Notifications
- **Method / Path**: `GET /api/v1/notifications/`
- **Access**: Authenticated (`IsAuthenticated`)
- **Query Parameters**: `unread=true`

#### 2. Mark Notification as Read
- **Method / Path**: `PATCH /api/v1/notifications/<int:pk>/read/` (or `POST`)

#### 3. Mark All Notifications as Read
- **Method / Path**: `POST /api/v1/notifications/mark-all-read/`

#### 4. Trigger Appointment Reminders
- **Method / Path**: `POST /api/v1/notifications/trigger-reminders/`
- **Access**: Administrator (`IsAdministrator`)
- **Request Body**: `{"lead_hours": 48}`

---

### Module 8: AI Assistant (`/api/v1/ai/`)

#### 1. Health Inquiry Guidance (Single Turn)
- **Method / Path**: `POST /api/v1/ai/guidance/`
- **Access**: Authenticated (`IsAuthenticated`)
- **Rate Limit**: Scoped AI Throttle (`30/min` in dev, `20/min` in prod)
- **Request Body**:
```json
{
  "query": "I have had a mild headache and low-grade fever for 2 days. What should I do?",
  "context": {}
}
```
- **Response (200 OK)**:
```json
{
  "status": "success",
  "data": {
    "provider": "MockAIProvider (Deterministic)",
    "guidance": "Mild fever may indicate an immune response...",
    "suggested_specialization": "GENERAL_MEDICINE",
    "disclaimer": "DISCLAIMER: This guidance is generated by an automated AI assistant...",
    "is_emergency_alert": false
  }
}
```

#### 2. Summarize Medical Record
- **Method / Path**: `POST /api/v1/ai/summarize-record/`
- **Access**: Authenticated Record Owner, Authoring Doctor, or Administrator
- **Request Body**:
```json
{
  "record_id": 5
}
```

#### 3. Multi-Turn AI Conversations
- `GET /api/v1/ai/conversations/` — List user's conversations with message counts.
- `POST /api/v1/ai/conversations/` — Start a new conversational session (`{"query": "...", "title": "..."}`).
- `GET /api/v1/ai/conversations/<id>/` — Get complete message history.
- `POST /api/v1/ai/conversations/<id>/messages/` — Send follow-up query with contextual memory.
- `DELETE /api/v1/ai/conversations/<id>/` — Delete conversational session.

---

### Module 9: Compliance Audit & Admin Analytics (`/api/v1/audit/`)

#### 1. List Audit Logs
- **Method / Path**: `GET /api/v1/audit/logs/`
- **Access**: Administrator (`IsAdministrator`)
- **Query Parameters**: `event_type`, `resource_type`

#### 2. Comprehensive Platform Analytics
- **Method / Path**: `GET /api/v1/audit/analytics/`
- **Access**: Administrator (`IsAdministrator`)
- **Query Parameters**: `days` (Default: `30`)
- **Response (200 OK)**:
```json
{
  "status": "success",
  "analytics_window_days": 30,
  "metrics": {
    "users": {
      "total_patients": 42,
      "total_doctors": 12,
      "verified_doctors": 10,
      "pending_verification": 2,
      "available_doctors": 9
    },
    "appointments": {
      "all_time_total": 85,
      "completed": 62,
      "confirmed": 14,
      "pending": 4,
      "cancelled": 3,
      "rejected": 2,
      "completion_rate_pct": 72.94,
      "cancellation_rate_pct": 3.53
    },
    "clinical": {
      "total_medical_records": 110,
      "total_prescriptions": 78
    },
    "ai_engine": {
      "active_provider": "openai",
      "model": "gpt-4o-mini",
      "queries_executed": 145
    }
  }
}
```

---

### Module 10: System Health & Probes (`/api/v1/health/`)

#### 1. Liveness Check
- **Method / Path**: `GET /api/v1/health/`
- **Access**: Public (`AllowAny`)
- **Response (200 OK)**:
```json
{
  "status": "healthy",
  "service": "vakcare-backend"
}
```

#### 2. Readiness Check
- **Method / Path**: `GET /api/v1/health/ready/`
- **Access**: Public (`AllowAny`)
- **Response (200 OK when DB is connected, 503 if DB is offline)**:
```json
{
  "status": "ready",
  "database": "connected",
  "ai_provider": "openai"
}
```
