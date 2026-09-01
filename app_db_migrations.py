import json


def _backfill_remision_snapshot_fields(conn) -> None:
    rows = conn.execute(
        "SELECT id, snapshot_json, cliente, ubicacion FROM remisiones"
    ).fetchall()
    for row in rows:
        try:
            snapshot = json.loads(row["snapshot_json"] or "{}")
        except Exception:
            snapshot = {}
        if not isinstance(snapshot, dict):
            snapshot = {}
        cliente = (row["cliente"] or "").strip() or str(snapshot.get("cliente", "")).strip()
        ubicacion = (row["ubicacion"] or "").strip() or str(snapshot.get("ubicacion", "")).strip()
        conn.execute(
            "UPDATE remisiones SET cliente=?, ubicacion=? WHERE id=?",
            (cliente, ubicacion, int(row["id"])),
        )


def apply_store_schema_migrations(store, conn) -> None:
    store._ensure_column(conn, "datasets", "family_code", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "datasets", "content_hash", "TEXT")
    store._ensure_column(conn, "datasets", "row_count", "INTEGER NOT NULL DEFAULT 0")
    store._ensure_column(conn, "datasets", "version", "INTEGER NOT NULL DEFAULT 1")
    store._ensure_column(conn, "datasets", "deleted_at", "TEXT")
    store._ensure_column(conn, "dataset_revisions", "content_hash", "TEXT")
    store._ensure_column(conn, "dataset_revisions", "row_count", "INTEGER NOT NULL DEFAULT 0")
    store._ensure_column(conn, "dataset_revisions", "note", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "qc_profiles", "values_json", "TEXT NOT NULL DEFAULT '{}'")
    store._ensure_column(conn, "qc_profiles", "version", "INTEGER NOT NULL DEFAULT 1")
    store._ensure_column(conn, "qc_profiles", "updated_at", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "doser_profiles", "params_json", "TEXT NOT NULL DEFAULT '{}'")
    store._ensure_column(conn, "doser_profiles", "version", "INTEGER NOT NULL DEFAULT 1")
    store._ensure_column(conn, "doser_profiles", "updated_at", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "users", "role", "TEXT NOT NULL DEFAULT 'presupuestador'")
    store._ensure_column(conn, "users", "password_hash", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "users", "is_active", "INTEGER NOT NULL DEFAULT 1")
    store._ensure_column(conn, "users", "must_change_password", "INTEGER NOT NULL DEFAULT 0")
    store._ensure_column(conn, "users", "password_updated_at", "TEXT")
    store._ensure_column(conn, "users", "created_at", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "users", "updated_at", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "users", "last_login_at", "TEXT")
    store._ensure_column(conn, "remisiones", "status", "TEXT NOT NULL DEFAULT 'abierta'")
    store._ensure_column(conn, "remisiones", "created_by", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "remisiones", "updated_at", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "remisiones", "version", "INTEGER NOT NULL DEFAULT 1")
    store._ensure_column(conn, "remisiones", "cliente", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "remisiones", "ubicacion", "TEXT NOT NULL DEFAULT ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_remisiones_cliente_created ON remisiones(cliente, created_at DESC)")
    store._ensure_column(conn, "audit_log", "created_at", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "audit_log", "username", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "audit_log", "action", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "audit_log", "entity", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "audit_log", "entity_id", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "audit_log", "dataset_id", "INTEGER")
    store._ensure_column(conn, "audit_log", "details_json", "TEXT NOT NULL DEFAULT '{}'")
    store._ensure_column(conn, "qc_cylinders", "failure_type", "TEXT NOT NULL DEFAULT ''")
    store._ensure_column(conn, "qc_cylinders", "image_data", "BYTEA" if store.is_postgres else "BLOB")
    _backfill_remision_snapshot_fields(conn)
