"""
Diagnostic script for inspecting Cloud Aiven MySQL production database state.
Non-destructive read-only queries only.
"""
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
os.environ.setdefault("DJANGO_SECRET_KEY", "production-readiness-verification-temporary-key-at-least-40-chars")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,vakcare.vercel.app")
os.environ.setdefault("DB_ENVIRONMENT", "aiven")

import django
django.setup()

from django.db import connection

def inspect_db():
    print("=" * 60)
    print("VakCare Cloud Aiven MySQL In-Depth Production Audit")
    print("=" * 60)
    with connection.cursor() as cursor:
        cursor.execute("SELECT VERSION();")
        version = cursor.fetchone()[0]
        print(f"MySQL Version        : {version}")

        cursor.execute("SELECT @@character_set_database, @@collation_database;")
        charset, collation = cursor.fetchone()
        print(f"Charset / Collation  : {charset} / {collation}")

        cursor.execute("SELECT @@ssl_cipher;")
        cipher = cursor.fetchone()
        print(f"SSL Cipher in use    : {cipher[0] if cipher else 'None'}")

        cursor.execute("""
            SELECT TABLE_NAME, ENGINE, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME;
        """)
        tables = cursor.fetchall()
        print(f"\nTotal Tables in defaultdb: {len(tables)}")
        for t in tables:
            print(f"  - {t[0]:<36} Engine: {t[1]:<6} Estimated Rows: {t[2]}")

        cursor.execute("""
            SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY TABLE_NAME, CONSTRAINT_NAME;
        """)
        fks = cursor.fetchall()
        print(f"\nTotal Foreign Key Constraints: {len(fks)}")
        for fk in fks:
            print(f"  - {fk[1]}.{fk[2]} -> {fk[3]}.{fk[4]} ({fk[0]})")

        cursor.execute("""
            SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, NON_UNIQUE, SEQ_IN_INDEX
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE() AND INDEX_NAME != 'PRIMARY'
            ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;
        """)
        indexes = cursor.fetchall()
        print(f"\nTotal Secondary & Composite Indexes: {len(indexes)}")
        for idx in indexes:
            kind = "NON-UNIQUE" if idx[3] == 1 else "UNIQUE"
            print(f"  - [{kind}] {idx[0]}.{idx[2]} (Index: {idx[1]}, pos: {idx[4]})")

        # Connection / max connections
        cursor.execute("SHOW VARIABLES LIKE 'max_connections';")
        max_conn = cursor.fetchone()
        cursor.execute("SHOW STATUS LIKE 'Threads_connected';")
        active_conn = cursor.fetchone()
        print("\nConnection Metrics:")
        print(f"  - {max_conn[0]}: {max_conn[1]}")
        print(f"  - {active_conn[0]}: {active_conn[1]}")

        # Check CONN_MAX_AGE in django settings
        from django.conf import settings
        conn_max_age = settings.DATABASES['default'].get('CONN_MAX_AGE')
        print(f"  - Django DB_CONN_MAX_AGE: {conn_max_age} seconds (0 required for serverless)")

if __name__ == "__main__":
    inspect_db()

