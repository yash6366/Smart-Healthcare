# VakCare — Security Architecture & Compliance Guidelines

## 1. Healthcare Security Overview

Managing Protected Health Information (PHI) and clinical consultation records requires rigorous safeguards against unauthorized access, data tampering, and identity enumeration. VakCare is engineered around zero-trust and defense-in-depth security principles.

```mermaid
graph TD
    subgraph Perimeter Defense
        CSP[Content-Security-Policy & Security Headers]
        RateLimit[Scoped Rate Limiting & Throttling]
        CORS[Strict CORS Whitelisting]
    end

    subgraph Authentication & Session
        JWT[Short-lived JWT Access Tokens - 30 min]
        Cookie[HttpOnly SameSite=Lax Refresh Tokens]
        Blacklist[Token Blacklist on Rotation & Logout]
    end

    subgraph Authorization & Privacy [HIPAA-Aligned Safeguards]
        RBAC[Explicit Role Access Controls]
        Ownership[Object-Level Ownership Verification]
        ClinicalRelation[Mandatory Doctor-Patient Consultation Link]
    end

    subgraph Audit & Accountability
        Sanitizer[Automated Credential Redaction]
        AuditLedger[Immutable Compliance Audit Trail]
    end

    Perimeter Defense --> Authentication & Session
    Authentication & Session --> Authorization & Privacy
    Authorization & Privacy --> Audit & Accountability
```

---

## 2. Authentication & Token Security

### 2.1 Cryptographic Storage & Password Hashing
- Passwords are validated using Django's standard validators:
  - Minimum length ($\ge 8$ characters)
  - Numeric character requirements
  - Attribute similarity checks
  - Common password dictionary blacklisting
- Password hashes are computed using PBKDF2 with SHA-256 (or Argon2 if configured). Plaintext passwords are never stored or logged.

### 2.2 Short-Lived Access Tokens & Refresh Rotation
- **Access Tokens**: Valid for 30 minutes. Signed with HMAC-SHA256 (`HS256`).
- **Refresh Tokens**: Valid for 7 days.
- **Refresh Token Rotation (`ROTATE_REFRESH_TOKENS = True`)**: Every token refresh issues a new refresh token and immediately invalidates the previous one.
- **Blacklisting (`BLACKLIST_AFTER_ROTATION = True`)**: Consumed or logged-out refresh tokens are written to the database blacklist table (`token_blacklist_blacklistedtoken`), rendering replay attacks impossible.
- **HttpOnly Secure Cookie Delivery**: Clients can receive and transmit refresh tokens via an `HttpOnly`, `Secure`, `SameSite=Lax` cookie (`vakcare_refresh_token`), insulating the session from Cross-Site Scripting (XSS) token extraction.

---

## 3. Privacy & Clinical Relationship Verification

### 3.1 Patient Isolation
Patients have strict, exclusive ownership over their records:
- Can only query their own appointments, medical timeline, prescriptions, and AI chat sessions.
- Object-level lookups filter by `patient.user == request.user`.

### 3.2 Doctor Consultation Relationship Constraint
To satisfy medical privacy requirements:
- A doctor **cannot** view a patient's historical medical records or prescriptions simply by knowing their patient ID.
- Access to `/api/v1/patients/<id>/clinical-history/` requires a verified historical or active consultation link between the doctor and the patient:
```python
has_relationship = Appointment.objects.filter(
    doctor=doctor_profile,
    patient=patient,
).exists()
if not has_relationship:
    raise PermissionDenied(
        "You are not authorized to view this patient's clinical history as no consultations exist between you and this patient."
    )
```
- Unauthorized inspection attempts immediately trigger an audited `PERMISSION_DENIED` event.

---

## 4. Immutable Compliance Audit Trail

### 4.1 Logged Events
The platform records sensitive security and operational events into `AuditLog`:

| Event Type | Triggering Action | Captured Details |
| :--- | :--- | :--- |
| `AUTH_LOGIN` | User login attempt | Identifier, success/failure, IP address, User Agent |
| `AUTH_LOGOUT` | User session termination | User ID, token invalidation confirmation |
| `AUTH_REGISTER` | Patient account creation | Email, role |
| `AUTH_PASSWORD_CHANGE`| Password update | User ID (passwords strictly omitted) |
| `DOCTOR_VERIFIED` | Admin credential approval/revocation | Admin actor, target doctor ID, verification state |
| `DOCTOR_AVAILABILITY`| Doctor schedule/status changes | Availability flag, working hours |
| `APPOINTMENT_CREATED`| New slot booking | Patient ID, doctor ID, date, slot time |
| `APPOINTMENT_STATUS_CHANGE` | Confirm, complete, reject | Previous status, new status, acting doctor/admin |
| `APPOINTMENT_CANCELLED` | Appointment cancellation | Cancellation reason, cancelling user |
| `PRESCRIPTION_ISSUED` | Medication issuance | Prescribing doctor, patient ID, medication count |
| `MEDICAL_RECORD_CREATED` | New clinical observation | Doctor, patient ID, record type |
| `AI_QUERY` | Health inquiry / Record summary | Query length, provider engine, conversation ID |
| `ADMIN_ACTION` | Doctor provisioning, system edits | Target entity, administrative parameters |
| `PERMISSION_DENIED` | Unauthorized access attempt | Requested resource, client IP, failure reason |

### 4.2 Automated Payload Sanitization
Before saving audit payloads, `sanitize_details()` recursively strips sensitive keys:
```python
SENSITIVE_KEYS = {
    "password", "password_confirm", "new_password", "old_password",
    "token", "access", "refresh", "secret", "api_key", "authorization"
}
```
Any matched keys are replaced with `"[REDACTED]"`, guaranteeing that credentials, tokens, and secrets are never committed to disk or database logs.

---

## 5. Defense-in-Depth HTTP Security Headers

VakCare enforces defensive headers via `SecurityHeadersMiddleware`:

| Header | Production Value | Purpose |
| :--- | :--- | :--- |
| **`Content-Security-Policy`** | `default-src 'self'; frame-ancestors 'none'; ...` | Prevents unauthorized script injection and framing |
| **`X-Frame-Options`** | `DENY` | Prevents Clickjacking attacks across all pages |
| **`X-Content-Type-Options`**| `nosniff` | Eliminates MIME-type sniffing vulnerabilities |
| **`Strict-Transport-Security`** | `max-age=31536000; includeSubDomains; preload` | Forces HTTPS communication for 1 full year |
| **`Referrer-Policy`** | `strict-origin-when-cross-origin` | Prevents URL path leakage to third parties |
| **`Permissions-Policy`** | `camera=(), microphone=(), geolocation=(), payment=()` | Disables unnecessary browser hardware APIs |

---

## 6. Rate Limiting & Throttling Tiers

API endpoints are protected against brute-force and DDoS via DRF throttles:

| Throttle Scope | Target Endpoints | Production Limit | Development Limit |
| :--- | :--- | :---: | :---: |
| **`anon`** | Unauthenticated public endpoints | `30 / minute` | `60 / minute` |
| **`user`** | Authenticated generic endpoints | `120 / minute` | `300 / minute` |
| **`auth`** | Login, Registration, Token Refresh | `15 / minute` | `300 / minute` |
| **`ai`** | AI Health Guidance & Chat | `20 / minute` | `60 / minute` |
