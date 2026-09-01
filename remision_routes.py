from flask import jsonify, request

from core.payloads import decode_json_payload
from core.rbac import DOSIFICADOR_ROLES, REMISIONES_ROLES, REMISION_DELETE_ROLES
from http_security import api_error_response
from repositories.doser_repository import DoserRepository
from services.doser_service import DoserService


def register_remision_routes(app, store, require_roles):
    doser_service = DoserService(DoserRepository(store))

    @app.get("/api/remisiones")
    @require_roles(*REMISIONES_ROLES)
    def api_remisiones_list():
        file_name = request.args.get("file")
        try:
            return jsonify(
                doser_service.list_remisiones(
                    file_name=file_name,
                    query=request.args.get("q", ""),
                    limit=request.args.get("limit", "80"),
                    date_filter=request.args.get("date"),
                    remision_no=request.args.get("remision_no", ""),
                    cliente=request.args.get("cliente", ""),
                    formula=request.args.get("formula", ""),
                    source_file=request.args.get("source_file", ""),
                    date_from=request.args.get("date_from"),
                    date_to=request.args.get("date_to"),
                    page=request.args.get("page", "1"),
                    page_size=request.args.get("page_size"),
                )
            )
        except Exception as exc:
            return api_error_response(exc, 400)

    @app.post("/api/remisiones/save")
    @require_roles(*DOSIFICADOR_ROLES)
    def api_remisiones_save():
        try:
            payload = decode_json_payload(request.get_data(cache=False))
            file_name = payload.get("file")
            if file_name is not None and not isinstance(file_name, str):
                return jsonify({"ok": False, "error": "file must be string."}), 400
            return jsonify(doser_service.save_remision(payload=payload, actor=request.current_user["username"]))
        except Exception as exc:
            return api_error_response(exc, 400)

    @app.get("/api/remisiones/<int:remision_id>")
    @require_roles(*REMISIONES_ROLES)
    def api_remisiones_get(remision_id: int):
        file_name = request.args.get("file")
        try:
            return jsonify(doser_service.get_remision(remision_id=remision_id, file_name=file_name))
        except Exception as exc:
            return api_error_response(exc, 400)

    @app.delete("/api/remisiones/<int:remision_id>")
    @require_roles(*REMISION_DELETE_ROLES)
    def api_remisiones_delete(remision_id: int):
        file_name = request.args.get("file")
        try:
            return jsonify(
                doser_service.delete_remision(
                    remision_id=remision_id,
                    file_name=file_name,
                    actor=request.current_user["username"],
                )
            )
        except FileNotFoundError as exc:
            return api_error_response(exc, 404)
        except Exception as exc:
            return api_error_response(exc, 400)

    @app.put("/api/remisiones/<int:remision_id>")
    @require_roles("administrador")
    def api_remisiones_update(remision_id: int):
        file_name = request.args.get("file")
        payload = request.get_json(silent=True) or {}
        try:
            return jsonify(
                doser_service.update_remision(
                    remision_id=remision_id,
                    payload=payload,
                    file_name=file_name,
                    actor=request.current_user["username"],
                )
            )
        except Exception as exc:
            return api_error_response(exc, 400)
