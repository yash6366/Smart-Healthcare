"""
Production settings for VakCare.
"""
import os
from .base import *  # noqa: F403

DEBUG = False

# Ensure SECRET_KEY is set and not default, and is of sufficient length
if SECRET_KEY == "vakcare-insecure-default-key-change-in-production" or len(SECRET_KEY) < 40:
    raise ValueError("DJANGO_SECRET_KEY must be set to a secure, random value with at least 40 characters in production!")

# Ensure ALLOWED_HOSTS is not empty and has no wildcards
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS or any("*" in host for host in ALLOWED_HOSTS):
    raise ValueError("DJANGO_ALLOWED_HOSTS must be explicitly defined and cannot contain wildcards in production!")

# Ensure CORS_ALLOWED_ORIGINS does not contain wildcards with credentials
if any("*" in origin for origin in CORS_ALLOWED_ORIGINS):
    raise ValueError("CORS_ALLOWED_ORIGINS cannot contain wildcards when CORS_ALLOW_CREDENTIALS is enabled!")

# Production Throttling Rates
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "anon": os.getenv("THROTTLE_ANON", "30/minute"),
    "user": os.getenv("THROTTLE_USER", "120/minute"),
    "auth": os.getenv("THROTTLE_AUTH", "15/minute"),
    "ai": os.getenv("THROTTLE_AI", "20/minute"),
}

# Redis distributed cache warning
if not os.getenv("REDIS_URL"):
    import logging
    logging.getLogger("django.security").warning(
        "PRODUCTION SECURITY NOTICE: REDIS_URL is not configured. Rate limits will fall back to LocMemCache and will not be shared across multi-worker instances."
    )

# Security Headers & Cookies
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() in ("true", "1", "yes")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Allows frontend CSRF token extraction if cookie-based
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Disable Swagger UI in production unless explicitly enabled
if not os.getenv("ENABLE_SWAGGER_IN_PRODUCTION", "False").lower() in ("true", "1", "yes"):
    SPECTACULAR_SETTINGS["SERVE_PERMISSIONS"] = ["rest_framework.permissions.IsAdminUser"]
