"""
Django management command to perform safe, sanitized database diagnostics.
Verifies active database environment, connectivity, and schema health without leaking secrets.
"""
import re
import sys
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Sanitized database environment and connectivity diagnostic check."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit with non-zero exit code if connection fails or safety rules are violated.",
        )

    def handle(self, *args, **options):
        db_conf = settings.DATABASES.get("default", {})
        engine = db_conf.get("ENGINE", "unknown")
        name = db_conf.get("NAME", "unknown")
        user = db_conf.get("USER", "unknown")
        host = db_conf.get("HOST", "127.0.0.1")
        port = str(db_conf.get("PORT", "3306"))
        ssl_options = db_conf.get("OPTIONS", {}).get("ssl")
        ssl_enabled = bool(ssl_options)
        db_env = getattr(settings, "DB_ENVIRONMENT", "local")

        is_cloud_host = "aivencloud.com" in str(host).lower()

        self.stdout.write("=" * 60)
        self.stdout.write("VakCare Database Diagnostic Check")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Active Environment    : {db_env.upper()} ({'Local MySQL' if db_env == 'local' else 'Aiven Cloud MySQL'})")
        self.stdout.write(f"Database Engine       : {engine}")
        self.stdout.write(f"Database Host         : {host}")
        self.stdout.write(f"Database Port         : {port}")
        self.stdout.write(f"Database Name         : {name}")
        self.stdout.write(f"Database User         : {user}")
        self.stdout.write(f"SSL Status            : {'Required' if ssl_enabled else 'Disabled'}")

        # Safety Check: Local mode must never resolve to a cloud database
        if db_env == "local" and is_cloud_host:
            self.stderr.write(self.style.ERROR("\n[SAFETY VIOLATION] DB_ENVIRONMENT is set to 'local', but Database Host"))
            self.stderr.write(self.style.ERROR(f"resolves to a cloud host: '{host}'."))
            self.stderr.write(self.style.ERROR("Local development must never connect to cloud database resources."))
            self.stderr.write(self.style.ERROR("To intentionally use Aiven, set DB_ENVIRONMENT=aiven."))
            self.stdout.write("=" * 60)
            sys.exit(1)

        # Connection Check (Non-destructive SELECT 1)
        self.stdout.write("-" * 60)
        self.stdout.write("Testing database connectivity (non-destructive)...")

        connection_ok = False
        table_count = None
        error_detail = None

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                row = cursor.fetchone()
                if row and row[0] == 1:
                    connection_ok = True

                # Inspect existing tables safely
                try:
                    cursor.execute("SHOW TABLES;")
                    tables = cursor.fetchall()
                    table_count = len(tables)
                except Exception:
                    table_count = None

        except Exception as exc:
            connection_ok = False
            # Sanitize error detail to prevent any password or credential URL leakage
            sanitized_err = re.sub(r"://([^:@/\s]+):([^@/\s]+)@", r"://\1:[REDACTED]@", str(exc))
            password = db_conf.get("PASSWORD")
            if password:
                sanitized_err = sanitized_err.replace(str(password), "[REDACTED]")
            error_detail = sanitized_err

        if connection_ok:
            self.stdout.write(self.style.SUCCESS("Connection Status     : SUCCESS (Connected)"))
            if table_count is not None:
                self.stdout.write(self.style.SUCCESS(f"Existing Tables Found : {table_count} tables detected"))
            self.stdout.write(self.style.SUCCESS("Safety Verification   : PASS (Target verified for active environment)"))
            self.stdout.write("=" * 60)
        else:
            self.stderr.write(self.style.ERROR("Connection Status     : FAILED (Cannot reach database)"))
            if error_detail:
                self.stderr.write(self.style.WARNING(f"Diagnostic Error      : {error_detail}"))
            self.stderr.write(self.style.NOTICE("\nTroubleshooting Guidance:"))
            if db_env == "local":
                self.stderr.write("  1. Verify the Windows MySQL80 service is running: Get-Service MySQL80")
                self.stderr.write("  2. If using 'vakcare_dev', verify the account was created using backend/scripts/setup_local_mysql.sql")
                self.stderr.write("  3. Verify that DB_PASSWORD in your .env or .env.local matches your local MySQL account password")
                self.stderr.write("  4. If using 'root', set DB_USER=root and DB_PASSWORD=<your-root-password> in .env or .env.local")
            else:
                self.stderr.write("  1. Verify network/internet connectivity to Aiven Cloud MySQL")
                self.stderr.write("  2. Verify that Aiven Cloud MySQL is active and accepting connections on port 12289")
                self.stderr.write("  3. Ensure DB_ENVIRONMENT is set back to 'local' for local development")
            self.stdout.write("=" * 60)
            if options.get("strict"):
                sys.exit(1)

