from flask import Blueprint, jsonify, request

from core.rbac import roles_for_view
from http_security import api_error_response
from repositories.inventory_repository import InventoryRepository
from services.inventory_service import InventoryService


def register_inventory_routes(app, store, login_required, require_roles=None):
    """
    Registers all inventory-related API routes to the given Flask app via a Blueprint.
    """
    inv_bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")
    inventory_service = InventoryService(InventoryRepository(store))

    @inv_bp.route("/materials", methods=["GET"])
    @require_roles(*roles_for_view("inventario"))
    def api_inv_materials_list():
        return jsonify(inventory_service.list_materials())

    @inv_bp.route("/materials", methods=["POST"])
    @require_roles(*roles_for_view("inventario"))
    def api_inv_materials_save():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(inventory_service.save_material(data, actor=request.current_user["username"]))
        except Exception as exc:
            return api_error_response(exc, 400)

    @inv_bp.route("/materials/<int:material_id>", methods=["DELETE"])
    @require_roles(*roles_for_view("inventario"))
    def api_inv_materials_delete(material_id):
        force = request.args.get("force") == "true"
        if force and request.current_user.get("role") != "administrador":
            return jsonify(
                {"ok": False, "error": "Acceso denegado: eliminacion definitiva requiere rol de administrador"}
            ), 403

        return jsonify(
            inventory_service.delete_material(
                material_id,
                actor=request.current_user["username"],
                force=force,
            )
        )

    @inv_bp.route("/materials/purge-inactive", methods=["POST"])
    @require_roles(*roles_for_view("inventario"))
    def api_inv_materials_purge():
        if request.current_user.get("role") != "administrador":
            return jsonify({"ok": False, "error": "Acceso denegado: se requiere rol de administrador"}), 403

        try:
            return jsonify(inventory_service.purge_inactive())
        except Exception as exc:
            return api_error_response(exc, 400)

    @inv_bp.route("/transactions", methods=["GET"])
    @require_roles(*roles_for_view("inventario"))
    def api_inv_transactions_list():
        mat_id = request.args.get("material_id", type=int)
        limit = request.args.get("limit", 100, type=int)
        return jsonify(inventory_service.list_transactions(material_id=mat_id, limit=limit))

    @inv_bp.route("/transactions", methods=["POST"])
    @require_roles(*roles_for_view("inventario"))
    def api_inv_transactions_save():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(inventory_service.save_transaction(data, actor=request.current_user["username"]))
        except Exception as exc:
            return api_error_response(exc, 400)

    @inv_bp.route("/transactions/<int:transaction_id>", methods=["DELETE"])
    @require_roles(*roles_for_view("inventario"))
    def api_inv_transactions_delete(transaction_id):
        if request.current_user.get("role") != "administrador":
            return jsonify({"ok": False, "error": "Acceso denegado: se requiere rol de administrador"}), 403

        try:
            return jsonify(inventory_service.delete_transaction(transaction_id, actor=request.current_user["username"]))
        except Exception as exc:
            return api_error_response(exc, 400)

    @inv_bp.route("/transactions", methods=["DELETE"])
    @require_roles(*roles_for_view("inventario"))
    def api_inv_transactions_clear():
        if request.current_user.get("role") != "administrador":
            return jsonify({"ok": False, "error": "Acceso denegado: se requiere rol de administrador"}), 403

        try:
            return jsonify(inventory_service.clear_transactions())
        except Exception as exc:
            return api_error_response(exc, 400)

    @inv_bp.route("/daily_summary", methods=["GET"])
    @require_roles(*roles_for_view("inventario"))
    def api_inv_daily_summary():
        date_str = request.args.get("date")
        if not date_str:
            return jsonify({"ok": False, "error": "Fecha requerida (YYYY-MM-DD)"}), 400
        try:
            return jsonify(inventory_service.daily_summary(date_str))
        except Exception as exc:
            return api_error_response(exc, 400)

    app.register_blueprint(inv_bp)
