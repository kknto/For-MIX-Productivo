import secrets
from functools import wraps

from flask import current_app, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException

from auth_store import normalize_username
from core.errors import ConcurrencyError
from core.rbac import ROLE_ALLOWED_VIEWS
from core.time import get_now


PUBLIC_EXCEPTIONS = (ValueError, FileNotFoundError, PermissionError, ConcurrencyError)


def api_error_response(exc: Exception, status: int = 500):
    if isinstance(exc, FileNotFoundError):
        status = 404
    elif isinstance(exc, PermissionError):
        status = 403
    elif isinstance(exc, (ValueError, ConcurrencyError)):
        status = status if status in {400, 409} else 400

    public = isinstance(exc, PUBLIC_EXCEPTIONS)
    message = str(exc) if public else ("Solicitud invalida." if status < 500 else "Error interno del servidor.")
    request_id = getattr(g, "request_id", "")

    log_extra = {
        "request_id": request_id,
        "method": request.method,
        "path": request.path,
        "status": status,
        "user": session.get("username"),
        "role": session.get("role"),
    }
    if status >= 500 or not public:
        current_app.logger.exception("request.error", extra=log_extra)
    else:
        current_app.logger.warning("request.rejected", extra=log_extra)

    return jsonify({"ok": False, "error": message, "request_id": request_id}), status


def configure_http_security(app, store):
    def api_unauthorized(message: str, status: int):
        return jsonify({"ok": False, "error": message, "request_id": getattr(g, "request_id", "")}), status

    def expected_origins() -> set[str]:
        forwarded_proto = (request.headers.get("X-Forwarded-Proto") or request.scheme or "").split(",")[0].strip()
        forwarded_host = (request.headers.get("X-Forwarded-Host") or request.host or "").split(",")[0].strip()
        origins = {request.host_url.rstrip("/")}
        if forwarded_proto and forwarded_host:
            origins.add(f"{forwarded_proto}://{forwarded_host}".rstrip("/"))
        return origins

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        if request.path.startswith("/api/"):
            return jsonify(
                {
                    "ok": False,
                    "error": exc.description or exc.name,
                    "request_id": getattr(g, "request_id", ""),
                }
            ), exc.code or 500
        return exc

    @app.errorhandler(Exception)
    def handle_unexpected_exception(exc):
        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return api_error_response(exc, 500)
        current_app.logger.exception("request.unhandled", extra={"request_id": getattr(g, "request_id", "")})
        return "Error interno del servidor.", 500

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
    def enforce_same_origin_for_mutations():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None
        if request.path.startswith("/static/"):
            return None
        origin = request.headers.get("Origin")
        if origin and origin.rstrip("/") not in expected_origins():
            return api_unauthorized("Origen no autorizado.", 403)
        return None

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
    def security_headers(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'"
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    return {
        "ensure_csrf_token": ensure_csrf_token,
        "current_auth": current_auth,
        "login_required": login_required,
        "require_roles": require_roles,
    }
