import secrets
from functools import wraps

from flask import jsonify, redirect, render_template, request, session, url_for

from auth_store import normalize_username
from core.rbac import ROLE_ALLOWED_VIEWS
from core.time import get_now


def configure_http_security(app, store):
    def api_unauthorized(message: str, status: int):
        return jsonify({"ok": False, "error": message}), status

    def ensure_csrf_token() -> str:
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    def is_valid_csrf() -> bool:
        expected = str(session.get("_csrf_token") or "")
        if not expected:
            return False
        provided = (
            request.headers.get("X-CSRF-Token")
            or request.form.get("_csrf_token")
            or (((request.get_json(silent=True) or {}).get("_csrf_token")) if request.is_json else "")
            or ""
        )
        return secrets.compare_digest(str(provided), expected)

    def current_auth() -> dict | None:
        username = normalize_username(session.get("username", ""))
        role = (session.get("role") or "").strip()
        if not username or role not in ROLE_ALLOWED_VIEWS:
            return None
        user = store.auth_get_user(username)
        if not user:
            return None
        if user["role"] != role:
            session.clear()
            return None
        return user

    @app.context_processor
    def inject_common_template_vars():
        return {
            "csrf_token": ensure_csrf_token(),
            "instance_meta": app.config["INSTANCE_META"],
        }

    @app.before_request
    def csrf_protect():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None
        if request.path.startswith("/static/"):
            return None
        if is_valid_csrf():
            return None
        message = "Solicitud invalida (CSRF). Recarga la pagina e intenta de nuevo."
        if request.path.startswith("/api/"):
            return api_unauthorized(message, 403)
        if request.endpoint == "login_submit":
            return render_template("login.html", error=message, cache_bust=int(get_now().timestamp())), 403
        if request.endpoint == "change_password_submit":
            user = current_auth()
            if user:
                return render_template(
                    "change_password.html",
                    error=message,
                    username=user["username"],
                    role=user["role"],
                    cache_bust=int(get_now().timestamp()),
                ), 403
        return message, 403

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_auth()
            if user:
                if user.get("must_change_password"):
                    allowed_paths = {"/change-password", "/logout"}
                    if request.path.startswith("/api/") and request.path != "/api/session":
                        return api_unauthorized("Debes cambiar tu contrasena antes de continuar.", 423)
                    if request.path not in allowed_paths:
                        return redirect(url_for("change_password"))
                request.current_user = user
                return fn(*args, **kwargs)
            if request.path.startswith("/api/"):
                return api_unauthorized("Sesion expirada o no autenticada.", 401)
            return redirect(url_for("login"))

        return wrapper

    def require_roles(*roles):
        allowed = set(roles)

        def deco(fn):
            @wraps(fn)
            @login_required
            def wrapper(*args, **kwargs):
                user = request.current_user
                if user["role"] not in allowed:
                    if request.path.startswith("/api/"):
                        return api_unauthorized("No autorizado para esta accion.", 403)
                    return redirect(url_for("index"))
                return fn(*args, **kwargs)

            return wrapper

        return deco

    @app.after_request
    def no_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return {
        "ensure_csrf_token": ensure_csrf_token,
        "current_auth": current_auth,
        "login_required": login_required,
        "require_roles": require_roles,
    }
