"""
Development settings for VakCare.
"""
import sys
from .base import *  # noqa: F403

DEBUG = True

# In development or during test execution, if USE_SQLITE_FOR_TESTS is True
# or if 'pytest' is running and PostgreSQL credentials are unconfigured, use SQLite.
use_sqlite = os.getenv("USE_SQLITE_FOR_TESTS", "False").lower() in ("true", "1", "yes")
is_testing = "pytest" in sys.modules or any("pytest" in arg or "test" in arg for arg in sys.argv)

if (use_sqlite and is_testing) or (is_testing and not DATABASES["default"].get("PASSWORD")):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test_db.sqlite3",
        }
    }
