from flask import Blueprint, jsonify, request

from repositories.users_repository import UsersRepository
from services.users_service import UsersService


def register_user_routes(app_store, require_roles):
    users_bp = Blueprint("users_api", __name__, url_prefix="/api/users")
    users_service = UsersService(UsersRepository(app_store))

    @users_bp.route("", methods=["GET"])
    @require_roles("administrador")
    def api_users_list():
        try:
            return jsonify(users_service.list_users())
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @users_bp.route("", methods=["POST"])
    @require_roles("administrador")
    def api_users_save():
        try:
            payload = request.get_json() or {}
            return jsonify(users_service.save_user(payload))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @users_bp.route("/<int:user_id>", methods=["DELETE"])
    @require_roles("administrador")
    def api_users_delete(user_id):
        try:
            return jsonify(users_service.delete_user(user_id))
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @users_bp.route("/<int:user_id>/reset_password", methods=["POST"])
    @require_roles("administrador")
    def api_users_reset_password(user_id):
        try:
            payload = request.get_json() or {}
            return jsonify(users_service.reset_password(user_id, payload.get("new_password")))
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    return users_bp
