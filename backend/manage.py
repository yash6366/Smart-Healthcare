#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def main():
    """Run administrative tasks."""
    # Ensure backend directory is in sys.path
    base_dir = Path(__file__).resolve().parent
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))

    # Serverless/local fallback: install PyMySQL as MySQLdb driver if native MySQLdb is unavailable
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
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
