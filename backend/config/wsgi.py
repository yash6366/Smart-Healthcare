"""
WSGI config for VakCare project.
"""
import os
import sys
from pathlib import Path
from django.core.wsgi import get_wsgi_application

base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

# Serverless environment fallback: install PyMySQL as MySQLdb driver if native MySQLdb is unavailable
try:
    import MySQLdb  # noqa: F401
except ImportError:
    try:
        import pymysql
        pymysql.version_info = (2, 2, 0, "final", 0)
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

application = get_wsgi_application()
app = application
