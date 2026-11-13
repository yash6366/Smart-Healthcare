"""
Base settings for VakCare Healthcare Management Platform.
"""
import os
import sys
from datetime import timedelta
from pathlib import Path
from dotenv import dotenv_values

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Add BASE_DIR to Python path to ensure apps and config are discovered cleanly
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ---------------------------------------------------------------------
# Environment Variable Loading (Strict Precedence)
# 1. Explicit OS / shell / platform environment variables (highest)
# 2. Environment-specific file (.env.local or .env.aiven; root overrides backend/)
# 3. Base .env file defaults (root overrides backend/)
# 4. Safe application defaults (lowest)
# ---------------------------------------------------------------------
_OS_ENV_KEYS = frozenset(os.environ.keys())


def _read_dotenv_layers(*paths: Path) -> dict[str, str]:
    merged: dict[str, str] = {}
    for env_path in paths:
        if env_path.exists():
            for key, value in dotenv_values(env_path).items():
                if value is not None:
                    merged[key] = value
    return merged


def _apply_env_defaults(values: dict[str, str]) -> None:
    for key, value in values.items():
        if key not in _OS_ENV_KEYS:
            os.environ[key] = value


# Layer 3: Load base .env defaults without overriding explicit OS environment variables
_base_env_defaults = _read_dotenv_layers(BASE_DIR / ".env", BASE_DIR.parent / ".env")
_apply_env_defaults(_base_env_defaults)

# Serverless environment detection
is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

# Database Environment Selector:
# - 'local': Local MySQL Server (default for local development)
# - 'aiven': Aiven Cloud MySQL (explicit cloud configuration, or default on serverless)
if "DB_ENVIRONMENT" in _OS_ENV_KEYS:
    raw_db_env = os.environ.get("DB_ENVIRONMENT", "")
elif is_serverless:
    raw_db_env = "aiven"
else:
    raw_db_env = os.environ.get("DB_ENVIRONMENT", "local")

DB_ENVIRONMENT = raw_db_env.strip().lower()
if not DB_ENVIRONMENT:
    raise RuntimeError(
        "[DATABASE CONFIGURATION ERROR] DB_ENVIRONMENT cannot be empty. "
        "Allowed values are 'local' or 'aiven'."
    )
if DB_ENVIRONMENT not in ("local", "aiven", "cloud"):
    raise RuntimeError(
        f"[DATABASE CONFIGURATION ERROR] Invalid DB_ENVIRONMENT '{DB_ENVIRONMENT}'. "
        "Allowed values are 'local' or 'aiven'."
    )

# Normalize alias 'cloud' -> 'aiven' while keeping env file lookup consistent
_env_file_suffix = "local" if DB_ENVIRONMENT == "local" else "aiven"
_env_specific_defaults = _read_dotenv_layers(
    BASE_DIR / f".env.{_env_file_suffix}",
    BASE_DIR.parent / f".env.{_env_file_suffix}",
)
# Layer 2: Environment-specific files override base .env defaults, never explicit OS env vars
_apply_env_defaults({**_base_env_defaults, **_env_specific_defaults})

# Core Security
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "vakcare-insecure-default-key-change-in-production")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")

# Allowed Hosts
ALLOWED_HOSTS_STR = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STR.split(",") if host.strip()]
for _vercel_host_var in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL", "VERCEL_BRANCH_URL"):
    _vercel_host = os.getenv(_vercel_host_var, "").strip()
    if _vercel_host and _vercel_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_vercel_host)
if os.getenv("ALLOW_ALL_VERCEL_HOSTS", "False").lower() in ("true", "1", "yes"):
    if ".vercel.app" not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(".vercel.app")

# Application definition
# Logical Database Organization:
#   DJANGO SYSTEM : django_migrations, django_content_type, auth_permission (+ supporting auth/admin/session tables)
#   SECURITY      : token_blacklist_outstandingtoken, token_blacklist_blacklistedtoken, audit_auditlog
#   CORE          : accounts_user, patients_patientprofile, doctors_doctorprofile
#   HEALTHCARE    : appointments_appointment, medical_records_medicalrecord, prescriptions_prescription, prescriptions_prescriptionitem
#   COMMUNICATION : notifications_notification, ai_assistant_conversation, ai_assistant_message
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
    "rest_framework_simplejwt.token_blacklist",  # SECURITY: JWT refresh & blacklist tables
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS = [
    # SHARED INFRASTRUCTURE (Abstract base models, health checks, middleware)
    "apps.common.apps.CommonConfig",
    # CORE (Identity & Profiles)
    "apps.accounts.apps.AccountsConfig",
    "apps.patients.apps.PatientsConfig",
    "apps.doctors.apps.DoctorsConfig",
    # HEALTHCARE (Clinical Domain)
    "apps.appointments.apps.AppointmentsConfig",
    "apps.medical_records.apps.MedicalRecordsConfig",
    "apps.prescriptions.apps.PrescriptionsConfig",
    # COMMUNICATION (Notifications & AI Assistant)
    "apps.notifications.apps.NotificationsConfig",
    "apps.ai_assistant.apps.AiAssistantConfig",
    # SECURITY (Compliance & Audit Trail)
    "apps.audit.apps.AuditConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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

# Database Configuration (Local MySQL vs. Aiven Cloud MySQL)
default_conn_max_age = "0" if is_serverless else "60"
_LOCALHOST_HOSTS = {"127.0.0.1", "localhost", "::1", "[::1]", "0.0.0.0"}

if DB_ENVIRONMENT == "local":
    # -----------------------------------------------------------------
    # 1. LOCAL MYSQL CONFIGURATION (Default for local development)
    # -----------------------------------------------------------------
    DB_ENGINE = os.getenv("DB_ENGINE", "django.db.backends.mysql")
    DB_NAME = os.getenv("DB_NAME", "vakcare_db")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1").strip()
    DB_PORT = str(os.getenv("DB_PORT", "3306")).strip()

    # Strict Safety Guard: Local mode must never resolve to a cloud/blank database
    if not DB_HOST:
        raise RuntimeError(
            "[DATABASE CONFIGURATION ERROR] DB_ENVIRONMENT is set to 'local', "
            "but DB_HOST is empty."
        )
    if "aivencloud.com" in DB_HOST.lower() or (
        os.getenv("DATABASE_URL", "").lower().find("aivencloud.com") != -1
        and "DB_HOST" not in _OS_ENV_KEYS
        and not _env_specific_defaults.get("DB_HOST")
        and not _base_env_defaults.get("DB_HOST")
    ):
        raise RuntimeError(
            f"[DATABASE SAFETY VIOLATION] DB_ENVIRONMENT is set to 'local', but DB_HOST points to "
            f"cloud host '{DB_HOST}'. Local development is restricted to local MySQL instances (127.0.0.1). "
            "To connect to Aiven Cloud MySQL intentionally, set DB_ENVIRONMENT=aiven."
        )

    try:
        conn_max_age = int(os.getenv("DB_CONN_MAX_AGE", default_conn_max_age))
    except ValueError as exc:
        raise RuntimeError(
            "[DATABASE CONFIGURATION ERROR] DB_CONN_MAX_AGE must be an integer."
        ) from exc

    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
            "CONN_MAX_AGE": conn_max_age,
            "OPTIONS": {},
        }
    }

    # SSL is disabled for local MySQL by default
    if os.getenv("DB_SSL_REQUIRE", "False").lower() in ("true", "1", "yes"):
        DATABASES["default"]["OPTIONS"]["ssl"] = {"ssl_mode": "REQUIRED"}

else:  # 'aiven' or alias 'cloud' (validated above)
    # -----------------------------------------------------------------
    # 2. AIVEN CLOUD MYSQL CONFIGURATION (Explicit cloud selection)
    # -----------------------------------------------------------------
    # Strict URL priority:
    # 1. Explicit OS env DATABASE_URL / AIVEN_DATABASE_URL
    # 2. .env.aiven DATABASE_URL / AIVEN_DATABASE_URL
    # 3. .env AIVEN_DATABASE_URL / DATABASE_URL
    if "DATABASE_URL" in _OS_ENV_KEYS and os.environ.get("DATABASE_URL"):
        DATABASE_URL = os.environ["DATABASE_URL"]
    elif "AIVEN_DATABASE_URL" in _OS_ENV_KEYS and os.environ.get("AIVEN_DATABASE_URL"):
        DATABASE_URL = os.environ["AIVEN_DATABASE_URL"]
    elif _env_specific_defaults.get("DATABASE_URL"):
        DATABASE_URL = _env_specific_defaults["DATABASE_URL"]
    elif _env_specific_defaults.get("AIVEN_DATABASE_URL"):
        DATABASE_URL = _env_specific_defaults["AIVEN_DATABASE_URL"]
    else:
        DATABASE_URL = os.getenv("AIVEN_DATABASE_URL") or os.getenv("DATABASE_URL")

    # Never accidentally inherit local DB_* variables from base .env if .env.aiven wasn't present
    # unless explicitly provided by OS env or .env.aiven or prefixed AIVEN_DB_*
    def _aiven_var(generic_key: str, aiven_key: str, default: str = "") -> str:
        if aiven_key in _OS_ENV_KEYS and os.environ.get(aiven_key) is not None:
            return os.environ[aiven_key]
        if generic_key in _OS_ENV_KEYS and os.environ.get(generic_key) is not None:
            return os.environ[generic_key]
        if _env_specific_defaults.get(aiven_key):
            return _env_specific_defaults[aiven_key]
        if _env_specific_defaults.get(generic_key):
            return _env_specific_defaults[generic_key]
        return os.getenv(aiven_key) or default

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
            DB_ENGINE = _aiven_var("DB_ENGINE", "AIVEN_DB_ENGINE", "django.db.backends.mysql")
            default_port = "3306"

        DB_NAME = parsed_db.path.lstrip("/") or _aiven_var("DB_NAME", "AIVEN_DB_NAME", "defaultdb")
        DB_USER = unquote(parsed_db.username or "") or _aiven_var("DB_USER", "AIVEN_DB_USER", "avnadmin")
        DB_PASSWORD = unquote(parsed_db.password or "") or _aiven_var("DB_PASSWORD", "AIVEN_DB_PASSWORD", "")
        DB_HOST = (parsed_db.hostname or _aiven_var("DB_HOST", "AIVEN_DB_HOST", "")).strip()
        DB_PORT = str(parsed_db.port or _aiven_var("DB_PORT", "AIVEN_DB_PORT", default_port)).strip()
    else:
        DB_ENGINE = _aiven_var("DB_ENGINE", "AIVEN_DB_ENGINE", "django.db.backends.mysql")
        DB_NAME = _aiven_var("DB_NAME", "AIVEN_DB_NAME", "defaultdb")
        DB_USER = _aiven_var("DB_USER", "AIVEN_DB_USER", "avnadmin")
        DB_PASSWORD = _aiven_var("DB_PASSWORD", "AIVEN_DB_PASSWORD", "")
        DB_HOST = _aiven_var("DB_HOST", "AIVEN_DB_HOST", "").strip()
        DB_PORT = str(_aiven_var("DB_PORT", "AIVEN_DB_PORT", "12289")).strip()

    if not DB_HOST:
        raise RuntimeError(
            "[DATABASE CONFIGURATION ERROR] DB_ENVIRONMENT is set to 'aiven', but required cloud database "
            "configuration (DATABASE_URL, AIVEN_DATABASE_URL, AIVEN_DB_HOST, or OS DB_HOST) is missing. "
            "Refusing to connect."
        )

    if DB_HOST.lower() in _LOCALHOST_HOSTS:
        raise RuntimeError(
            f"[DATABASE SAFETY VIOLATION] DB_ENVIRONMENT is set to 'aiven', but DB_HOST resolves to "
            f"local host '{DB_HOST}'. Refusing to connect Aiven mode to a local database."
        )

    try:
        conn_max_age = int(os.getenv("DB_CONN_MAX_AGE", default_conn_max_age))
    except ValueError as exc:
        raise RuntimeError(
            "[DATABASE CONFIGURATION ERROR] DB_CONN_MAX_AGE must be an integer."
        ) from exc

    _ssl_ca = os.getenv("DB_SSL_CA", "").strip()
    _ssl_opts = {"ssl": {"ca": _ssl_ca}} if _ssl_ca else {"ssl": {"ssl_mode": "REQUIRED"}}

    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
            "CONN_MAX_AGE": conn_max_age,
            "OPTIONS": _ssl_opts,
        }
    }

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

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

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

# Auto-add explicit Vercel deployment URLs to trusted origins if running on Vercel
for _vercel_origin_var in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL", "VERCEL_BRANCH_URL"):
    _vercel_host = os.getenv(_vercel_origin_var, "").strip()
    if _vercel_host:
        vercel_origin = _vercel_host if _vercel_host.startswith("https://") else f"https://{_vercel_host}"
        if vercel_origin not in CORS_ALLOWED_ORIGINS:
            CORS_ALLOWED_ORIGINS.append(vercel_origin)
        if vercel_origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(vercel_origin)

# Preview wildcard opt-in (disabled by default to avoid trusting arbitrary *.vercel.app tenants with credentials)
if os.getenv("CORS_ALLOW_VERCEL_PREVIEWS", "False").lower() in ("true", "1", "yes"):
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https:\/\/.*\.vercel\.app$",
    ]
    if "https://*.vercel.app" not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append("https://*.vercel.app")

# Reverse Proxy SSL Header for Vercel/Cloudflare/AWS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

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
_default_ai_model = "gpt-4o-mini" if AI_PROVIDER.lower() in ("openai", "chatgpt") else "gemini-flash-latest"
AI_PROVIDER_MODEL = os.getenv("AI_PROVIDER_MODEL") or _default_ai_model
