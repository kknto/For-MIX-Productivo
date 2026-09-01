from flask import Blueprint, jsonify, request

from core.rbac import roles_for_view
from repositories.fleet_repository import FleetRepository
from services.fleet_service import FleetService


def register_fleet_routes(app, store, login_required, require_roles):
    """
    Registers all fleet-related API routes to the given Flask app via a Blueprint.
    """
    fleet_bp = Blueprint("fleet", __name__, url_prefix="/api/fleet")
    fleet_service = FleetService(FleetRepository(store))

    @fleet_bp.route("/vehicles", methods=["GET"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_vehicles_list():
        return jsonify(fleet_service.list_vehicles())

    @fleet_bp.route("/vehicles", methods=["POST"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_vehicles_save():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(fleet_service.save_vehicle(data, actor=request.current_user["username"]))
        except Exception as exc:
            msg = str(exc)
            if "unique" in msg.lower() or "duplicate" in msg.lower():
                msg = "Ya existe un vehiculo con ese numero de unidad."
            return jsonify({"ok": False, "error": msg}), 400

    @fleet_bp.route("/vehicles/<int:vehicle_id>", methods=["DELETE"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_vehicles_delete(vehicle_id):
        return jsonify(fleet_service.delete_vehicle(vehicle_id, actor=request.current_user["username"]))

    @fleet_bp.route("/fuel", methods=["GET"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_fuel_list():
        vid = request.args.get("vehicle_id", type=int)
        limit = request.args.get("limit", 200, type=int)
        date_from = request.args.get("date_from", "")
        date_to = request.args.get("date_to", "")
        return jsonify(
            fleet_service.list_fuel(
                vehicle_id=vid,
                limit=limit,
                date_from=date_from,
                date_to=date_to,
            )
        )

    @fleet_bp.route("/fuel", methods=["POST"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_fuel_save():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(fleet_service.save_fuel(data, actor=request.current_user["username"]))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @fleet_bp.route("/fuel/<int:record_id>", methods=["PUT"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_fuel_edit(record_id):
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(fleet_service.edit_fuel(record_id, data))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @fleet_bp.route("/fuel/<int:record_id>", methods=["DELETE"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_fuel_delete(record_id):
        return jsonify(fleet_service.delete_fuel(record_id))

    @fleet_bp.route("/summary", methods=["GET"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_summary():
        return jsonify(fleet_service.summary())

    @fleet_bp.route("/kpis", methods=["GET"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_kpis():
        try:
            return jsonify(fleet_service.kpis())
        except Exception:
            return jsonify(
                {
                    "ok": True,
                    "total_vehicles": 0,
                    "month_liters": 0,
                    "month_cost": 0,
                    "month_avg_kml": 0,
                }
            )

    @fleet_bp.route("/trend/<int:vehicle_id>", methods=["GET"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_trend(vehicle_id):
        return jsonify(fleet_service.trend(vehicle_id))

    @fleet_bp.route("/maintenance", methods=["GET"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_maintenance_list():
        vid = request.args.get("vehicle_id", type=int)
        return jsonify(fleet_service.list_maintenance(vehicle_id=vid))

    @fleet_bp.route("/maintenance", methods=["POST"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_maintenance_save():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(fleet_service.save_maintenance(data, actor=request.current_user["username"]))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @fleet_bp.route("/maintenance/<int:record_id>", methods=["DELETE"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_maintenance_delete(record_id):
        return jsonify(fleet_service.delete_maintenance(record_id))

    @fleet_bp.route("/alerts", methods=["GET"])
    @require_roles(*roles_for_view("flotilla"))
    def api_fleet_alerts():
        try:
            return jsonify(fleet_service.alerts())
        except Exception:
            return jsonify({"ok": True, "alerts": []})

    app.register_blueprint(fleet_bp)
