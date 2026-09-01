from flask import jsonify, request

from core.errors import ConcurrencyError
from core.payloads import decode_json_payload
from core.rbac import DOSIFICADOR_ROLES, EDITOR_ROLES, QC_HUMIDITY_ROLES, ROLE_ALLOWED_VIEWS
from http_security import api_error_response
from repositories.doser_repository import DoserRepository
from services.doser_service import DoserService


def register_doser_routes(app, store, require_roles):
    doser_service = DoserService(DoserRepository(store))

    @app.get("/api/qc")
    @require_roles(*ROLE_ALLOWED_VIEWS.keys())
    def api_qc():
        file_name = request.args.get("file")
        try:
            return jsonify(doser_service.load_qc(file_name=file_name))
        except Exception as exc:
            return api_error_response(exc, 400)

    @app.post("/api/qc/save")
    @require_roles(*EDITOR_ROLES)
    def api_qc_save():
        try:
            payload = decode_json_payload(request.get_data(cache=False))
            file_name = payload.get("file")
            if file_name is not None and not isinstance(file_name, str):
                return jsonify({"ok": False, "error": "file must be string."}), 400
            return jsonify(doser_service.save_qc(payload=payload, actor=request.current_user["username"]))
        except ConcurrencyError as exc:
            return api_error_response(exc, 409)
        except Exception as exc:
            return api_error_response(exc, 400)

    @app.post("/api/qc/humidity/save")
    @require_roles(*QC_HUMIDITY_ROLES)
    def api_qc_humidity_save():
        try:
            payload = decode_json_payload(request.get_data(cache=False))
            file_name = payload.get("file")
            if file_name is not None and not isinstance(file_name, str):
                return jsonify({"ok": False, "error": "file must be string."}), 400
            return jsonify(doser_service.save_qc_humidity(payload=payload, actor=request.current_user["username"]))
        except ConcurrencyError as exc:
            return api_error_response(exc, 409)
        except Exception as exc:
            return api_error_response(exc, 400)

    @app.get("/api/doser/recipes_global")
    @require_roles(*DOSIFICADOR_ROLES)
    def api_doser_recipes_global():
        try:
            return jsonify(doser_service.recipes_global())
        except Exception as exc:
            return api_error_response(exc, 400)

    @app.get("/api/doser/params")
    @require_roles(*DOSIFICADOR_ROLES)
    def api_doser_params():
        file_name = request.args.get("file")
        try:
            return jsonify(doser_service.load_params(file_name=file_name))
        except Exception as exc:
            return api_error_response(exc, 400)

    @app.post("/api/doser/params/save")
    @require_roles(*EDITOR_ROLES)
    def api_doser_params_save():
        try:
            payload = decode_json_payload(request.get_data(cache=False))
            file_name = payload.get("file")
            if file_name is not None and not isinstance(file_name, str):
                return jsonify({"ok": False, "error": "file must be string."}), 400
            return jsonify(doser_service.save_params(payload=payload, actor=request.current_user["username"]))
        except ConcurrencyError as exc:
            return api_error_response(exc, 409)
        except Exception as exc:
            return api_error_response(exc, 400)
