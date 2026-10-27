# VakCare — System Architecture & Design Specification

## 1. Architectural Overview

VakCare is an enterprise-grade, full-stack healthcare management platform engineered with a strict separation of concerns, defense-in-depth security principles, and domain-driven design. The platform connects three primary stakeholders: **Patients**, **Verified Healthcare Practitioners (Doctors)**, and **Platform Administrators**.

```mermaid
graph TD
    subgraph Client Layer [Frontend Client - Vanilla ES6 / Modern CSS]
        Landing[Landing & Auth Pages]
        PatientPortal[Patient Dashboard & Portals]
        DoctorPortal[Doctor Clinical Dashboard]
        AdminPortal[Administrator Governance Portal]
        ApiClient[Unified ApiClient & Token Manager]
    end

    subgraph Gateway & Infrastructure Layer
        VercelEdge[Vercel Serverless / Nginx Reverse Proxy]
        SecurityMiddleware[Security Headers & CSP Middleware]
        CorsMiddleware[CORS & CSRF Middleware]
        ThrottleEngine[Rate Limiting Engine: LocMem / Redis]
    end

    subgraph Application Layer [Django 5.2 / DRF 3.15 Engine]
        AuthModule[apps.accounts - RBAC & JWT]
        PatientModule[apps.patients - Profiles & Timeline]
        DoctorModule[apps.doctors - Directory & Working Hours]
        ApptModule[apps.appointments - Concurrency Safe Scheduling]
        EHRModule[apps.medical_records - Encrypted Records]
        RxModule[apps.prescriptions - Medication Issuance]
        NotifModule[apps.notifications - In-App Alerts]
        AiModule[apps.ai_assistant - Pluggable LLM Engine]
        AuditModule[apps.audit - Compliance Ledger & Analytics]
        CommonModule[apps.common - Error Envelope & Probes]
    end

    subgraph Data & Persistence Layer
        DB[(PostgreSQL / MySQL / SQLite)]
        Cache[(Redis Cache / Session Store)]
        AuditStore[(Immutable Audit Logs)]
    end

    subgraph External Services
        OpenAI[OpenAI API GPT-4o-mini]
        Gemini[Google Gemini 2.5 API]
        MockAI[Deterministic Mock Provider]
    end

    PatientPortal --> ApiClient
    DoctorPortal --> ApiClient
    AdminPortal --> ApiClient
    Landing --> ApiClient

    ApiClient -->|HTTPS + JWT / Cookies| VercelEdge
    VercelEdge --> SecurityMiddleware
    SecurityMiddleware --> CorsMiddleware
    CorsMiddleware --> ThrottleEngine
    ThrottleEngine --> AuthModule

    AuthModule --> PatientModule
    AuthModule --> DoctorModule
    AuthModule --> ApptModule
    AuthModule --> EHRModule
    AuthModule --> RxModule
    AuthModule --> NotifModule
    AuthModule --> AiModule
    AuthModule --> AuditModule

    PatientModule --> DB
    DoctorModule --> DB
    ApptModule --> DB
    EHRModule --> DB
    RxModule --> DB
    NotifModule --> DB
    AuditModule --> AuditStore

    ThrottleEngine -.-> Cache
    AiModule --> OpenAI
    AiModule --> Gemini
    AiModule --> MockAI
```

---

## 2. Core Architectural Pillars

### 2.1 Domain-Driven Partitioning (Django Apps)
The backend is structured into 10 decoupled domain applications located under `backend/apps/`:

| Domain Application | Primary Responsibility | Key Entities & Services |
| :--- | :--- | :--- |
| **`apps.accounts`** | Authentication, JWT token lifecycle, custom User model, RBAC | `User`, `UserManager`, `set_refresh_cookie`, `CookieTokenRefreshView` |
| **`apps.patients`** | Demographics, emergency contacts, unified health timeline | `PatientProfile`, `PatientHealthTimelineView`, `PatientClinicalHistoryView` |
| **`apps.doctors`** | Practitioner directory, search, schedule boundaries, credential verification | `DoctorProfile`, `DoctorListView`, `DoctorVerifyView` |
| **`apps.appointments`** | Race-condition-free slot booking, consultation state machine | `Appointment`, `create_appointment`, `confirm_appointment`, `DoctorDailyScheduleView` |
| **`apps.medical_records`**| Audited Electronic Health Records (EHR) & diagnostic notes | `MedicalRecord`, `MedicalRecordListCreateView` |
| **`apps.prescriptions`** | Prescription issuance, structured medication items, dosage schedules | `Prescription`, `PrescriptionItem`, `PrescriptionCreateSerializer` |
| **`apps.notifications`** | In-app alerts, read state, automated appointment reminders | `Notification`, `send_notification`, `generate_appointment_reminders` |
| **`apps.ai_assistant`** | Pluggable LLM integration, medical triage, records summarization | `Conversation`, `Message`, `OpenAIProvider`, `GeminiAIProvider`, `MockAIProvider` |
| **`apps.audit`** | Security audit ledger, sanitized event recording, administrative KPI analytics | `AuditLog`, `log_audit_event`, `sanitize_details`, `AdminAnalyticsView` |
| **`apps.common`** | Timestamped abstract base models, unified error envelopes, liveness/readiness | `TimeStampedModel`, `custom_exception_handler`, `SecurityHeadersMiddleware` |

---

## 3. Concurrency Control & Double-Booking Prevention

In healthcare platforms, slot double-booking introduces severe clinical conflicts. VakCare solves this at the database level using pessimistic row locking within an isolated atomic transaction:

```mermaid
sequenceDiagram
    autonumber
    actor Patient as Patient Client
    participant Service as Appointment Service
    participant DB as Relational Database
    participant Counterparty as Doctor / Counterparty

    Patient->>Service: POST /api/v1/appointments/ (doctor_id, date, start_time, duration)
    Service->>Service: Validate appointment_date & start_time > timezone.now()
    Service->>Service: Calculate end_time = start_time + duration_minutes
    
    rect rgb(240, 248, 255)
        Note over Service,DB: Atomic Transaction with Exclusive Row Locks
        Service->>DB: BEGIN TRANSACTION
        Service->>DB: SELECT FOR UPDATE doctor WHERE id = doctor_id
        Service->>DB: SELECT FOR UPDATE patient WHERE id = patient_id
        
        Service->>Service: Verify doctor.is_verified == True AND doctor.is_available == True
        Service->>Service: Verify start_time >= doctor.working_hours_start AND end_time <= doctor.working_hours_end
        
        Service->>DB: SELECT overlaps FROM Appointment WHERE doctor_id = locked_doc AND date = appt_date AND status IN ('PENDING', 'CONFIRMED') AND start_time < requested_end AND end_time > requested_start
        alt Conflict Found
            Service->>DB: ROLLBACK
            Service-->>Patient: 400 Bad Request ("Doctor already has an active appointment...")
        else No Conflict
            Service->>DB: SELECT overlaps FROM Appointment WHERE patient_id = locked_patient ...
            Service->>DB: INSERT INTO Appointment (status='PENDING')
            Service->>DB: INSERT INTO Notification (recipient=doctor, type='APPOINTMENT_REQUESTED')
            Service->>DB: INSERT INTO AuditLog (type='APPOINTMENT_CREATED')
            Service->>DB: COMMIT TRANSACTION
            Service-->>Counterparty: In-App Notification Received
            Service-->>Patient: 201 Created (Appointment Details)
        end
    end
```

### Key Concurrency Invariants
1. **Pessimistic Locking (`select_for_update`)**: Concurrently executing requests trying to reserve slots with the same doctor or patient block until the prior transaction commits or rolls back.
2. **Boundary Checks**: Working hours are verified strictly against the doctor's stored `working_hours_start` and `working_hours_end`.
3. **Past-Date Rejection**: Timezone-aware validation ensures appointments cannot be scheduled in the past.
4. **Active Status Filter**: Only appointments with `status IN ('PENDING', 'CONFIRMED')` occupy time slots. `CANCELLED` and `REJECTED` appointments release slots immediately.

---

## 4. Role-Based Access Control (RBAC) & State Machine

### 4.1 Role Matrix
VakCare implements strict role isolation across three user personas:

| Capability / Resource | Patient | Doctor | Administrator |
| :--- | :---: | :---: | :---: |
| Self-Registration & Profile Update | Yes | Admin Provisioned | CLI / Seeded |
| Public Doctor Directory Search | Yes | Yes | Yes |
| Request Appointment Slot | Yes | No | Yes (on behalf) |
| Confirm / Reject Appointment | No | Yes (assigned only) | Yes |
| Complete Consultation | No | Yes (assigned only) | Yes |
| Cancel Appointment | Yes (own) | Yes (assigned) | Yes (any) |
| Read Medical Records | Yes (own only) | Yes (consulted patients) | Yes (all) |
| Create Medical Record | No | Yes (verified only) | Yes |
| Issue Prescriptions | No | Yes (verified only) | No |
| Access AI Health Assistant | Yes (isolated) | Yes (isolated) | Yes (isolated) |
| View Security Audit Logs | No | No | Yes |
| Doctor Verification Approval | No | No | Yes |
| Platform Analytics Dashboard | No | No | Yes |

### 4.2 Appointment Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> PENDING: Patient Books Slot

    PENDING --> CONFIRMED: Doctor / Admin Confirms
    PENDING --> REJECTED: Doctor / Admin Rejects
    PENDING --> CANCELLED: Patient / Doctor / Admin Cancels

    CONFIRMED --> COMPLETED: Doctor / Admin Marks Complete
    CONFIRMED --> CANCELLED: Patient / Doctor / Admin Cancels

    REJECTED --> [*]
    CANCELLED --> [*]
    COMPLETED --> [*]
```

---

## 5. Security & Defense-in-Depth Architecture

```mermaid
flowchart TD
    Req[Incoming HTTP Request] --> SecHeaders[SecurityHeadersMiddleware]
    SecHeaders --> CSP[CSP: default-src 'self', frame-ancestors 'none']
    SecHeaders --> HSTS[HSTS: max-age=31536000, includeSubDomains]
    SecHeaders --> Opts[X-Content-Type-Options: nosniff, X-Frame-Options: DENY]
    
    Opts --> CORS[CorsMiddleware: Whitelisted Origins Only]
    CORS --> CSRF[CsrfViewMiddleware: SameSite Lax / Strict]
    
    CSRF --> Throttle[DRF ScopedRateThrottle]
    Throttle --> AuthCheck[SimpleJWT Authentication]
    
    AuthCheck --> Perm[Custom Permission Classes]
    Perm --> Sanitizer[Audit Log Sanitizer: Redacts Passwords/Tokens]
    Sanitizer --> View[Target View Execution]
    View --> ErrorEnv[Custom Exception Handler: Unified Error Envelope]
    ErrorEnv --> Resp[HTTP Response]
```

1. **Token Security**:
   - Access tokens have a short lifetime (30 minutes).
   - Refresh tokens (7 days) are rotated upon each use (`ROTATE_REFRESH_TOKENS = True`) and blacklisted in the database (`BLACKLIST_AFTER_ROTATION = True`).
   - Refresh tokens can be delivered via JSON body or stored in an `HttpOnly`, `Secure`, `SameSite=Lax` cookie (`vakcare_refresh_token`).
2. **Immutable Audit Trail**:
   - Sensitive user operations (logins, logouts, appointments, prescriptions, clinical notes, AI inquiries, administrative verifications) are recorded in the `AuditLog` table.
   - All payloads pass through `sanitize_details()` to ensure credentials, secrets, and authorization tokens are redacted (`[REDACTED]`).
3. **Protected Health Information (PHI) Privacy**:
   - A doctor cannot access patient clinical records unless an active or historical appointment relationship exists between them.
   - Unauthorized attempts immediately trigger a `PERMISSION_DENIED` security audit event.

---

## 6. Unified JSON Error Envelope

Every API error returns a standardized envelope format ensuring client-side resilience:

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR | AUTHENTICATION_FAILED | PERMISSION_DENIED | RESOURCE_NOT_FOUND | CONFLICT | RATE_LIMIT_EXCEEDED | INTERNAL_SERVER_ERROR",
    "message": "Human-readable diagnostic summary",
    "details": {
      "field_name": ["Specific validation error message"]
    }
  }
}
```
