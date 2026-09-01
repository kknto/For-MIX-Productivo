from flask import jsonify, redirect, render_template, request, session, url_for

from core.rbac import EDITOR_ROLES, QC_HUMIDITY_ROLES
from core.time import get_now, now_str


def register_auth_routes(
    app,
    store,
    current_auth,
    login_required,
    ensure_csrf_token,
    allowed_views_for_role,
    feature_enabled,
):
    @app.get("/login")
    def login():
        user = current_auth()
        if user:
            if user.get("must_change_password"):
                return redirect(url_for("change_password"))
            return redirect(url_for("index"))
        return render_template("login.html", error="", cache_bust=int(get_now().timestamp()))

    @app.post("/login")
    def login_submit():
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        try:
            user = store.auth_authenticate(username, password)
            session.clear()
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["login_at"] = now_str()
            if user.get("must_change_password"):
                return redirect(url_for("change_password"))
            return redirect(url_for("index"))
        except PermissionError as exc:
            return render_template("login.html", error=str(exc), cache_bust=int(get_now().timestamp())), 429
        except Exception as exc:
            return render_template("login.html", error=str(exc), cache_bust=int(get_now().timestamp())), 401

    @app.get("/change-password")
    @login_required
    def change_password():
        user = request.current_user
        if not user.get("must_change_password"):
            return redirect(url_for("index"))
        return render_template(
            "change_password.html",
            error="",
            username=user["username"],
            role=user["role"],
            cache_bust=int(get_now().timestamp()),
        )

    @app.post("/change-password")
    @login_required
    def change_password_submit():
        user = request.current_user
        if not user.get("must_change_password"):
            return redirect(url_for("index"))
        current_password = request.form.get("current_password") or ""
        new_password = request.form.get("new_password") or ""
        confirm_password = request.form.get("confirm_password") or ""
        if new_password != confirm_password:
            return render_template(
                "change_password.html",
                error="La confirmacion de contrasena no coincide.",
                username=user["username"],
                role=user["role"],
                cache_bust=int(get_now().timestamp()),
            ), 400
        try:
            store.auth_change_password(user["username"], current_password, new_password)
            session["login_at"] = now_str()
            return redirect(url_for("index"))
        except PermissionError as exc:
            code = 403
            msg = str(exc)
        except Exception as exc:
            code = 400
            msg = str(exc)
        return render_template(
            "change_password.html",
            error=msg,
            username=user["username"],
            role=user["role"],
            cache_bust=int(get_now().timestamp()),
        ), code

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def index():
        user = request.current_user
        auth_boot = {
            "username": user["username"],
            "role": user["role"],
            "must_change_password": bool(user.get("must_change_password")),
            "allowed_views": allowed_views_for_role(user["role"]),
            "can_edit": user["role"] in EDITOR_ROLES and feature_enabled("editor"),
            "can_edit_qc_humidity": user["role"] in QC_HUMIDITY_ROLES and feature_enabled("dosificador"),
            "csrf_token": ensure_csrf_token(),
            "enabled_features": dict(app.config["INSTANCE_SETTINGS"].features),
        }
        return render_template("index.html", cache_bust=int(get_now().timestamp()), auth_boot=auth_boot)

    @app.get("/api/session")
    @login_required
    def api_session():
        user = request.current_user
        return jsonify(
            {
                "ok": True,
                "username": user["username"],
                "role": user["role"],
                "must_change_password": bool(user.get("must_change_password")),
                "allowed_views": allowed_views_for_role(user["role"]),
                "can_edit": user["role"] in EDITOR_ROLES and feature_enabled("editor"),
                "can_edit_qc_humidity": user["role"] in QC_HUMIDITY_ROLES and feature_enabled("dosificador"),
                "csrf_token": ensure_csrf_token(),
                "enabled_features": dict(app.config["INSTANCE_SETTINGS"].features),
            }
        )
