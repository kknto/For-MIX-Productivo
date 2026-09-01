import argparse
import os
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import RLock

from flask import Flask
from dotenv import load_dotenv
from app_feature_routes import register_feature_routes
from app_db_init import initialize_store_database
from app_db_runtime import columns, ensure_column, wrap_pg_conn, wrap_sqlite_conn
from auth_store import AuthStoreMixin
from dataset_store import DatasetStoreMixin
from http_security import configure_http_security
from core.config import load_instance_settings
from core.dataset_ops import configure_dataset_limits
from core.rbac import (
    allowed_views,
)
from core.time import get_now

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2.pool import ThreadedConnectionPool
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

load_dotenv()


def load_or_create_secret(secret_path: Path) -> str:
    env_secret = os.getenv("APP_SECRET_KEY", "").strip()
    if env_secret:
        return env_secret
    if secret_path.exists():
        text = secret_path.read_text(encoding="utf-8").strip()
        if text:
            return text
    key = secrets.token_hex(32)
    secret_path.write_text(key, encoding="utf-8")
    return key


from fleet_store import FleetStoreMixin
from inventory_store import InventoryStoreMixin
from qc_store import QCLabStoreMixin
from qc_doser_store import QCDoserStoreMixin
from remision_store import RemisionStoreMixin
from user_store import UserStoreMixin


class AppStore(AuthStoreMixin, DatasetStoreMixin, QCDoserStoreMixin, RemisionStoreMixin, FleetStoreMixin, InventoryStoreMixin, QCLabStoreMixin, UserStoreMixin):
    def __init__(
        self,
        base_dir: Path,
        csv_file: str | None = None,
        db_url: str | None = None,
        db_path: Path | None = None,
        snapshot_dir: Path | None = None,
        allow_default_users: bool = True,
        max_upload_bytes: int = 10 * 1024 * 1024,
    ):
        self.base_dir = base_dir.resolve()
        self.db_url = db_url
        self.db_path = (db_path or (self.base_dir / "mix_data.sqlite3")).resolve()
        self.snapshot_dir = (snapshot_dir or (self.base_dir / "backups" / "db_snapshots")).resolve()
        self.lock = RLock()
        self.allow_default_users = bool(allow_default_users)
        self.max_upload_bytes = int(max_upload_bytes or 10 * 1024 * 1024)
        self.is_postgres = bool(db_url and POSTGRES_AVAILABLE)
        if not self.is_postgres:
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.pg_pool = None
        if self.is_postgres:
            # Revert keepalives since setsockopt might fail in Render sandboxed containers
            self.pg_pool = ThreadedConnectionPool(1, 20, self.db_url)
        self._init_db()
        self._bootstrap(csv_file)

    def _conn(self):
        if self.is_postgres:
            return wrap_pg_conn(self.pg_pool.getconn(), pool=self.pg_pool, cursor_factory=RealDictCursor)
        else:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            return wrap_sqlite_conn(conn)

    def _columns(self, conn, table_name: str) -> set[str]:
        return columns(conn, table_name, is_postgres=self.is_postgres)

    def _ensure_column(self, conn, table_name: str, column_name: str, ddl: str):
        ensure_column(conn, table_name, column_name, ddl, is_postgres=self.is_postgres)

    def _init_db(self):
        initialize_store_database(self)

    def get_now(self) -> datetime:
        return get_now()
    # -- Fleet methods provided by FleetStoreMixin (fleet_store.py) --



def create_app(base_dir: Path, csv_file: str | None = None) -> Flask:
    settings = load_instance_settings(base_dir.resolve())
    os.environ["APP_TIMEZONE"] = settings.timezone
    settings.qc_uploads_dir.mkdir(parents=True, exist_ok=True)
    configure_dataset_limits(max_rows=settings.max_rows, max_columns=settings.max_columns)

    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.config["BASE_DIR"] = str(settings.base_dir)
    app.config["QC_UPLOADS_DIR"] = str(settings.qc_uploads_dir)
    app.config["INSTANCE_SETTINGS"] = settings
    app.config["INSTANCE_META"] = settings.template_context()
    app.config["SECRET_KEY"] = load_or_create_secret(settings.secret_file)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = settings.session_cookie_secure
    db_url = os.getenv("DATABASE_URL")
    store = AppStore(
        base_dir=base_dir,
        csv_file=csv_file,
        db_url=db_url,
        db_path=settings.sqlite_db_path,
        snapshot_dir=settings.snapshot_dir,
        allow_default_users=settings.allow_default_users,
        max_upload_bytes=settings.max_upload_bytes,
    )
    app.extensions["formix_store"] = store

    @app.get("/healthz")
    def healthz():
        try:
            with store._conn() as conn:
                conn.execute("SELECT 1")
            return {"ok": True, "database": "postgres" if store.is_postgres else "sqlite"}, 200
        except Exception as exc:
            return {"ok": False, "error": str(exc)}, 503

    def feature_enabled(view: str) -> bool:
        return bool(settings.features.get(view, True))

    def allowed_views_for_role(role: str) -> list[str]:
        return [view for view in allowed_views(role) if feature_enabled(view)]
    security = configure_http_security(app, store)
    ensure_csrf_token = security["ensure_csrf_token"]
    current_auth = security["current_auth"]
    login_required = security["login_required"]
    require_roles = security["require_roles"]

    from auth_routes import register_auth_routes
    register_auth_routes(
        app=app,
        store=store,
        current_auth=current_auth,
        login_required=login_required,
        ensure_csrf_token=ensure_csrf_token,
        allowed_views_for_role=allowed_views_for_role,
        feature_enabled=feature_enabled,
    )

    register_feature_routes(app, store, feature_enabled, login_required, require_roles)






    return app

def main() -> None:
    parser = argparse.ArgumentParser(description="Concrete mix design editor with SQLite persistence.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    parser.add_argument("--csv", default=None, help="CSV used only for first bootstrap")
    args = parser.parse_args()
    local_app = create_app(base_dir=Path.cwd(), csv_file=args.csv)
    local_app.run(host=args.host, port=args.port, debug=False)

if __name__ == "__main__":
    main()
