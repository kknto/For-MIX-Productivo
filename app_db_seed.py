import json
import os

from werkzeug.security import check_password_hash, generate_password_hash

from auth_store import normalize_username, validate_password_policy
from core.dataset_ops import content_hash, guess_family_from_filename
from core.rbac import DEFAULT_USER_PASSWORD, DEFAULT_USERS
from core.time import now_str


def seed_store_defaults(store, conn) -> None:
    now = now_str()
    _seed_bootstrap_admin(conn, now)
    if store.allow_default_users:
        for item in DEFAULT_USERS:
            conn.execute(
                """
                INSERT OR IGNORE INTO users(username,role,password_hash,is_active,must_change_password,password_updated_at,created_at,updated_at,last_login_at)
                VALUES(?,?,?,?,?,?,?, ?,NULL)
                """,
                (
                    normalize_username(item["username"]),
                    item["role"],
                    generate_password_hash(item["password"]),
                    1,
                    1,
                    "",
                    now,
                    now,
                ),
            )

        for uname, plain in DEFAULT_USER_PASSWORD.items():
            row = conn.execute(
                "SELECT id,password_hash FROM users WHERE username=? LIMIT 1",
                (uname,),
            ).fetchone()
            if not row:
                continue
            if check_password_hash(row["password_hash"] or "", plain):
                conn.execute(
                    "UPDATE users SET must_change_password=1, updated_at=? WHERE id=?",
                    (now, int(row["id"])),
                )

    _backfill_dataset_metadata(conn)


def _seed_bootstrap_admin(conn, now: str) -> None:
    password = os.getenv("FORMIX_BOOTSTRAP_ADMIN_PASSWORD", "").strip()
    if not password:
        return

    existing = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()
    if int(existing["total"] or 0) > 0:
        return

    policy_error = validate_password_policy(password)
    if policy_error:
        raise ValueError(f"FORMIX_BOOTSTRAP_ADMIN_PASSWORD invalida: {policy_error}")

    username = normalize_username(os.getenv("FORMIX_BOOTSTRAP_ADMIN_USERNAME", "admin"))
    if not username:
        raise ValueError("FORMIX_BOOTSTRAP_ADMIN_USERNAME invalido.")

    conn.execute(
        """
        INSERT INTO users(username,role,password_hash,is_active,must_change_password,password_updated_at,created_at,updated_at,last_login_at)
        VALUES(?,?,?,?,?,?,?,?,NULL)
        """,
        (
            username,
            "administrador",
            generate_password_hash(password),
            1,
            1,
            "",
            now,
            now,
        ),
    )


def _backfill_dataset_metadata(conn) -> None:
    missing_hash_rows = conn.execute(
        "SELECT id, headers_json, rows_json FROM datasets WHERE content_hash IS NULL OR row_count=0"
    ).fetchall()
    for row in missing_hash_rows:
        headers = json.loads(row["headers_json"])
        rows = json.loads(row["rows_json"])
        conn.execute(
            "UPDATE datasets SET content_hash=?, row_count=? WHERE id=?",
            (content_hash(headers, rows), len(rows), int(row["id"])),
        )

    missing_family_rows = conn.execute(
        "SELECT id,name FROM datasets WHERE family_code IS NULL OR TRIM(family_code)=''"
    ).fetchall()
    for row in missing_family_rows:
        fam = guess_family_from_filename(row["name"])
        conn.execute("UPDATE datasets SET family_code=? WHERE id=?", (fam, int(row["id"])))
