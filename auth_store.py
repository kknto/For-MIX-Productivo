from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from core.rbac import ROLE_ALLOWED_VIEWS
from core.time import get_now, now_str


AUTH_MAX_FAILED = 5
AUTH_LOCK_MINUTES = 15


def normalize_username(text: str) -> str:
    return (text or "").strip().lower()


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def validate_password_policy(password: str) -> str | None:
    text = (password or "").strip()
    if len(text) < 10:
        return "La contrasena debe tener al menos 10 caracteres."
    if not any(ch.isupper() for ch in text):
        return "La contrasena debe incluir al menos una letra mayuscula."
    if not any(ch.islower() for ch in text):
        return "La contrasena debe incluir al menos una letra minuscula."
    if not any(ch.isdigit() for ch in text):
        return "La contrasena debe incluir al menos un numero."
    if text.isalnum():
        return "La contrasena debe incluir al menos un simbolo."
    return None


class AuthStoreMixin:
    def _user_row(self, conn, username: str):
        return conn.execute(
            "SELECT id,username,role,password_hash,is_active,must_change_password,password_updated_at,last_login_at FROM users WHERE username=? LIMIT 1",
            (normalize_username(username),),
        ).fetchone()

    def auth_get_user(self, username: str) -> dict | None:
        with self._conn() as conn:
            row = self._user_row(conn, username)
            if not row or int(row["is_active"] or 0) != 1:
                return None
            role = (row["role"] or "").strip()
            if role not in ROLE_ALLOWED_VIEWS:
                return None
            return {
                "id": int(row["id"]),
                "username": row["username"],
                "role": role,
                "must_change_password": bool(int(row["must_change_password"] or 0)),
                "password_updated_at": row["password_updated_at"] or "",
                "last_login_at": row["last_login_at"] or "",
            }

    def _clear_auth_lock(self, conn, username: str):
        conn.execute("DELETE FROM auth_locks WHERE username=?", (normalize_username(username),))

    def _register_auth_fail(self, conn, username: str):
        uname = normalize_username(username)
        now = now_str()
        row = conn.execute("SELECT failed_count FROM auth_locks WHERE username=?", (uname,)).fetchone()
        failed = int(row["failed_count"]) + 1 if row else 1
        lock_until = None
        if failed >= AUTH_MAX_FAILED:
            lock_until = (get_now() + timedelta(minutes=AUTH_LOCK_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
            failed = 0
        conn.execute(
            """
            INSERT INTO auth_locks(username,failed_count,locked_until,last_failed_at)
            VALUES(?,?,?,?)
            ON CONFLICT(username) DO UPDATE SET
              failed_count=excluded.failed_count,
              locked_until=excluded.locked_until,
              last_failed_at=excluded.last_failed_at
            """,
            (uname, failed, lock_until, now),
        )
        return lock_until

    def auth_authenticate(self, username: str, password: str) -> dict:
        uname = normalize_username(username)
        if not uname or not password:
            raise ValueError("Usuario y contrasena son requeridos.")
        with self.lock:
            with self._conn() as conn:
                lock_row = conn.execute(
                    "SELECT failed_count,locked_until FROM auth_locks WHERE username=?",
                    (uname,),
                ).fetchone()
                if lock_row:
                    locked_until = parse_dt(lock_row["locked_until"])
                    if locked_until and locked_until > get_now():
                        mins = max(1, int((locked_until - get_now()).total_seconds() // 60))
                        raise PermissionError(f"Cuenta bloqueada temporalmente. Intente en {mins} minutos.")
                    if locked_until and locked_until <= get_now():
                        self._clear_auth_lock(conn, uname)

                row = self._user_row(conn, uname)
                ok = bool(
                    row
                    and int(row["is_active"] or 0) == 1
                    and (row["role"] or "") in ROLE_ALLOWED_VIEWS
                    and check_password_hash(row["password_hash"] or "", password)
                )
                if not ok:
                    lock_until = self._register_auth_fail(conn, uname)
                    conn.commit()
                    if lock_until:
                        raise PermissionError("Demasiados intentos fallidos. Cuenta bloqueada 15 min.")
                    raise ValueError("Credenciales invalidas.")

                self._clear_auth_lock(conn, uname)
                now = now_str()
                conn.execute(
                    "UPDATE users SET last_login_at=?, updated_at=? WHERE id=?",
                    (now, now, int(row["id"])),
                )
                return {
                    "id": int(row["id"]),
                    "username": row["username"],
                    "role": row["role"],
                    "must_change_password": bool(int(row["must_change_password"] or 0)),
                    "last_login_at": now,
                }

    def auth_change_password(self, username: str, current_password: str, new_password: str) -> dict:
        uname = normalize_username(username)
        if not uname:
            raise ValueError("Usuario invalido.")
        if not current_password:
            raise ValueError("La contrasena actual es requerida.")
        policy_error = validate_password_policy(new_password)
        if policy_error:
            raise ValueError(policy_error)

        with self.lock:
            with self._conn() as conn:
                row = self._user_row(conn, uname)
                if not row or int(row["is_active"] or 0) != 1:
                    raise PermissionError("Usuario no valido o inactivo.")
                if not check_password_hash(row["password_hash"] or "", current_password):
                    raise PermissionError("La contrasena actual no es correcta.")
                if check_password_hash(row["password_hash"] or "", new_password):
                    raise ValueError("La nueva contrasena debe ser distinta a la actual.")

                ts = now_str()
                conn.execute(
                    """
                    UPDATE users
                    SET password_hash=?, must_change_password=0, password_updated_at=?, updated_at=?
                    WHERE id=?
                    """,
                    (generate_password_hash(new_password), ts, ts, int(row["id"])),
                )
                self._clear_auth_lock(conn, uname)
                self._audit(
                    conn,
                    action="auth.password.change",
                    username=uname,
                    entity="user",
                    entity_id=str(int(row["id"])),
                    details={"username": uname},
                )
                return {
                    "id": int(row["id"]),
                    "username": row["username"],
                    "role": row["role"],
                    "must_change_password": False,
                    "password_updated_at": ts,
                }
