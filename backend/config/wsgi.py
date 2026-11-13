"""
WSGI config for VakCare project.
"""
import os
import sys
from pathlib import Path
from django.core.wsgi import get_wsgi_application

base_dir = Path(__file__).resolve().parent.parent
root_dir = base_dir.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Ensure config/__init__.py registers PyMySQL fallback if native MySQLdb is absent
import config  # noqa: E402, F401

_default_settings = (
    "config.settings.production"
    if (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
    else "config.settings.development"
)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", _default_settings)

application = get_wsgi_application()
app = application
