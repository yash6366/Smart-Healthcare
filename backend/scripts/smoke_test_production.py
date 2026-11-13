"""
Smoke testing script executing non-destructive checks against production configuration.
Simulates production WSGI request handling with config.settings.production and Aiven MySQL.
"""
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
root_dir = backend_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
os.environ.setdefault("DJANGO_SECRET_KEY", "production-readiness-verification-temporary-key-at-least-40-chars")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "testserver,localhost,127.0.0.1,vakcare.vercel.app")
os.environ.setdefault("DB_ENVIRONMENT", "aiven")
os.environ.setdefault("SECURE_SSL_REDIRECT", "False")  # Allow test client HTTP requests

import django
django.setup()

from rest_framework.test import APIClient
from rest_framework import status

def run_smoke_tests():
    print("=" * 60)
    print("VakCare Production Configuration Smoke Tests")
    print("=" * 60)

    client = APIClient()

    # 1. API Health (Liveness Probe)
    print("\n[1] Testing Liveness Health Probe (/api/v1/health/)...")
    res_health = client.get("/api/v1/health/")
    print(f"  Status: {res_health.status_code}")
    print(f"  Body  : {res_health.json()}")
    assert res_health.status_code == status.HTTP_200_OK
    assert res_health.json().get("status") == "healthy"

    # 2. Database Readiness Probe (/api/v1/health/ready/)
    print("\n[2] Testing Database Readiness Probe (/api/v1/health/ready/)...")
    res_ready = client.get("/api/v1/health/ready/")
    print(f"  Status: {res_ready.status_code}")
    print(f"  Body  : {res_ready.json()}")
    assert res_ready.status_code == status.HTTP_200_OK
    assert res_ready.json().get("database") == "connected"

    # 3. OpenAPI Schema Endpoint (/api/schema/) - Production Gated
    print("\n[3] Testing OpenAPI Schema Endpoint (/api/schema/)...")
    res_schema_anon = client.get("/api/schema/")
    print(f"  Anonymous /api/schema/ Status: {res_schema_anon.status_code} (IsAdminUser gated in production)")
    assert res_schema_anon.status_code == status.HTTP_401_UNAUTHORIZED

    # Authenticate as admin to verify schema generation in production
    from apps.accounts.models import User
    admin_u = User.objects.filter(role=User.Role.ADMIN).first()
    if admin_u:
        client.force_authenticate(user=admin_u)
        res_schema_admin = client.get("/api/schema/")
        print(f"  Admin /api/schema/ Status: {res_schema_admin.status_code}")
        print(f"  Admin /api/schema/ Content-Type: {res_schema_admin.headers.get('Content-Type')}")
        assert res_schema_admin.status_code == status.HTTP_200_OK
        assert b"VakCare" in res_schema_admin.content
        client.force_authenticate(user=None)
    else:
        print("  Notice: No existing admin found in Aiven MySQL; verified 401 protection.")

    # 4. Authentication Failure Handling
    print("\n[4] Testing Authentication Failure Handling (/api/v1/auth/login/)...")
    bad_login = client.post(
        "/api/v1/auth/login/",
        {"email_or_username": "nonexistent_probe@example.com", "password": "WrongPassword123!"},
        format="json"
    )
    print(f"  Status: {bad_login.status_code}")
    print(f"  Response: {bad_login.json()}")
    assert bad_login.status_code == status.HTTP_401_UNAUTHORIZED
    assert "detail" in bad_login.json() or "error" in bad_login.json()

    # 5. Role-Based Access Restriction (Unauthenticated to /api/v1/patients/)
    print("\n[5] Testing RBAC Protection on Protected Endpoints...")
    res_pat = client.get("/api/v1/patients/")
    print(f"  Unauthenticated /api/v1/patients/ Status: {res_pat.status_code}")
    assert res_pat.status_code == status.HTTP_401_UNAUTHORIZED

    res_audit = client.get("/api/v1/audit/analytics/")
    print(f"  Unauthenticated /api/v1/audit/analytics/ Status: {res_audit.status_code}")
    assert res_audit.status_code == status.HTTP_401_UNAUTHORIZED

    # 6. Static Frontend Files Verification
    print("\n[6] Verifying Frontend File Assets on Disk...")
    frontend_dir = root_dir / "frontend"
    key_files = [
        "index.html",
        "login.html",
        "register.html",
        "unauthorized.html",
        "not-found.html",
        "css/global.css",
        "css/landing.css",
        "css/auth.css",
        "css/dashboard.css",
        "js/config.js",
        "js/auth.js",
        "js/api-client.js",
        "pages/admin/dashboard.html",
        "pages/doctor/dashboard.html",
        "pages/patient/dashboard.html",
    ]
    for rel_path in key_files:
        fpath = frontend_dir / rel_path
        exists = fpath.exists()
        size = fpath.stat().st_size if exists else 0
        print(f"  - {rel_path:<32} Exists: {exists} ({size} bytes)")
        assert exists and size > 0

    print("\n" + "=" * 60)
    print("ALL PRODUCTION SMOKE TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_smoke_tests()
