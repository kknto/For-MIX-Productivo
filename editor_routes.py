from flask import jsonify, request

from core.errors import ConcurrencyError
from core.rbac import EDITOR_ROLES, ROLE_ALLOWED_VIEWS
from repositories.editor_repository import EditorRepository
from services.editor_service import EditorService, MODES


def register_editor_routes(app, store, require_roles):
    editor_service = EditorService(EditorRepository(store))

    @app.get("/api/data")
    @require_roles(*ROLE_ALLOWED_VIEWS.keys())
    def api_data():
        return jsonify(editor_service.load_active_payload())

    @app.get("/api/families/summary")
    @require_roles(*ROLE_ALLOWED_VIEWS.keys())
    def api_families_summary():
        try:
            return jsonify(editor_service.families_summary())
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/select")
    @require_roles(*ROLE_ALLOWED_VIEWS.keys())
    def api_select():
        payload = request.get_json(silent=True) or {}
        file_name = payload.get("file", "")
        if not isinstance(file_name, str):
            return jsonify({"ok": False, "error": "Invalid file name."}), 400
        try:
            return jsonify(editor_service.select_file(file_name))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/upload/preview")
    @require_roles(*EDITOR_ROLES)
    def api_upload_preview():
        try:
            if "file" not in request.files:
                return jsonify({"ok": False, "error": "Missing file field."}), 400
            out = editor_service.upload_preview(request.files["file"])
            return jsonify(out), (200 if out["ok"] else 400)
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/upload/commit")
    @require_roles(*EDITOR_ROLES)
    def api_upload_commit():
        payload = request.get_json(silent=True) or {}
        token = (payload.get("token") or "").strip()
        mode = (payload.get("mode") or "new").strip().lower()
        target_file = payload.get("target_file")
        family_code = payload.get("family_code")
        if not token:
            return jsonify({"ok": False, "error": "Upload token is required."}), 400
        if mode not in MODES:
            return jsonify({"ok": False, "error": "Mode must be new|replace|merge."}), 400
        if target_file is not None and not isinstance(target_file, str):
            return jsonify({"ok": False, "error": "target_file must be string."}), 400
        if family_code is not None and not isinstance(family_code, str):
            return jsonify({"ok": False, "error": "family_code must be string."}), 400
        try:
            return jsonify(editor_service.commit_upload(
                token=token,
                mode=mode,
                target_file=target_file,
                family_code=family_code,
                actor=request.current_user["username"],
            ))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/upload")
    @require_roles(*EDITOR_ROLES)
    def api_upload_legacy():
        try:
            if "file" not in request.files:
                return jsonify({"ok": False, "error": "Missing file field."}), 400
            out = editor_service.upload_legacy(request.files["file"], actor=request.current_user["username"])
            return jsonify(out), (200 if out["ok"] else 400)
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/purge_deleted")
    @require_roles("administrador")
    def api_purge_deleted():
        try:
            return jsonify(editor_service.purge_deleted(actor=request.current_user["username"]))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/delete")
    @require_roles(*EDITOR_ROLES)
    def api_delete():
        payload = request.get_json(silent=True) or {}
        file_name = payload.get("file", "")
        if not isinstance(file_name, str):
            return jsonify({"ok": False, "error": "Invalid file name."}), 400
        try:
            return jsonify(editor_service.delete_dataset(file_name, actor=request.current_user["username"]))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/family")
    @require_roles(*EDITOR_ROLES)
    def api_family_save():
        payload = request.get_json(silent=True) or {}
        family_code = payload.get("family_code", "")
        file_name = payload.get("file")
        if not isinstance(family_code, str):
            return jsonify({"ok": False, "error": "family_code must be string."}), 400
        if file_name is not None and not isinstance(file_name, str):
            return jsonify({"ok": False, "error": "file must be string."}), 400
        try:
            return jsonify(editor_service.save_family(
                family_code=family_code,
                file_name=file_name,
                actor=request.current_user["username"],
            ))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/save")
    @require_roles(*EDITOR_ROLES)
    def api_save():
        try:
            return jsonify(editor_service.save_dataset(request.get_data(cache=False), actor=request.current_user["username"]))
        except ConcurrencyError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/history")
    @require_roles(*EDITOR_ROLES)
    def api_history():
        file_name = request.args.get("file")
        try:
            return jsonify(editor_service.history(file_name=file_name, limit=50))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/history/restore")
    @require_roles(*EDITOR_ROLES)
    def api_history_restore():
        payload = request.get_json(silent=True) or {}
        revision_id = payload.get("revision_id")
        file_name = payload.get("file")
        version = payload.get("version")
        if revision_id is None:
            return jsonify({"ok": False, "error": "revision_id is required."}), 400
        try:
            revision_id = int(revision_id)
            if version is not None:
                version = int(version)
            return jsonify(
                editor_service.restore_history(
                    revision_id=revision_id,
                    file_name=file_name,
                    version=version,
                    actor=request.current_user["username"],
                )
            )
        except ConcurrencyError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/audit")
    @require_roles(*EDITOR_ROLES)
    def api_audit():
        file_name = request.args.get("file")
        limit = request.args.get("limit", "120")
        try:
            return jsonify(editor_service.audit(file_name=file_name, limit=int(limit)))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/backups")
    @require_roles(*EDITOR_ROLES)
    def api_backups():
        limit = request.args.get("limit", "80")
        try:
            return jsonify(editor_service.backups(limit=int(limit)))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/backups/create")
    @require_roles(*EDITOR_ROLES)
    def api_backups_create():
        payload = request.get_json(silent=True) or {}
        reason = payload.get("reason", "")
        if reason is not None and not isinstance(reason, str):
            return jsonify({"ok": False, "error": "reason must be string."}), 400
        try:
            return jsonify(editor_service.create_backup(reason=reason or "manual", actor=request.current_user["username"]))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/backups/restore")
    @require_roles("administrador")
    def api_backups_restore():
        payload = request.get_json(silent=True) or {}
        backup_file = payload.get("file", "")
        if not isinstance(backup_file, str):
            return jsonify({"ok": False, "error": "file must be string."}), 400
        try:
            return jsonify(editor_service.restore_backup(backup_file=backup_file, actor=request.current_user["username"]))
        except FileNotFoundError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
