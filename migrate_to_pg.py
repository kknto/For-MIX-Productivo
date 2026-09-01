import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
from pathlib import Path
from dotenv import load_dotenv
from app import AppStore
from core.config import load_instance_settings

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
SETTINGS = load_instance_settings(BASE_DIR)
SQLITE_DB = str(SETTINGS.sqlite_db_path)
POSTGRES_URL = os.getenv("DATABASE_URL")


def ensure_postgres_schema() -> None:
    store = AppStore(
        base_dir=BASE_DIR,
        db_url=POSTGRES_URL,
        db_path=SETTINGS.sqlite_db_path,
        snapshot_dir=SETTINGS.snapshot_dir,
        allow_default_users=False,
        max_upload_bytes=SETTINGS.max_upload_bytes,
    )
    if store.pg_pool:
        store.pg_pool.closeall()


def migrate():
    if not POSTGRES_URL:
        raise SystemExit("Error: DATABASE_URL not found in environment.")
    if not Path(SQLITE_DB).exists():
        raise SystemExit(f"Error: SQLite source not found: {SQLITE_DB}")

    ensure_postgres_schema()

    lite_conn = sqlite3.connect(SQLITE_DB)
    lite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg2.connect(POSTGRES_URL)
    pg_conn.autocommit = True

    tables = [
        "app_state", "datasets", "dataset_revisions", "upload_staging",
        "qc_profiles", "doser_profiles", "users", "auth_locks",
        "remisiones", "audit_log", "materials", "inventory_transactions",
        "qc_samples", "qc_cylinders", "vehicles", "fuel_records",
        "maintenance_records"
    ]

    for table in tables:
        print(f"Migrating table: {table}...")
        try:
            cursor = lite_conn.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            if not rows:
                print(f"  Table {table} is empty. Skipping.")
                continue

            columns = rows[0].keys()
            col_names = ",".join(columns)

            with pg_conn.cursor() as pg_cur:
                pg_cur.execute(f"TRUNCATE TABLE {table} CASCADE")
                data = [tuple(row) for row in rows]
                execute_values(pg_cur, f"INSERT INTO {table} ({col_names}) VALUES %s", data)
                if "id" in columns:
                    pg_cur.execute(
                        """
                        SELECT pg_get_serial_sequence(%s, 'id')
                        """,
                        (table,),
                    )
                    seq_row = pg_cur.fetchone()
                    seq_name = seq_row[0] if seq_row else None
                    if seq_name:
                        pg_cur.execute(
                            f"SELECT setval(%s, COALESCE((SELECT MAX(id) FROM {table}), 1), true)",
                            (seq_name,),
                        )
            print(f"  Successfully migrated {len(rows)} records.")
        except Exception as e:
            print(f"  Error migrating {table}: {e}")

    lite_conn.close()
    pg_conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate()
