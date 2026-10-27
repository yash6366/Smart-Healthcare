"""
Base settings for VakCare Healthcare Management Platform.
"""
import os
import sys
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Add BASE_DIR to Python path to ensure apps and config are discovered cleanly
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# Core Security
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "vakcare-insecure-default-key-change-in-production")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")

# Allowed Hosts
ALLOWED_HOSTS_STR = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],.vercel.app")
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STR.split(",") if host.strip()]
vercel_url = os.getenv("VERCEL_URL")
if vercel_url and vercel_url not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(vercel_url)
if ".vercel.app" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(".vercel.app")

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.common.apps.CommonConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.patients.apps.PatientsConfig",
    "apps.doctors.apps.DoctorsConfig",
    "apps.appointments.apps.AppointmentsConfig",
    "apps.medical_records.apps.MedicalRecordsConfig",
    "apps.prescriptions.apps.PrescriptionsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.ai_assistant.apps.AiAssistantConfig",
    "apps.audit.apps.AuditConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "apps.common.middleware.security_headers.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Database Configuration (MySQL / PostgreSQL / Cloud Database)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    from urllib.parse import urlparse, unquote
    parsed_db = urlparse(DATABASE_URL)
    scheme = parsed_db.scheme.lower()
    if scheme in ("mysql", "mysql2"):
        DB_ENGINE = "django.db.backends.mysql"
        default_port = "3306"
    elif scheme in ("postgres", "postgresql", "psql"):
        DB_ENGINE = "django.db.backends.postgresql"
        default_port = "5432"
    elif scheme == "sqlite":
        DB_ENGINE = "django.db.backends.sqlite3"
        default_port = ""
    else:
        DB_ENGINE = os.getenv("DB_ENGINE", "django.db.backends.mysql")
        default_port = "3306"

    DB_NAME = parsed_db.path.lstrip("/") or os.getenv("DB_NAME", "vakcare_db")
    DB_USER = unquote(parsed_db.username or "") or os.getenv("DB_USER", "root")
    DB_PASSWORD = unquote(parsed_db.password or "") or os.getenv("DB_PASSWORD", "")
    DB_HOST = parsed_db.hostname or os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = str(parsed_db.port or default_port)
else:
    DB_ENGINE = os.getenv("DB_ENGINE", "django.db.backends.mysql")
    DB_NAME = os.getenv("DB_NAME", "vakcare_db")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")

DATABASES = {
    "default": {
        "ENGINE": DB_ENGINE,
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        "OPTIONS": {},
    }
}

# Cloud MySQL SSL Option (Aiven, PlanetScale, Railway, AWS RDS)
is_ssl_required = (
    os.getenv("DB_SSL_REQUIRE", "False").lower() in ("true", "1", "yes")
    or bool(DATABASE_URL and ("ssl-mode" in DATABASE_URL.lower() or "aivencloud" in DATABASE_URL.lower()))
)
if is_ssl_required:
    DATABASES["default"]["OPTIONS"]["ssl"] = {"ssl_mode": "REQUIRED"}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization and Timezone
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework Settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON", "60/minute"),
        "user": os.getenv("THROTTLE_USER", "300/minute"),
        "auth": os.getenv("THROTTLE_AUTH", "300/minute" if DEBUG else "15/minute"),
        "ai": os.getenv("THROTTLE_AI", "60/minute" if DEBUG else "30/minute"),
    },
}

# Simple JWT Settings
ACCESS_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "30"))
REFRESH_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "7"))

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=ACCESS_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=REFRESH_DAYS),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Caching & Distributed Throttling Backend
REDIS_URL = os.getenv("REDIS_URL", "")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "vakcare",
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "vakcare-default-locmem",
        }
    }

# CORS Configuration
CORS_ALLOWED_ORIGINS_STR = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080",
)
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in CORS_ALLOWED_ORIGINS_STR.split(",") if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

# CSRF Configuration
CSRF_TRUSTED_ORIGINS_STR = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080",
)
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in CSRF_TRUSTED_ORIGINS_STR.split(",") if origin.strip()
]

# Auto-add Vercel deployment URL to trusted origins if running on Vercel
if vercel_url:
    vercel_origin = f"https://{vercel_url}"
    if vercel_origin not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(vercel_origin)
    if vercel_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(vercel_origin)

# Baseline Security Defaults
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# drf-spectacular OpenAPI Settings
SPECTACULAR_SETTINGS = {
    "TITLE": "VakCare — AI-Powered Healthcare Management Platform API",
    "DESCRIPTION": (
        "Enterprise RESTful API for VakCare healthcare management platform supporting "
        "patients, doctors, appointments, medical records, prescriptions, notifications, "
        "AI assistant guidance, and security audit logging."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1/",
    "TAGS": [
        {"name": "Auth", "description": "Authentication and Token Management"},
        {"name": "Patients", "description": "Patient Profiles and Management"},
        {"name": "Doctors", "description": "Doctor Directory and Profiles"},
        {"name": "Appointments", "description": "Appointment Scheduling and State Transitions"},
        {"name": "Medical Records", "description": "Patient Medical Records and History"},
        {"name": "Prescriptions", "description": "Doctor Prescriptions and Items"},
        {"name": "Notifications", "description": "In-app Notifications and Alerts"},
        {"name": "AI Assistant", "description": "AI-powered Healthcare Guidance Service"},
        {"name": "Audit", "description": "Security and Compliance Audit Logs"},
        {"name": "Health", "description": "System Health and Readiness Verification"},
    ],
}

# Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} [{name}:{lineno}] {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# AI Provider Configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "mock")
AI_PROVIDER_API_KEY = os.getenv("AI_PROVIDER_API_KEY", "")
AI_PROVIDER_MODEL = os.getenv("AI_PROVIDER_MODEL", "gemini-2.5-flash")
